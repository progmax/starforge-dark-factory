#!/usr/bin/env python3
"""Independent Stage1 HTTP audit. No product imports; network only with --run.

Author modes: --list, --self-check. Verifier mode requires two isolated live services.
All export payloads and bearer tokens remain in memory, never included in reports.
"""
import argparse
import concurrent.futures
import copy
import datetime as dt
import json
import os
import re
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


PASSWORD = "synthetic correct horse"
HANDLES = ["ada", "bob", "cy", "dee", "eve", "op"]
METRICS = {"http_calls": 0, "max_request_seconds": 0.0}
METRICS_LOCK = threading.Lock()
BASE = PEER = None


def fixture(balances=None, currency="EUR", minor_units=2, operators=True):
    balances = balances or [10000] * len(HANDLES)
    return {"currency": currency, "minor_units": minor_units,
            "users": [{"id": "u_" + h, "email": h + "@example.test",
                       "password": PASSWORD, "display_name": h.title(),
                       "handle": h, "balance": b} for h, b in zip(HANDLES, balances)],
            "payments": [], "requests": [],
            "settlement_operator_ids": ["u_op"] if operators else []}


def equal_shares(amount, handles):
    q, r = divmod(amount, len(handles))
    return [{"handle": h, "amount": q + (i < r)} for i, h in enumerate(handles)]


def integral_number(value):
    # JSON numeric encoding is deliberately not restricted to lexical integers (§4).
    return type(value) in (int, float) and value == int(value)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTP:
    def __init__(self, base):
        self.base = base.rstrip("/")
        # Deliberately ignore host proxy settings: these are isolated local targets.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def call(self, method, path, body=None, token=None, key=None, raw=None, auth=None):
        headers = {"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if auth is not None:
            headers["Authorization"] = auth
        if key is not None:
            headers["Idempotency-Key"] = key
        data = raw if raw is not None else (json.dumps(body, ensure_ascii=False).encode("utf-8")
                                           if body is not None else None)
        if isinstance(data, str):
            data = data.encode("utf-8")
        timeout = 10 if path.split("?")[0].startswith("/_test/") else 5
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        start = time.monotonic()
        try:
            response = self.opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            response = exc
        except Exception as exc:
            raise AssertionError(f"transport failure {method} {path}: {type(exc).__name__}") from None
        with response:
            status = response.code
            content_type = response.headers.get("Content-Type", "")
            payload = response.read()
        elapsed = time.monotonic() - start
        with METRICS_LOCK:
            METRICS["http_calls"] += 1
            METRICS["max_request_seconds"] = max(METRICS["max_request_seconds"], elapsed)
        if elapsed > timeout:
            raise AssertionError(f"request timeout budget exceeded {method} {path}")
        if status >= 500:
            raise AssertionError(f"forbidden 5xx {method} {path}: {status}")
        if status == 204:
            if payload:
                raise AssertionError(f"204 must have no body: {method} {path}")
            return status, None
        ct = content_type.lower().replace(" ", "").replace('"', "")
        if not ct.startswith("application/json") or "charset=utf-8" not in ct:
            raise AssertionError(f"JSON UTF-8 content type required: {method} {path}")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise AssertionError(f"response not UTF-8 JSON: {method} {path}") from None
        if status >= 400:
            if not (isinstance(value, dict) and isinstance(value.get("error"), dict)
                    and isinstance(value["error"].get("code"), str)
                    and isinstance(value["error"].get("message"), str)
                    and value["error"]["message"].strip()):
                raise AssertionError(f"invalid error envelope: {method} {path}")
        return status, value


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value):
        raise AssertionError("RFC3339 timestamp with explicit offset required")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
    if parsed.utcoffset() is None:
        raise AssertionError("timestamp must have timezone")
    return parsed


def race(functions):
    """All workers ready at barrier; at most 50 calls released concurrently."""
    if not 1 <= len(functions) <= 50:
        raise ValueError("race requires 1..50 calls")
    barrier = threading.Barrier(len(functions))
    def worker(fn):
        barrier.wait(timeout=15)
        return fn()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(functions)) as pool:
        futures = [pool.submit(worker, fn) for fn in functions]
        return [f.result(timeout=30) for f in futures]


class Stage1(unittest.TestCase):
    def setUp(self):
        self.api = HTTP(BASE)
        self.peer = HTTP(PEER)
        self.sequence = 0
        self.seed()

    def unique(self, prefix="key"):
        self.sequence += 1
        return f"{self.id().split('.')[-1]}-{prefix}-{self.sequence}"

    def expect(self, method, path, body=None, who=None, key=None, status=200,
               code=None, api=None, raw=None, auth=None, token=None):
        api = api or self.api
        token = token if token is not None else (self.tokens[who] if who else None)
        actual, value = api.call(method, path, body, token, key, raw, auth)
        self.assertEqual(actual, status, f"{method} {path} expected status {status}")
        if code:
            self.assertEqual(value["error"]["code"], code, f"{method} {path} error code")
        return value

    def seed(self, data=None, api=None):
        data = data or fixture()
        api = api or self.api
        self.expect("POST", "/_test/reset", data, status=204, api=api)
        tokens = {}
        for user in data["users"]:
            result = self.expect("POST", "/auth/login",
                                 {"email": user["email"], "password": user["password"]}, api=api)
            tokens[user["handle"]] = result["token"]
        if api is self.api:
            self.tokens = tokens
            self.seed_total = sum(u["balance"] for u in data["users"])
            self.currency = data["currency"]
        return tokens

    def balance(self, who, api=None, tokens=None):
        value = self.expect("GET", "/me", token=(tokens or self.tokens)[who], api=api)["balance"]
        self.assertTrue(integral_number(value) and 0 <= value <= 2**53)
        return value

    def balances(self, api=None, tokens=None):
        return [self.balance(h, api, tokens) for h in HANDLES]

    def invariant(self):
        values = self.balances()
        self.assertTrue(all(integral_number(b) and 0 <= b <= 2**53 for b in values))
        self.assertEqual(sum(values), self.seed_total)
        return values

    def payment(self, who="ada", to="bob", amount=10, **extra):
        return self.expect("POST", "/payments", {"to_handle": to, "amount": amount, **extra},
                           who, self.unique(), status=201)

    def request(self, who="bob", payer="ada", amount=10, **extra):
        return self.expect("POST", "/requests", {"payer_handle": payer, "amount": amount, **extra},
                           who, self.unique(), status=201)

    def activity(self, who, query="", api=None, tokens=None):
        return self.expect("GET", "/activity" + query, api=api, token=(tokens or self.tokens)[who])

    def requests(self, who, query="", api=None, tokens=None):
        return self.expect("GET", "/requests" + query, api=api, token=(tokens or self.tokens)[who])

    def ident(self, value):
        self.assertTrue(isinstance(value, str) and len(value) <= 64, "opaque ID string <=64")

    def payment_receipt(self, value, sender, receiver, amount, note="", visibility="public",
                        request_id=None, settlement_id=None):
        self.ident(value["payment_id"])
        for field, expected in {"from_user_id": "u_" + sender, "from_handle": sender,
                                "to_user_id": "u_" + receiver, "to_handle": receiver,
                                "amount": amount, "currency": self.currency, "note": note,
                                "visibility": visibility, "request_id": request_id,
                                "settlement_id": settlement_id}.items():
            self.assertEqual(value[field], expected, field)
        self.assertTrue(integral_number(value["amount"]))
        timestamp(value["created_at"])

    def request_receipt(self, value, requester, payer, amount, note="", status="pending", payment_id=None):
        self.ident(value["request_id"])
        for field, expected in {"requester_id": "u_" + requester, "requester_handle": requester,
                                "payer_id": "u_" + payer, "payer_handle": payer,
                                "amount": amount, "currency": self.currency, "note": note,
                                "status": status, "payment_id": payment_id}.items():
            self.assertEqual(value[field], expected, field)
        self.assertTrue(integral_number(value["amount"]))
        timestamp(value["created_at"])

    def state_observation(self):
        # Public observables only; do not assume implementation's state encoding.
        return {"balances": self.balances(),
                "payments": [self.activity(h) for h in HANDLES],
                "requests": [self.requests(h) for h in HANDLES]}

    def write_context(self, kind):
        if kind == "payments":
            return "/payments", "ada", {"to_handle": "bob", "amount": 3}, {"amount": 0, "to_handle": "bob"}
        if kind == "requests":
            return "/requests", "bob", {"payer_handle": "ada", "amount": 3}, {"amount": 0, "payer_handle": "ada"}
        if kind == "pay":
            req = self.request(amount=3)
            return "/requests/" + req["request_id"] + "/pay", "ada", {}, {"visibility": "invalid"}
        if kind == "splits":
            return "/splits", "ada", {"amount": 3, "participant_handles": ["ada", "bob"]}, {"amount": 0, "participant_handles": ["ada", "bob"]}
        if kind == "settlements":
            return "/settlements", "op", {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 3}]}, {"transfers": []}
        raise ValueError(kind)

    def test_health(self):
        self.assertEqual(self.expect("GET", "/health"), {"status": "ok"})

    def test_reset_seed_and_currency(self):
        for currency, units in [("EUR", 2), ("JPY", 0), ("BHD", 3)]:
            with self.subTest(currency=currency):
                data = fixture(currency=currency, minor_units=units)
                data["payments"] = [{"id": "seed-payment", "from_user_id": "u_ada", "to_user_id": "u_bob",
                                     "amount": 500, "note": "seed", "visibility": "private"}]
                data["requests"] = [{"id": "seed-request", "requester_id": "u_bob", "payer_id": "u_ada",
                                     "amount": 1200, "note": "seed ask", "status": "pending"}]
                self.seed(data)
                for h in HANDLES:
                    me = self.expect("GET", "/me", who=h)
                    expected = {"user_id": "u_" + h, "display_name": h.title(), "handle": h,
                                "balance": 10000, "currency": currency, "minor_units": units}
                    self.assertEqual({field: me[field] for field in expected}, expected)
                self.assertEqual(self.activity("ada")["payments"][0]["payment_id"], "seed-payment")
                self.assertEqual(self.requests("ada")["requests"][0]["request_id"], "seed-request")
                p = self.payment(amount=1000)
                self.payment_receipt(p, "ada", "bob", 1000)
                self.assertEqual(self.balances()[:2], [9000, 11000])
                self.invariant()

    def test_reset_replacement_and_failure(self):
        self.payment()
        self.request()
        old_tokens = dict(self.tokens)
        before = self.state_observation()
        bad = fixture()
        bad["users"][0]["balance"] = -1
        self.expect("POST", "/_test/reset", bad, status=422, code="validation_failed")
        self.assertEqual(self.state_observation(), before)
        self.expect("POST", "/_test/reset", raw="{", status=400, code="malformed_request")
        self.assertEqual(self.state_observation(), before)
        for _ in range(2):
            self.seed(fixture([101, 202, 303, 404, 505, 606], operators=False))
            self.assertEqual(self.balances(), [101, 202, 303, 404, 505, 606])
            self.assertEqual(self.activity("ada")["payments"], [])
            self.assertEqual(self.requests("ada")["requests"], [])
            self.invariant()
        self.expect("GET", "/me", token=old_tokens["ada"], status=401, code="unauthenticated")
        self.expect("POST", "/settlements", {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 1}]},
                    "op", "reset-clears-operator", status=403, code="forbidden")
        # Reset also clears idempotency receipts; same key is a fresh first use.
        body = {"to_handle": "bob", "amount": 1}
        self.expect("POST", "/payments", body, "ada", "cleared-key", status=201)
        self.seed()
        self.expect("POST", "/payments", body, "ada", "cleared-key", status=201)

    def test_authentication(self):
        for body, status, code in [
            ({"email": "bad", "password": PASSWORD, "display_name": "X"}, 422, "validation_failed"),
            ({"email": "@example.test", "password": PASSWORD, "display_name": "X"}, 422, "validation_failed"),
            ({"email": "a@", "password": PASSWORD, "display_name": "X"}, 422, "validation_failed"),
            ({"email": "a@example.test", "password": "1234567", "display_name": "X"}, 422, "validation_failed"),
            ({"email": "ada@example.test", "password": PASSWORD, "display_name": "X"}, 409, "email_taken"),
            ({"email": "ada@else.test", "password": PASSWORD, "display_name": "X"}, 409, "handle_taken"),
            ({"email": 5, "password": PASSWORD, "display_name": "X"}, 400, "malformed_request"),
            ({"email": "x@example.test", "password": False, "display_name": "X"}, 400, "malformed_request"),
            ({"email": "x@example.test", "password": PASSWORD, "display_name": []}, 400, "malformed_request"),
            ({"email": "x@example.test", "password": PASSWORD}, 422, "validation_failed"),
            ({"password": PASSWORD, "display_name": "X"}, 422, "validation_failed"),
            ({"email": "x@example.test", "display_name": "X"}, 422, "validation_failed"),
        ]:
            with self.subTest(status=status, code=code):
                self.expect("POST", "/auth/signup", body, status=status, code=code)
        for body in [{"email": "ada@example.test", "password": "wrong pass"},
                     {"email": "ada@else.test", "password": PASSWORD},
                     {"email": "missing@example.test", "password": PASSWORD}]:
            self.expect("POST", "/auth/login", body, status=401, code="unauthenticated")
        self.expect("POST", "/auth/login", {"email": False, "password": PASSWORD}, status=400, code="malformed_request")
        self.expect("POST", "/auth/login", {"email": "ada@example.test"}, status=422, code="validation_failed")
        for i, local in enumerate(["MiX.+ED", "ABCDEFGHIJKLMNOPQRSTUV", "!"]):
            expected = re.sub("[^a-z0-9_]", "_", local.lower())[:20]
            result = self.expect("POST", "/auth/signup", {"email": local + "@example.test",
                                 "password": "12345678", "display_name": "New 👩🏽‍💻", "handle": "ignored", "extra": {}}, status=201)
            self.ident(result["user_id"])
            self.assertEqual(result["display_name"], "New 👩🏽‍💻")
            self.assertTrue(isinstance(result["token"], str) and bool(result["token"]))
            me = self.expect("GET", "/me", token=result["token"])
            self.assertEqual(me["handle"], expected)
            self.assertEqual(me["balance"], 0)
            self.assertEqual(me["user_id"], result["user_id"])
            self.payment(to=expected, amount=1)
            request = self.request(payer=expected, amount=2)
            self.assertEqual(request["payer_id"], result["user_id"])
            self.assertEqual(self.expect("GET", "/me", token=result["token"])["balance"], 1)
        sessions = [self.expect("POST", "/auth/login", {"email": "ada@example.test", "password": PASSWORD}) for _ in range(3)]
        responses = race([lambda t=r["token"]: self.api.call("GET", "/me", token=t) for r in sessions] +
                         [lambda: self.api.call("GET", "/me", token=self.tokens["ada"])])
        self.assertTrue(all(s == 200 and b["handle"] == "ada" for s, b in responses))
        self.assertEqual(self.balance("ada") + 3, 10000)

    def test_authenticated_routes(self):
        routes = [("GET", "/me", None), ("GET", "/activity", None), ("GET", "/requests", None),
                  ("POST", "/payments", {"to_handle": "bob", "amount": 1}),
                  ("POST", "/requests", {"payer_handle": "bob", "amount": 1}),
                  ("POST", "/splits", {"amount": 1, "participant_handles": ["bob"]}),
                  ("POST", "/settlements", {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 1}]}),
                  ("POST", "/requests/missing/pay", {}), ("POST", "/requests/missing/decline", {}),
                  ("POST", "/requests/missing/cancel", {})]
        for method, path, body in routes:
            for auth in [None, "Basic invalid", "Bearer", "Bearer definitely-unknown"]:
                with self.subTest(path=path, auth_kind=auth and auth.split()[0]):
                    self.expect(method, path, body, key="auth-check", auth=auth, status=401, code="unauthenticated")

    def test_common_validation(self):
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            path, who, valid, _ = self.write_context(kind)
            self.expect("POST", path, who=who, key=self.unique(), raw="{", status=400, code="malformed_request")
            # Explicit endpoint exceptions override generic wrong-field-type handling.
            fields = (["visibility"] if kind == "pay" else
                      ["note", "visibility"] if kind in ["payments", "settlements"] else ["note"])
            if kind != "pay":
                fields += ["amount"]
            for field in fields:
                values = {"amount": [0, -1, 1000000001, 1.5, "1", True, False, None, {}, []],
                          "note": [None, 4, False, [], {}, "x" * 201],
                          "visibility": [None, True, 1, [], {}, "PUBLIC", ""]}[field]
                for bad in values:
                    with self.subTest(path=path, field=field, bad_type=type(bad).__name__):
                        body = copy.deepcopy(valid)
                        target = body["transfers"][0] if kind == "settlements" else body
                        target[field] = bad
                        self.expect("POST", path, body, who, self.unique(), status=422, code="validation_failed")
            for required in ({"payments": ["amount", "to_handle"], "requests": ["amount", "payer_handle"],
                              "pay": [], "splits": ["amount", "participant_handles"], "settlements": ["transfers"]}[kind]):
                body = copy.deepcopy(valid)
                del body[required]
                self.expect("POST", path, body, who, self.unique(), status=422, code="validation_failed")
            if kind in ["payments", "requests"]:
                field = "to_handle" if kind == "payments" else "payer_handle"
                body = {**valid, field: 4}
                self.expect("POST", path, body, who, self.unique(), status=400, code="malformed_request")
            body = {**valid, "unrecognized": {"nested": [1, None, False]}}
            receipt = self.expect("POST", path, body, who, self.unique(), status=201)
            self.assertTrue(isinstance(receipt, dict))
            if kind != "pay":
                for numeric in ["3.0", "3e0"]:
                    numeric_body = json.dumps(valid).replace('"amount": 3', '"amount": ' + numeric)
                    self.expect("POST", path, who=who, key=self.unique(), raw=numeric_body, status=201)
        # Unknown query parameters ignored on both list APIs.
        for route in ["/activity", "/requests"]:
            self.assertEqual(self.expect("GET", route, who="ada"),
                             self.expect("GET", route + "?unrecognized=%7B%7D", who="ada"))
        self.invariant()

    def test_requests_and_insufficient_recovery(self):
        req = self.request(amount=10001, note="  taxi 🚕\n")
        self.request_receipt(req, "bob", "ada", 10001, "  taxi 🚕\n")
        before = self.state_observation()
        key = self.unique("short-pay")
        path = "/requests/" + req["request_id"] + "/pay"
        self.expect("POST", path, {}, "ada", key, status=409, code="insufficient_funds")
        self.assertEqual(self.state_observation(), before)
        self.payment(who="cy", to="ada", amount=1)
        p = self.expect("POST", path, {"visibility": "private", "note": None, "amount": False}, "ada", key, status=201)
        self.payment_receipt(p, "ada", "bob", 10001, "  taxi 🚕\n", "private", req["request_id"])
        paid = next(r for r in self.requests("bob")["requests"] if r["request_id"] == req["request_id"])
        self.request_receipt(paid, "bob", "ada", 10001, "  taxi 🚕\n", "paid", p["payment_id"])
        self.assertIn(p, self.activity("bob")["payments"])
        self.assertNotIn(p, self.activity("eve")["payments"])
        self.assertEqual(self.balances()[:3], [0, 20001, 9999])
        for body, status, code in [({"payer_handle": "bob", "amount": 1}, 422, "self_request"),
                                  ({"payer_handle": "missing", "amount": 1}, 404, "not_found")]:
            self.expect("POST", "/requests", body, "bob", self.unique(), status=status, code=code)
        req2 = self.request(who="ada", payer="bob", amount=1, visibility="private")
        self.request_receipt(req2, "ada", "bob", 1)
        default = self.expect("POST", "/requests/" + req2["request_id"] + "/pay", {}, "bob", self.unique(), status=201)
        self.payment_receipt(default, "bob", "ada", 1, request_id=req2["request_id"])
        self.invariant()

    def test_request_permissions_and_terminal_states(self):
        for action, allowed in [("pay", "ada"), ("decline", "ada"), ("cancel", "bob")]:
            req = self.request()
            path = "/requests/" + req["request_id"] + "/" + action
            before = self.state_observation()
            for caller in [h for h in HANDLES if h != allowed]:
                self.expect("POST", path, {}, caller, self.unique() if action == "pay" else None,
                            status=403, code="forbidden")
                self.assertEqual(self.state_observation(), before)
            self.expect("POST", "/requests/unknown/" + action, {}, allowed,
                        self.unique() if action == "pay" else None, status=404, code="not_found")
        for terminal, owner in [("decline", "ada"), ("cancel", "bob"), ("pay", "ada")]:
            req = self.request()
            root = "/requests/" + req["request_id"]
            result = self.expect("POST", root + "/" + terminal, {}, owner,
                                 self.unique() if terminal == "pay" else None,
                                 status=201 if terminal == "pay" else 200)
            observed = self.state_observation()
            if terminal != "pay":
                self.assertEqual(result["status"], "declined" if terminal == "decline" else "cancelled")
                again = self.expect("POST", root + "/" + terminal, {}, owner)
                self.assertEqual(again, result)
            for action, caller in [("pay", "ada"), ("decline", "ada"), ("cancel", "bob")]:
                if action == terminal and action != "pay":
                    continue
                self.expect("POST", root + "/" + action, {}, caller,
                            self.unique() if action == "pay" else None, status=409, code="request_not_pending")
                self.assertEqual(self.state_observation(), observed)
        self.invariant()

    def test_request_lists(self):
        created = [self.request(who="bob", payer="ada", amount=i) for i in range(1, 5)]
        outgoing = self.request(who="ada", payer="cy", amount=5)
        unrelated = self.request(who="dee", payer="eve", amount=6)
        for req, action, caller in [(created[1], "pay", "ada"), (created[2], "decline", "ada"),
                                    (created[3], "cancel", "bob")]:
            self.expect("POST", "/requests/" + req["request_id"] + "/" + action, {}, caller,
                        self.unique() if action == "pay" else None, status=201 if action == "pay" else 200)
        visible = self.requests("ada")["requests"]
        self.assertEqual({r["request_id"] for r in visible}, {r["request_id"] for r in created + [outgoing]})
        self.assertNotIn(unrelated["request_id"], {r["request_id"] for r in visible})
        for direction, expected in [("incoming", created), ("outgoing", [outgoing])]:
            found = self.requests("ada", "?direction=" + direction)["requests"]
            self.assertEqual({r["request_id"] for r in found}, {r["request_id"] for r in expected})
        for status in ["pending", "paid", "declined", "cancelled"]:
            found = self.requests("ada", "?status=" + status)["requests"]
            self.assertEqual({r["request_id"] for r in found}, {r["request_id"] for r in visible if r["status"] == status})
        self.assertEqual(self.requests("ada", "?direction=outgoing&status=paid")["requests"], [])
        for query in ["?direction=other", "?status=other", "?direction=", "?status="]:
            self.expect("GET", "/requests" + query, who="ada", status=422, code="validation_failed")
        for limit, offset in [(1, 0), (2, 2), (200, 0), (2, 5), (2, 10000)]:
            page = self.requests("ada", f"?limit={limit}&offset={offset}")
            # No writes occur during pagination; timestamp ties need no arbitrary ID ordering.
            self.assertEqual(len(page["requests"]), len(visible[offset:offset + limit]))
            self.assertTrue({r["request_id"] for r in page["requests"]} <= {r["request_id"] for r in visible})
            self.assertIs(page["has_more"], offset + len(page["requests"]) < len(visible))
        times = [timestamp(r["created_at"]) for r in visible]
        self.assertEqual(times, sorted(times, reverse=True))

    def test_feed_and_pagination(self):
        public = self.payment("ada", "bob", 1, visibility="public")
        private = self.payment("cy", "dee", 1, visibility="private")
        own_private = self.payment("ada", "cy", 1, visibility="private")
        req = self.request()
        split = self.expect("POST", "/splits", {"amount": 1, "participant_handles": ["ada", "bob", "cy"]},
                            "ada", self.unique(), status=201)
        expected = {"ada": {public["payment_id"], own_private["payment_id"]},
                    "bob": {public["payment_id"]}, "cy": {p["payment_id"] for p in [public, private, own_private]},
                    "dee": {public["payment_id"], private["payment_id"]}, "eve": {public["payment_id"]},
                    "op": {public["payment_id"]}}
        for h in HANDLES:
            items = self.activity(h)["payments"]
            self.assertEqual({p["payment_id"] for p in items}, expected[h])
            for p in items:
                self.assertEqual(p, next(original for original in [public, private, own_private] if original["payment_id"] == p["payment_id"]))
            self.assertTrue(all("requester_id" not in p and "split_id" not in p for p in items))
        self.assertEqual(self.requests("eve")["requests"], [])
        self.assertNotIn(req["request_id"], {r["request_id"] for r in self.requests("cy")["requests"]})
        self.assertEqual({r["request_id"] for r in self.requests("cy")["requests"]},
                         {r["request_id"] for r in split["requests"] if r["payer_handle"] == "cy"})
        all_items = self.activity("cy")["payments"]
        for limit, offset in [(1, 0), (1, 1), (1, 3), (200, 0), (1, 999999)]:
            page = self.activity("cy", f"?limit={limit}&offset={offset}")
            self.assertEqual(len(page["payments"]), len(all_items[offset:offset + limit]))
            self.assertTrue({p["payment_id"] for p in page["payments"]} <= {p["payment_id"] for p in all_items})
            self.assertIs(page["has_more"], offset + len(page["payments"]) < len(all_items))
        for route in ["/activity", "/requests"]:
            for field, bad_values in [("limit", ["0", "201", "-1", "1e9", "4.0", "%2B4", "", "no", "true"]),
                                      ("offset", ["-1", "1e9", "4.0", "%2B4", "", "no", "false"])]:
                for bad in bad_values:
                    with self.subTest(route=route, field=field, value=bad):
                        self.expect("GET", route + f"?{field}={bad}", who="ada", status=422, code="validation_failed")
            self.expect("GET", route + "?limit=200&offset=0&unknown=ignored", who="ada")
        self.invariant()

    def test_splits_rounding(self):
        self.seed(fixture([0, 0, 0, 0, 0, 0]))
        cases = [(1000, ["ada", "bob", "cy"]), (1, ["ada", "bob", "cy"]),
                 (10, ["ada", "bob", "cy"]), (999, ["ada", "bob", "cy"]),
                 (5, ["ada", "bob", "cy", "dee", "eve"]),
                 (1, ["cy", "bob", "ada"]), (1, ["bob", "cy"]), (7, ["ada"]),
                 (1000000000, ["cy", "bob", "ada"])]
        for amount, handles in cases:
            with self.subTest(amount=amount, handles=handles):
                body = {"amount": amount, "participant_handles": handles, "note": "  dinner 🍜\n"}
                split = self.expect("POST", "/splits", body, "ada", self.unique(), status=201)
                self.ident(split["split_id"])
                timestamp(split["created_at"])
                self.assertEqual(split["currency"], "EUR")
                self.assertEqual(split["amount"], amount)
                self.assertEqual(split["note"], body["note"])
                self.assertEqual(split["shares"], equal_shares(amount, handles))
                self.assertEqual(sum(s["amount"] for s in split["shares"]), amount)
                self.assertLessEqual(max(s["amount"] for s in split["shares"]) - min(s["amount"] for s in split["shares"]), 1)
                shares = [s for s in split["shares"] if s["handle"] != "ada"]
                self.assertEqual(len(split["requests"]), len(shares))
                for req, share in zip(split["requests"], shares):
                    self.request_receipt(req, "ada", share["handle"], share["amount"], body["note"])
                    if share["amount"] == 0:
                        p = self.expect("POST", "/requests/" + req["request_id"] + "/pay", {}, share["handle"], self.unique(), status=201)
                        self.payment_receipt(p, share["handle"], "ada", 0, body["note"], request_id=req["request_id"])
                self.invariant()
        # Full payment of several independent splits, including reordered remainder.
        self.seed()
        for amount, handles in [(10, ["ada", "bob", "cy"]), (10, ["cy", "ada", "bob"]), (1, ["bob", "cy", "ada"])]:
            split = self.expect("POST", "/splits", {"amount": amount, "participant_handles": handles}, "ada", self.unique(), status=201)
            self.assertEqual(split["shares"], equal_shares(amount, handles))
            for req in split["requests"]:
                self.expect("POST", "/requests/" + req["request_id"] + "/pay", {}, req["payer_handle"], self.unique(), status=201)
            self.invariant()

    def test_split_validation_atomic(self):
        before = self.state_observation()
        for handles, status, code in [([], 422, "validation_failed"), (["bob", "bob"], 422, "validation_failed"),
                                      (["bob", "missing"], 404, "not_found")]:
            key = self.unique()
            self.expect("POST", "/splits", {"amount": 1, "participant_handles": handles}, "ada", key, status=status, code=code)
            self.assertEqual(self.state_observation(), before)
            self.expect("POST", "/splits", {"amount": 1, "participant_handles": ["ada"]}, "ada", key, status=201)
        for handles in [None, True, {}, "bob", [4], [None], [False]]:
            self.expect("POST", "/splits", {"amount": 1, "participant_handles": handles}, "ada", self.unique(), status=400, code="malformed_request")
        self.assertEqual(self.state_observation(), before)

    def test_idempotency_all_paths(self):
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            with self.subTest(kind=kind):
                path, who, body, invalid = self.write_context(kind)
                before = self.state_observation()
                for key in [None, ""]:
                    self.expect("POST", path, body, who, key, status=400, code="missing_idempotency_key")
                self.expect("POST", path, body, who, "x" * 256, status=422, code="validation_failed")
                failed_key = self.unique("failed")
                self.expect("POST", path, invalid, who, failed_key, status=422, code="validation_failed")
                self.assertEqual(self.state_observation(), before)
                self.expect("POST", path, who=who, key=failed_key, raw="{", status=400, code="malformed_request")
                original = self.expect("POST", path, body, who, failed_key, status=201)
                after = self.state_observation()
                replay = self.expect("POST", path, body, who, failed_key)
                self.assertEqual(replay, original)
                self.assertEqual(self.state_observation(), after)
                # Claimed-key conflict must precede invalid amount/visibility/batch shape and pending checks.
                self.expect("POST", path, invalid, who, failed_key, status=409, code="idempotency_key_reuse")
                self.assertEqual(self.state_observation(), after)
                # Boundary keys 1 and 255 are accepted independently; fresh pay request each time.
                for boundary in ["x", "x" * 255]:
                    fresh_path, fresh_who, fresh_body, _ = self.write_context(kind)
                    receipt = self.expect("POST", fresh_path, fresh_body, fresh_who, boundary, status=201)
                    self.assertEqual(self.expect("POST", fresh_path, fresh_body, fresh_who, boundary), receipt)
                self.invariant()

    def test_idempotency_scope_and_json(self):
        # Parsed equality, ignored-field body identity and user isolation for EACH path.
        operator_fixture = fixture()
        operator_fixture["settlement_operator_ids"] = ["u_op", "u_eve"]
        self.seed(operator_fixture)
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            path, who, value, _ = self.write_context(kind)
            value = {**value, "semantic_probe": {"a": 1, "b": [False, None]}}
            scoped_key = self.unique("json-each")
            original_value = self.expect("POST", path, value, who, scoped_key, status=201)
            reordered = {k: value[k] for k in reversed(list(value))}
            reordered["semantic_probe"] = {"b": [False, None], "a": 1.0}
            self.assertEqual(self.expect("POST", path, who=who, key=scoped_key,
                                        raw=" \n" + json.dumps(reordered, indent=2) + " \n"), original_value)
            self.expect("POST", path, {**value, "semantic_probe": {"a": True, "b": [False, None]}},
                        who, scoped_key, status=409, code="idempotency_key_reuse")
            other = "eve" if kind == "settlements" else "cy"
            other_path = path
            if kind == "pay":
                req = self.request(payer=other, amount=3)
                other_path = "/requests/" + req["request_id"] + "/pay"
            self.expect("POST", other_path, value, other, scoped_key, status=201)
        body = {"to_handle": "bob", "payer_handle": "bob", "amount": 1000,
                "note": "same", "extra": {"a": 1, "b": [None, True]}}
        key = self.unique()
        original = self.expect("POST", "/payments", body, "ada", key, status=201)
        raw = ' { "extra": {"b":[null,true], "a":1.0}, "note":"same", "amount":1e3, "payer_handle":"bob", "to_handle":"bob" } '
        self.assertEqual(self.expect("POST", "/payments", who="ada", key=key, raw=raw), original)
        # Same exact body/key on another path is a first use, independent of ignored fields.
        self.expect("POST", "/requests", body, "ada", key, status=201)
        self.expect("POST", "/payments", body, "cy", key, status=201)
        self.expect("POST", "/requests", body, "cy", key, status=201)
        for changed in [{**body, "extra": {"a": True, "b": [None, True]}},
                        {**body, "extra": {"a": 1, "b": [True, None]}},
                        {k: v for k, v in body.items() if k != "extra"}]:
            self.expect("POST", "/payments", changed, "ada", key, status=409, code="idempotency_key_reuse")
        first = self.request(amount=1)
        second = self.request(amount=1)
        pay_key = self.unique()
        for req in [first, second]:
            path = "/requests/" + req["request_id"] + "/pay"
            p = self.expect("POST", path, {}, "ada", pay_key, status=201)
            self.assertEqual(self.expect("POST", path, {}, "ada", pay_key), p)
            self.expect("POST", path, {"visibility": "public"}, "ada", pay_key, status=409, code="idempotency_key_reuse")
        split_key = self.unique()
        split = {"amount": 1, "participant_handles": ["ada", "bob", "cy"]}
        self.expect("POST", "/splits", split, "ada", split_key, status=201)
        self.expect("POST", "/splits", {**split, "participant_handles": ["cy", "bob", "ada"]}, "ada", split_key,
                    status=409, code="idempotency_key_reuse")
        self.invariant()

    def test_idempotency_after_state_change(self):
        for action, caller in [("decline", "ada"), ("cancel", "bob"), ("pay", "ada")]:
            body = {"payer_handle": "ada", "amount": 1, "note": "original"}
            create_key = self.unique()
            req = self.expect("POST", "/requests", body, "bob", create_key, status=201)
            path = "/requests/" + req["request_id"] + "/" + action
            pay_key = self.unique()
            result = self.expect("POST", path, {}, caller, pay_key if action == "pay" else None,
                                 status=201 if action == "pay" else 200)
            before = self.state_observation()
            self.assertEqual(self.expect("POST", "/requests", body, "bob", create_key), req)
            if action == "pay":
                self.assertEqual(self.expect("POST", path, {}, "ada", pay_key), result)
                self.expect("POST", path, {"visibility": None}, "ada", pay_key, status=409, code="idempotency_key_reuse")
                self.expect("POST", path, {}, "ada", self.unique(), status=409, code="request_not_pending")
            self.assertEqual(self.state_observation(), before)
        split_body = {"amount": 3, "participant_handles": ["bob", "cy"]}
        key = self.unique()
        split = self.expect("POST", "/splits", split_body, "ada", key, status=201)
        for req in split["requests"]:
            self.expect("POST", "/requests/" + req["request_id"] + "/cancel", {}, "ada")
        before = self.state_observation()
        self.assertEqual(self.expect("POST", "/splits", split_body, "ada", key), split)
        self.assertEqual(self.state_observation(), before)
        # A payment replay is still original after sender has no funds left.
        pbody = {"to_handle": "bob", "amount": self.balance("ada")}
        pkey = self.unique()
        payment = self.expect("POST", "/payments", pbody, "ada", pkey, status=201)
        self.assertEqual(self.expect("POST", "/payments", pbody, "ada", pkey), payment)
        self.invariant()

    def test_concurrent_identical_all_paths(self):
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            with self.subTest(kind=kind):
                self.seed()
                path, who, body, _ = self.write_context(kind)
                before_balances = self.balances()
                before_p = len(self.activity("ada")["payments"])
                before_r = len(self.requests("ada")["requests"])
                key = self.unique()
                results = race([lambda: self.api.call("POST", path, body, self.tokens[who], key) for _ in range(50)])
                self.assertEqual([s for s, _ in results].count(201), 1)
                self.assertEqual([s for s, _ in results].count(200), 49)
                original = next(b for s, b in results if s == 201)
                self.assertTrue(all(b == original for _, b in results), "all concurrent receipts identical")
                money = kind in ["payments", "pay", "settlements"]
                expected = list(before_balances)
                if money:
                    expected[0] -= 3
                    expected[1] += 3
                self.assertEqual(self.balances(), expected)
                self.assertEqual(len(self.activity("ada")["payments"]) - before_p, int(money))
                self.assertEqual(len(self.requests("ada")["requests"]) - before_r, int(kind in ["requests", "splits"]))
                self.invariant()

    def test_concurrent_conflicting_keys(self):
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            self.seed()
            path, who, body, _ = self.write_context(kind)
            alternate = copy.deepcopy(body)
            if kind == "pay":
                alternate["visibility"] = "private"
            elif kind == "settlements":
                alternate["transfers"][0]["note"] = "different"
            else:
                alternate["note"] = "different"
            key = self.unique()
            inputs = [body] * 25 + [alternate] * 25
            results = race([lambda b=b: self.api.call("POST", path, b, self.tokens[who], key) for b in inputs])
            codes = [s for s, _ in results]
            self.assertEqual(codes.count(201), 1)
            self.assertEqual(codes.count(200), 24)
            self.assertEqual(codes.count(409), 25)
            original = next(b for s, b in results if s == 201)
            self.assertTrue(all(b == original for s, b in results if s in [200, 201]))
            self.assertTrue(all(b["error"]["code"] == "idempotency_key_reuse" for s, b in results if s == 409))
            self.invariant()

    def test_concurrent_spending_and_reads(self):
        self.seed(fixture([25, 0, 0, 0, 0, 0]))
        keys = [self.unique() for _ in range(50)]
        results = race([lambda k=k: self.api.call("POST", "/payments", {"to_handle": "bob", "amount": 1}, self.tokens["ada"], k) for k in keys])
        self.assertEqual([s for s, _ in results].count(201), 25)
        self.assertEqual([s for s, _ in results].count(409), 25)
        self.assertTrue(all(b["error"]["code"] == "insufficient_funds" for s, b in results if s == 409))
        self.assertEqual(self.balances(), [0, 25, 0, 0, 0, 0])
        self.assertEqual(len(self.activity("eve")["payments"]), 25)
        self.invariant()
        # Snapshot readers race with transfers. Each snapshot is validated by importing it,
        # never by depending on the opaque state representation. At most50 in flight.
        calls = [lambda k=self.unique(): self.api.call("POST", "/payments", {"to_handle": "ada", "amount": 1}, self.tokens["bob"], k) for _ in range(25)]
        calls += [lambda: self.api.call("GET", "/_test/export") for _ in range(25)]
        results = race(calls)
        for status, snap in results[25:]:
            self.assertEqual(status, 200)
            self.expect("POST", "/_test/import", snap, api=self.peer, status=204)
            values = self.balances(api=self.peer)
            self.assertEqual(sum(values), 25)
            self.assertTrue(all(v >= 0 for v in values))
            payments = self.activity("eve", api=self.peer)["payments"]
            net_ada = 25 - sum(p["amount"] for p in payments if p["from_handle"] == "ada") + sum(p["amount"] for p in payments if p["to_handle"] == "ada")
            self.assertEqual(values[0], net_ada)
        self.assertEqual(self.balances(), [25, 0, 0, 0, 0, 0])
        self.invariant()

    def test_request_terminal_races(self):
        for actions in [["pay"] * 50, ["pay"] * 17 + ["decline"] * 17 + ["cancel"] * 16,
                        ["pay"] * 25 + ["cancel"] * 25, ["pay"] * 25 + ["decline"] * 25,
                        ["cancel"] * 25 + ["decline"] * 25, ["cancel"] * 50, ["decline"] * 50]:
            with self.subTest(actions=sorted(set(actions))):
                self.seed()
                req = self.request(amount=100)
                root = "/requests/" + req["request_id"]
                jobs = []
                for action in actions:
                    key = self.unique() if action == "pay" else None
                    caller = "bob" if action == "cancel" else "ada"
                    jobs.append(lambda a=action, k=key, c=caller: self.api.call("POST", root + "/" + a, {}, self.tokens[c], k))
                results = race(jobs)
                final = self.requests("ada")["requests"][0]
                self.assertIn(final["status"], ["paid", "declined", "cancelled"])
                self.assertTrue(all(s in [200, 201, 409] for s, _ in results))
                for s, b in results:
                    if s == 409:
                        self.assertEqual(b["error"]["code"], "request_not_pending")
                paid = final["status"] == "paid"
                self.assertEqual(sum(s == 201 for s, _ in results), int(paid))
                self.assertEqual(self.balances()[:2], [9900, 10100] if paid else [10000, 10000])
                self.assertEqual(len(self.activity("eve")["payments"]), int(paid))
                for s, b in results:
                    if s == 200:
                        self.assertEqual(b["status"], final["status"])
                self.invariant()

    def test_settlement_net_and_receipts(self):
        self.seed(fixture([0, 0, 0, 0, 0, 0]))
        # Net-zero circulation is affordable despite every sequential first debit being short.
        transfers = [{"from_handle": "ada", "to_handle": "bob", "amount": 7, "visibility": "private", "note": "one"},
                     {"from_handle": "bob", "to_handle": "cy", "amount": 7},
                     {"from_handle": "cy", "to_handle": "ada", "amount": 7, "note": "  🔁\n"}]
        body = {"transfers": transfers, "ignored": []}
        key = self.unique()
        settled = self.expect("POST", "/settlements", body, "op", key, status=201)
        self.ident(settled["settlement_id"])
        timestamp(settled["committed_at"])
        self.assertEqual(len(settled["payments"]), len(transfers))
        for p, t in zip(settled["payments"], transfers):
            self.payment_receipt(p, t["from_handle"], t["to_handle"], t["amount"], t.get("note", ""),
                                 t.get("visibility", "public"), settlement_id=settled["settlement_id"])
            self.assertEqual(p["created_at"], settled["committed_at"])
        self.assertEqual(self.balances(), [0] * 6)
        self.assertEqual(self.expect("POST", "/settlements", body, "op", key), settled)
        for h in HANDLES:
            ids = {p["payment_id"] for p in self.activity(h)["payments"]}
            wanted = {p["payment_id"] for p in settled["payments"] if p["visibility"] == "public" or h in [p["from_handle"], p["to_handle"]]}
            self.assertEqual(ids, wanted)
        # Max32 members, valid integral float/scientific amounts, unknown entry fields ignored.
        entries = [{"from_handle": "ada" if i % 2 == 0 else "bob", "to_handle": "bob" if i % 2 == 0 else "ada",
                    "amount": 1000.0, "unknown": {"x": True}} for i in range(32)]
        result = self.expect("POST", "/settlements", {"transfers": entries}, "op", self.unique(), status=201)
        self.assertEqual(len(result["payments"]), 32)
        maximum = {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 1000000000},
                                  {"from_handle": "bob", "to_handle": "ada", "amount": 1000000000}]}
        self.expect("POST", "/settlements", maximum, "op", self.unique(), status=201)
        self.invariant()

    def test_settlement_validation_and_permissions(self):
        valid = {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 1}]}
        self.expect("POST", "/settlements", valid, key="permission", status=401, code="unauthenticated")
        for h in HANDLES[:-1]:
            self.expect("POST", "/settlements", valid, h, "permission", status=403, code="forbidden")
        before = self.state_observation()
        for transfers in [None, {}, "bad", True, [], [False], [1], ["bad"], valid["transfers"] * 33]:
            key = self.unique()
            self.expect("POST", "/settlements", {"transfers": transfers}, "op", key, status=422, code="validation_failed")
            self.assertEqual(self.state_observation(), before)
        bad_entries = [({"from_handle": "missing", "to_handle": "bob", "amount": 1}, 404, "not_found"),
                       ({"from_handle": "ada", "to_handle": "ada", "amount": 1}, 422, "self_payment"),
                       ({"from_handle": "ada", "to_handle": "bob", "amount": 0}, 422, "validation_failed"),
                       ({"from_handle": "ada", "to_handle": "bob", "amount": 1, "note": None}, 422, "validation_failed"),
                       ({"from_handle": "ada", "to_handle": "bob", "amount": 1, "visibility": False}, 422, "validation_failed"),
                       ({"from_handle": "ada", "to_handle": "bob"}, 422, "validation_failed"),
                       ({"from_handle": 5, "to_handle": "bob", "amount": 1}, 400, "malformed_request")]
        insufficient = {"from_handle": "ada", "to_handle": "bob", "amount": 10001}
        for entry, status, code in bad_entries:
            key = self.unique()
            self.expect("POST", "/settlements", {"transfers": [insufficient, entry]}, "op", key, status=status, code=code)
            self.assertEqual(self.state_observation(), before)
            self.expect("POST", "/settlements", valid, "op", key, status=201)
            # Restore balance/receipt baseline for independent error cases.
            self.seed()
            before = self.state_observation()
        # Two invalid entries: first error wins in input order, before any net funds check.
        a, sa, ca = bad_entries[0]
        b, sb, cb = bad_entries[1]
        for entries, status, code in [([a, b], sa, ca), ([b, a], sb, cb)]:
            self.expect("POST", "/settlements", {"transfers": entries}, "op", self.unique(), status=status, code=code)
            self.assertEqual(self.state_observation(), before)
        key = self.unique()
        self.expect("POST", "/settlements", {"transfers": [insufficient]}, "op", key, status=409, code="insufficient_funds")
        self.assertEqual(self.state_observation(), before)
        self.expect("POST", "/settlements", valid, "op", key, status=201)
        private = self.payment(visibility="private")
        req = self.request()
        self.assertNotIn(private["payment_id"], {p["payment_id"] for p in self.activity("op")["payments"]})
        self.assertNotIn(req["request_id"], {r["request_id"] for r in self.requests("op")["requests"]})
        for action in ["pay", "decline", "cancel"]:
            self.expect("POST", "/requests/" + req["request_id"] + "/" + action, {}, "op",
                        self.unique() if action == "pay" else None, status=403, code="forbidden")
        data = fixture()
        del data["settlement_operator_ids"]
        self.seed(data)
        self.expect("POST", "/settlements", valid, "op", "no-operators", status=403, code="forbidden")

    def test_settlement_concurrency(self):
        self.seed(fixture([25, 0, 0, 0, 0, 0]))
        # Two-member net movement costs one unit; 50 competing batches must not overspend.
        body = {"transfers": [{"from_handle": "ada", "to_handle": "bob", "amount": 2},
                              {"from_handle": "bob", "to_handle": "ada", "amount": 1}]}
        jobs = [lambda k=self.unique(): self.api.call("POST", "/settlements", body, self.tokens["op"], k) for _ in range(50)]
        results = race(jobs)
        self.assertEqual(sum(s == 201 for s, _ in results), 25)
        self.assertEqual(sum(s == 409 for s, _ in results), 25)
        self.assertTrue(all(b["error"]["code"] == "insufficient_funds" for s, b in results if s == 409))
        self.assertEqual(self.balances(), [0, 25, 0, 0, 0, 0])
        payments = self.activity("eve")["payments"]
        self.assertEqual(len(payments), 50)
        groups = {}
        for p in payments:
            groups.setdefault(p["settlement_id"], []).append(p)
        self.assertEqual(len(groups), 25)
        self.assertTrue(all(len(items) == 2 and items[0]["created_at"] == items[1]["created_at"] for items in groups.values()))
        self.invariant()
        # A direct payment competes with settlements for the same seed balance.
        self.seed(fixture([25, 0, 0, 0, 0, 0]))
        jobs = [lambda k=self.unique(): self.api.call("POST", "/settlements", body, self.tokens["op"], k) for _ in range(25)]
        jobs += [lambda k=self.unique(): self.api.call("POST", "/payments", {"to_handle": "cy", "amount": 1}, self.tokens["ada"], k) for _ in range(25)]
        results = race(jobs)
        self.assertEqual(sum(s == 201 for s, _ in results), 25)
        self.assertEqual(sum(s == 409 for s, _ in results), 25)
        values = self.invariant()
        self.assertEqual(values[0], 0)
        self.assertEqual(values[1] + values[2], 25)

    def test_exact_high_balance(self):
        initial = [2**53 - 100, 99, 1, 0, 0, 0]
        self.seed(fixture(initial))
        self.payment(amount=1)
        self.payment("bob", "ada", 1)
        self.assertEqual(self.balances(), initial)
        self.payment(amount=1000000000)
        self.assertEqual(self.balance("ada"), initial[0] - 1000000000)
        self.payment("bob", "ada", 1000000000)
        self.assertEqual(self.balances(), initial)
        self.invariant()
        # Overflow behavior must maintain range/atomicity; status/code are not specified.
        self.seed(fixture([2**53, 1, 0, 0, 0, 0]))
        before = self.state_observation()
        status, _ = self.api.call("POST", "/payments", {"to_handle": "ada", "amount": 1}, self.tokens["bob"], self.unique())
        self.assertTrue(400 <= status < 500, "overflow cannot produce out-of-range balance or 5xx")
        self.assertEqual(self.state_observation(), before)

    def test_export_import_portability(self):
        # Both services must be distinct independent processes supplied by Verifier.
        self.seed(fixture(currency="BHD", minor_units=3))
        receipts = []
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            path, who, body, _ = self.write_context(kind)
            key = self.unique("portable")
            result = self.expect("POST", path, body, who, key, status=201)
            receipts.append((path, who, body, key, result))
        # Preserve replay after request terminal changes and original split response.
        created_request = next(r for path, _, _, _, r in receipts if path == "/requests")
        self.expect("POST", "/requests/" + created_request["request_id"] + "/decline", {}, "ada")
        split = next(r for path, _, _, _, r in receipts if path == "/splits")
        for r in split["requests"]:
            self.expect("POST", "/requests/" + r["request_id"] + "/cancel", {}, "ada")
        pending = self.request(amount=23, note="pending import")
        self.request_receipt(pending, "bob", "ada", 23, "pending import")
        # Failed keys remain reusable after import, across all five paths.
        failed = []
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            path, who, body, invalid = self.write_context(kind)
            key = self.unique("failed-portable")
            self.expect("POST", path, invalid, who, key, status=422, code="validation_failed")
            failed.append((path, who, body, key))
        new_body = {"email": "fresh.user@example.test", "password": "synthetic new password", "display_name": "Fresh"}
        new_user = self.expect("POST", "/auth/signup", new_body, status=201)
        self.payment(to="fresh_user", amount=11, visibility="private", note=" portable 👩🏽‍💻 ")
        sessions = [self.expect("POST", "/auth/login", {"email": "ada@example.test", "password": PASSWORD})["token"] for _ in range(2)]
        before = self.state_observation()
        new_me = self.expect("GET", "/me", token=new_user["token"])
        snap = self.expect("GET", "/_test/export")
        self.assertIsInstance(snap, dict)
        self.assertEqual(snap["track"], "pocketful")
        self.assertEqual(snap["format_version"], 1)
        self.assertIsInstance(snap["state"], dict)
        self.assertEqual(self.state_observation(), before, "export has no HTTP-observable write effects")
        held = copy.deepcopy(snap)
        self.payment(amount=1)
        self.expect("POST", "/requests/" + pending["request_id"] + "/cancel", {}, "bob")
        self.assertTrue(snap == held, "previous export object is independent of source writes")
        destination_tokens = self.seed(api=self.peer)
        old = self.expect("POST", "/auth/signup", {"email": "destination.only@example.test", "password": PASSWORD, "display_name": "Gone"}, api=self.peer, status=201)
        self.expect("POST", "/payments", {"to_handle": "bob", "amount": 19}, token=destination_tokens["ada"],
                    api=self.peer, key="destination-only", status=201)
        for attempt in range(2):
            self.expect("POST", "/_test/import", held, api=self.peer, status=204)
            self.assertEqual(self.balances(api=self.peer), before["balances"])
            for i, h in enumerate(HANDLES):
                self.assertEqual(self.activity(h, api=self.peer), before["payments"][i])
                self.assertEqual(self.requests(h, api=self.peer), before["requests"][i])
                me = self.expect("GET", "/me", who=h, api=self.peer)
                self.assertEqual((me["currency"], me["minor_units"]), ("BHD", 3))
            self.assertEqual(self.expect("GET", "/me", token=new_user["token"], api=self.peer), new_me)
            login = self.expect("POST", "/auth/login", {"email": new_body["email"], "password": new_body["password"]}, api=self.peer)
            self.assertEqual(login["user_id"], new_user["user_id"])
            for token in sessions:
                self.assertEqual(self.expect("GET", "/me", token=token, api=self.peer)["user_id"], "u_ada")
            for path, who, body, key, receipt in receipts:
                self.assertEqual(self.expect("POST", path, body, who, key, api=self.peer), receipt)
                changed = {**body, "unknown_changed": True}
                self.expect("POST", path, changed, who, key, api=self.peer, status=409, code="idempotency_key_reuse")
            self.expect("GET", "/me", token=old["token"], api=self.peer, status=401, code="unauthenticated")
            self.expect("GET", "/me", token=destination_tokens["ada"], api=self.peer, status=401, code="unauthenticated")
            self.expect("POST", "/auth/login", {"email": "destination.only@example.test", "password": PASSWORD}, api=self.peer,
                        status=401, code="unauthenticated")
            for path, who, body, key in failed:
                self.expect("POST", path, body, who, key, api=self.peer, status=201)
            # Permission preserved: original operator can create another batch, others cannot.
            body = {"transfers": [{"from_handle": "cy", "to_handle": "dee", "amount": 1}]}
            self.expect("POST", "/settlements", body, "op", "post-import-new", api=self.peer, status=201)
            self.expect("POST", "/settlements", body, "ada", "post-import-denied", api=self.peer, status=403, code="forbidden")
            # A second import restores original state even after all these destination mutations.
        self.seed(api=self.peer)
        self.expect("GET", "/me", token=new_user["token"], api=self.peer, status=401, code="unauthenticated")
        self.expect("POST", "/auth/login", {"email": new_body["email"], "password": new_body["password"]}, api=self.peer,
                    status=401, code="unauthenticated")
        self.assertEqual(self.expect("GET", "/activity", token=self.seed(api=self.peer)["ada"], api=self.peer)["payments"], [])

    def test_export_import_validation(self):
        self.payment()
        self.request()
        before = self.state_observation()
        good = self.expect("GET", "/_test/export")
        bad_cases = [{k: v for k, v in good.items() if k != field} for field in ["track", "format_version", "state"]]
        bad_cases += [{**good, "track": "other"}, {**good, "format_version": 2},
                      {**good, "state": None}, {**good, "state": []}, {**good, "state": "not an object"}]
        for invalid in bad_cases:
            self.expect("POST", "/_test/import", invalid, status=422, code="validation_failed")
            self.assertEqual(self.state_observation(), before)
        self.expect("POST", "/_test/import", raw="{", status=400, code="malformed_request")
        self.assertEqual(self.state_observation(), before)
        # Unknown envelope fields ignored. The state itself is unchanged and opaque.
        self.expect("POST", "/_test/import", {**good, "unknown_envelope": True}, status=204)
        self.assertEqual(self.state_observation(), before)

    def test_control_atomic_races(self):
        a = fixture([11] * 6, "JPY", 0)
        a["payments"] = [{"id": "seed-a", "from_user_id": "u_ada", "to_user_id": "u_bob", "amount": 1, "note": "a", "visibility": "public"}]
        b = fixture([22] * 6, "BHD", 3, operators=False)
        self.seed(a)
        snap_a = self.expect("GET", "/_test/export")
        self.seed(b)
        snap_b = self.expect("GET", "/_test/export")
        jobs = [lambda: self.api.call("POST", "/_test/reset", a) for _ in range(10)]
        jobs += [lambda: self.api.call("POST", "/_test/import", snap_b) for _ in range(10)]
        jobs += [lambda: self.api.call("POST", "/_test/import", snap_a) for _ in range(10)]
        jobs += [lambda: self.api.call("GET", "/_test/export") for _ in range(20)]
        results = race(jobs)
        self.assertTrue(all(s == 204 for s, _ in results[:30]))
        for s, snapshot in results[30:]:
            self.assertEqual(s, 200)
            self.expect("POST", "/_test/import", snapshot, api=self.peer, status=204)
            tokens = {}
            for h in HANDLES:
                tokens[h] = self.expect("POST", "/auth/login", {"email": h + "@example.test", "password": PASSWORD}, api=self.peer)["token"]
            values = self.balances(api=self.peer, tokens=tokens)
            self.assertIn(values, [[11] * 6, [22] * 6])
            me = self.expect("GET", "/me", token=tokens["ada"], api=self.peer)
            expected_currency = ("JPY", 0) if values == [11] * 6 else ("BHD", 3)
            self.assertEqual((me["currency"], me["minor_units"]), expected_currency)
            ids = {p["payment_id"] for p in self.activity("eve", api=self.peer, tokens=tokens)["payments"]}
            self.assertEqual(ids, {"seed-a"} if values == [11] * 6 else set())
        # Completed replacement must also invalidate any previous source token.
        self.seed(a)
        old = self.tokens["ada"]
        self.expect("POST", "/_test/import", snap_b, status=204)
        self.expect("GET", "/me", token=old, status=401, code="unauthenticated")

    def test_sorting_and_default_pagination(self):
        # More than default50; verify complete lists at200, no invented same-second tie breaker.
        for i in range(55):
            self.payment(amount=1, note=str(i))
            self.request(amount=1, note=str(i))
        for route, field in [("/activity", "payments"), ("/requests", "requests")]:
            default = self.expect("GET", route, who="ada")
            full = self.expect("GET", route + "?limit=200", who="ada")
            self.assertEqual(len(default[field]), 50)
            self.assertEqual(len(full[field]), 55)
            self.assertIs(default["has_more"], True)
            self.assertIs(full["has_more"], False)
            times = [timestamp(item["created_at"]) for item in full[field]]
            self.assertEqual(times, sorted(times, reverse=True))
            # Do not impose a fixed same-second tie order across queries.
            explicit = self.expect("GET", route + "?limit=50&offset=0", who="ada")
            self.assertEqual(len(explicit[field]), len(default[field]))
            last = self.expect("GET", route + "?limit=50&offset=50", who="ada")
            self.assertEqual(len(last[field]), 5)
            self.assertIs(last["has_more"], False)
        self.invariant()
        # Distinct seconds establish pagination order without a same-second tie assumption.
        time.sleep(1.05)
        latest_payment = self.payment(amount=1, note="latest")
        latest_request = self.request(amount=1, note="latest")
        self.assertEqual(self.activity("ada", "?limit=1")["payments"][0]["payment_id"], latest_payment["payment_id"])
        self.assertEqual(self.requests("ada", "?limit=1")["requests"][0]["request_id"], latest_request["request_id"])


    def test_payment_values_and_receipts(self):
        note = "  e\u0301 é 👩🏽‍💻\n\t<>&\"\\\u0000  "
        for literal in ["1000", "1000.0", "1e3"]:
            raw = '{"to_handle":"bob","amount":' + literal + ',"note":' + json.dumps(note) + ',"visibility":"private"}'
            p = self.expect("POST", "/payments", who="ada", key=self.unique(), raw=raw, status=201)
            self.payment_receipt(p, "ada", "bob", 1000, note, "private")
            self.assertEqual(p["note"].encode("utf-8"), note.encode("utf-8"))
            self.assertIn(p, self.activity("bob")["payments"])
        p = self.payment(amount=1)
        self.payment_receipt(p, "ada", "bob", 1)
        self.payment(amount=1, note="🙂" * 200)
        self.assertEqual(self.balances()[:2], [6998, 13002])
        self.invariant()
        self.seed(fixture([1000000000, 0, 0, 0, 0, 0]))
        self.payment_receipt(self.payment(amount=1000000000), "ada", "bob", 1000000000)
        self.assertEqual(self.balances()[:2], [0, 1000000000])

    def test_payment_errors_atomic(self):
        before = self.state_observation()
        for body, status, code in [({"to_handle": "bob", "amount": 10001}, 409, "insufficient_funds"),
                                  ({"to_handle": "ada", "amount": 1}, 422, "self_payment"),
                                  ({"to_handle": "missing", "amount": 1}, 404, "not_found")]:
            self.expect("POST", "/payments", body, "ada", self.unique(), status=status, code=code)
            self.assertEqual(self.state_observation(), before)
        self.payment(amount=10000)
        empty = self.state_observation()
        self.expect("POST", "/payments", {"to_handle": "bob", "amount": 1}, "ada", self.unique(), status=409, code="insufficient_funds")
        self.assertEqual(self.state_observation(), empty)
        self.invariant()


    def test_concurrent_signup(self):
        body = {"email": "newcollision@example.test", "password": PASSWORD, "display_name": "New"}
        results = race([lambda: self.api.call("POST", "/auth/signup", body) for _ in range(50)])
        self.assertEqual(sum(s == 201 for s, _ in results), 1)
        self.assertEqual(sum(s == 409 for s, _ in results), 49)
        self.assertTrue(all(r["error"]["code"] == "email_taken" for s, r in results if s == 409))
        winner = next(r for s, r in results if s == 201)
        login = self.expect("POST", "/auth/login", {"email": body["email"], "password": PASSWORD})
        self.assertEqual(login["user_id"], winner["user_id"])
        self.assertEqual(self.expect("GET", "/me", token=winner["token"])["balance"], 0)
        bodies = [{"email": "samehandle@d" + str(i) + ".test", "password": PASSWORD, "display_name": str(i)} for i in range(50)]
        results = race([lambda b=b: self.api.call("POST", "/auth/signup", b) for b in bodies])
        self.assertEqual(sum(s == 201 for s, _ in results), 1)
        self.assertEqual(sum(s == 409 for s, _ in results), 49)
        self.assertTrue(all(r["error"]["code"] == "handle_taken" for s, r in results if s == 409))
        for body, (s, r) in zip(bodies, results):
            if s == 201:
                login = self.expect("POST", "/auth/login", {"email": body["email"], "password": PASSWORD})
                self.assertEqual(login["user_id"], r["user_id"])
                self.assertEqual(self.expect("GET", "/me", token=r["token"])["handle"], "samehandle")
            else:
                self.expect("POST", "/auth/login", {"email": body["email"], "password": PASSWORD}, status=401, code="unauthenticated")
        self.invariant()

    def test_cross_path_money_races(self):
        for competing in ["payment", "settlement"]:
            for _ in range(3):
                self.seed(fixture([1, 0, 0, 0, 0, 0]))
                req = self.request(amount=1)
                pay_path = "/requests/" + req["request_id"] + "/pay"
                pay_key, other_key = self.unique(), self.unique()
                other_path = "/payments" if competing == "payment" else "/settlements"
                other_body = ({"to_handle": "cy", "amount": 1} if competing == "payment" else
                              {"transfers": [{"from_handle": "ada", "to_handle": "cy", "amount": 1}]})
                other_caller = "ada" if competing == "payment" else "op"
                results = race([lambda: self.api.call("POST", pay_path, {}, self.tokens["ada"], pay_key),
                                lambda: self.api.call("POST", other_path, other_body, self.tokens[other_caller], other_key)])
                self.assertEqual(sorted(s for s, _ in results), [201, 409])
                self.assertEqual(next(b for s, b in results if s == 409)["error"]["code"], "insufficient_funds")
                paid = results[0][0] == 201
                final = self.requests("ada")["requests"][0]
                self.assertEqual(final["status"], "paid" if paid else "pending")
                self.assertEqual(self.balances(), [0, int(paid), int(not paid), 0, 0, 0])
                self.assertEqual(len(self.activity("eve")["payments"]), 1)
                self.invariant()

    def test_reset_clears_all_idempotency_paths(self):
        saves = []
        for kind in ["payments", "requests", "pay", "splits", "settlements"]:
            path, who, body, _ = self.write_context(kind)
            key = self.unique("reset-all")
            receipt = self.expect("POST", path, body, who, key, status=201)
            saves.append((kind, path, who, body, key, receipt))
        snap = self.expect("GET", "/_test/export")
        self.expect("POST", "/_test/import", snap, status=204)
        old_tokens = dict(self.tokens)
        self.seed()
        for h in HANDLES:
            self.expect("GET", "/me", token=old_tokens[h], status=401, code="unauthenticated")
        for kind, path, who, body, key, _ in saves:
            if kind == "pay":
                self.expect("POST", path, body, who, key, status=404, code="not_found")
                path, who, body, _ = self.write_context(kind)
            self.expect("POST", path, body, who, key, status=201)
        self.invariant()


class SafeResult(unittest.TextTestResult):
    """Summary excludes response bodies, token values and export state."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.failed_names = []
        self.subtests_run = 0

    def addFailure(self, test, err):
        self.failed_names.append(test.id())
        super().addFailure(test, err)

    def addError(self, test, err):
        self.failed_names.append(test.id())
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        self.subtests_run += 1
        if err:
            self.failed_names.append(test.id())
        super().addSubTest(test, subtest, err)


def author_checks():
    """Pure oracles and ledger links only. Never instantiate HTTP or execute product."""
    examples = [(1000, 3, [334, 333, 333]), (1, 3, [1, 0, 0]),
                (10, 3, [4, 3, 3]), (999, 3, [333, 333, 333]), (5, 5, [1] * 5)]
    for amount, n, expected in examples:
        assert [s["amount"] for s in equal_shares(amount, HANDLES[:n])] == expected
    for n in range(1, 7):
        for amount in [1, 2, 5, 9, 999, 1000, 1000000000]:
            shares = [s["amount"] for s in equal_shares(amount, HANDLES[:n])]
            assert sum(shares) == amount and max(shares) - min(shares) <= 1
            assert all(type(v) is int and v >= 0 for v in shares)
    for value in ["2026-09-24T11:04:03+00:00", "2026-09-24T19:00:00+02:00", "2026-09-24T11:04:03.123Z"]:
        timestamp(value)
    for value in ["2026-09-24T11:04:03", "bad", 1]:
        try:
            timestamp(value)
        except (AssertionError, ValueError):
            pass
        else:
            raise AssertionError("timezone oracle accepted invalid timestamp")
    ledger = Path(__file__).with_name("LEDGER.md").read_text()
    methods = set(unittest.defaultTestLoader.getTestCaseNames(Stage1))
    references = set(re.findall(r"\btest_[a-z_]+\b", ledger))
    assert references <= methods, "ledger refers to undefined executable tests"
    assert methods <= references, "executable tests missing ledger linkage"
    ids = re.findall(r"^\| (S\d+-\d+) \|", ledger, re.M)
    assert len(ids) == len(set(ids)), "duplicate stable requirement IDs"
    inspections = set(re.findall(r"\bI-\d+\b", Path(__file__).with_name("INSPECTION.md").read_text()))
    assert set(re.findall(r"\bI-\d+\b", ledger)) <= inspections, "missing inspection obligation"
    return {"author_checks": "PASS", "test_methods": len(methods), "ledger_rows": len(ids),
            "inspection_ids": len(inspections), "pure_share_cases": 47, "runtime_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--base-url", default=os.environ.get("AUDIT_BASE_URL"))
    parser.add_argument("--peer-url", default=os.environ.get("AUDIT_PEER_URL"))
    parser.add_argument("--report", help="safe JSON summary path in Verifier evidence directory")
    args = parser.parse_args()
    if args.self_check:
        print(json.dumps(author_checks(), sort_keys=True))
        return 0
    if args.list or not args.run:
        print("\n".join(unittest.defaultTestLoader.getTestCaseNames(Stage1)))
        return 0
    global BASE, PEER
    BASE, PEER = args.base_url, args.peer_url
    if not BASE or not PEER or BASE.rstrip("/") == PEER.rstrip("/"):
        parser.error("--run requires two distinct isolated service URLs; no skipped portability tests")
    for target in [BASE, PEER]:
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ["", "/"] or parsed.query or parsed.fragment:
            parser.error("targets must be bare http service origins without credentials")
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    begin = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Stage1)
    runner = unittest.TextTestRunner(verbosity=2, resultclass=SafeResult)
    result = runner.run(suite)
    summary = {"started_at": started, "elapsed_seconds": round(time.monotonic() - begin, 6),
               "tests_run": result.testsRun, "subtests_run": result.subtests_run,
               "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
               "failed_test_names": sorted(set(result.failed_names)), "http_calls": METRICS["http_calls"],
               "max_request_seconds": round(METRICS["max_request_seconds"], 6),
               "passed": result.wasSuccessful() and not result.skipped}
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
