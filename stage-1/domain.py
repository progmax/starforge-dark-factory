"""Pocketful Stage1. Detached preparation, then live work under Service.lock."""
from contextlib import contextmanager
from collections import deque
import copy
import datetime as dt
from decimal import Decimal
import hashlib
import hmac
import json
import re
import secrets
import threading
import uuid
from urllib.parse import unquote

MAX_BALANCE = 2**53
MAX_AMOUNT = 1_000_000_000
HANDLE = re.compile(r"[a-z0-9_]{1,20}\Z")
STATUSES = {"pending", "paid", "declined", "cancelled"}
CURRENCIES = {"EUR": 2, "JPY": 0, "BHD": 3}


class APIError(Exception):
    def __init__(self, status=422, code="validation_failed", message="Invalid request"):
        self.status, self.code, self.message = status, code, message

    def body(self):
        return {"error": {"code": self.code, "message": self.message}}


class CredentialChanged(Exception):
    """Internal recapture signal, never an HTTP error or state mutation."""


def require(condition, status=422, code="validation_failed", message="Invalid request"):
    if not condition:
        raise APIError(status, code, message)


def field(body, name, kind=str):
    require(name in body, message="Missing " + name)
    value = body[name]
    require(type(value) is kind, 400, "malformed_request", "Wrong type for " + name)
    return value


def integer(value, low, high):
    require(type(value) in (int, Decimal) and low <= value <= high)
    require(value == int(value))
    return int(value)


def fixture_number(body, name, low, high):
    """Fixture scalars follow §5 generic types, unlike API amount exceptions."""
    require(name in body, message="Missing " + name)
    value = body[name]
    require(type(value) in (int, Decimal), 400, "malformed_request", "Wrong type for " + name)
    return integer(value, low, high)


def optional_list(body, name):
    return field(body, name, list) if name in body else []


def amount(body):
    require("amount" in body, message="Missing amount")
    return integer(body["amount"], 1, MAX_AMOUNT)


def note(body):
    value = body.get("note", "")
    require(type(value) is str and len(value) <= 200, message="Invalid note")
    return value


def visibility(body):
    value = body.get("visibility", "public")
    require(type(value) is str and value in ("public", "private"), message="Invalid visibility")
    return value


def identifier(value):
    require(type(value) is str and 1 <= len(value) <= 64, message="Invalid identifier")
    return value


def timestamp(value):
    require(type(value) is str and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})", value))
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
        require(parsed.utcoffset() is not None)
    except ValueError:
        raise APIError(message="Invalid timestamp") from None
    return value


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def new_id():
    return uuid.uuid4().hex


def json_identity(value):
    """Typed exact JSON value, independent of key order and numeric spelling.

    Numeric tuples avoid Decimal context rounding, float conversion and expansion
    of large exponents. Booleans have their own tag. Unknown fields are retained.
    """
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if type(value) in (int, Decimal):
        sign, digits, exponent = Decimal(value).as_tuple()
        digits = list(digits)
        if not any(digits):
            return ["number", 0, [0], 0]
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        return ["number", sign, digits, exponent]
    if type(value) is str:
        return ["string", value]
    if type(value) is list:
        return ["array", [json_identity(v) for v in value]]
    return ["object", [[k, json_identity(value[k])] for k in sorted(value)]]


def body_identity(body):
    return json.dumps(json_identity(body), ensure_ascii=True, separators=(",", ":"))


class PasswordWork:
    """FIFO admission for individual KDF calls, with at most two active.

    This gate is independent of the live-state lock. Callers never hold the
    state lock while waiting here or hashing. Password material is request-local;
    there is no password/result cache and no change to scrypt strength.
    """
    def __init__(self):
        self.condition = threading.Condition()
        self.active = 0
        self.waiters = deque()

    @contextmanager
    def slot(self):
        ticket = object()
        with self.condition:
            self.waiters.append(ticket)
            try:
                while self.active >= 2 or self.waiters[0] is not ticket:
                    self.condition.wait()
            except BaseException:
                self.waiters.remove(ticket)
                self.condition.notify_all()
                raise
            self.waiters.popleft()
            self.active += 1
            self.condition.notify_all()  # Allow the next ticket into a second free slot.
        try:
            yield
        finally:
            with self.condition:
                self.active -= 1
                self.condition.notify_all()


PASSWORD_WORK = PasswordWork()


def password_hash(password):
    salt = secrets.token_bytes(16)
    with PASSWORD_WORK.slot():
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return {"algorithm": "scrypt", "salt": salt.hex(), "digest": digest.hex()}


def password_matches(password, stored):
    with PASSWORD_WORK.slot():
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(stored["salt"]),
                                n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(digest.hex(), stored["digest"])


def empty_state():
    return {"currency": "EUR", "minor_units": 2, "seed_total": 0,
            "users": {}, "payments": {}, "requests": {}, "settlements": {},
            "operators": [], "tokens": {}, "idempotency": [],
            "opening_balances": {}, "historical_payments": [], "historical_requests": []}


def payment_record(state, sender, receiver, count, text, visible, when,
                   payment_id=None, request_id=None, settlement_id=None):
    return {"payment_id": payment_id or new_id(), "from_user_id": sender["id"],
            "from_handle": sender["handle"], "to_user_id": receiver["id"],
            "to_handle": receiver["handle"], "amount": count, "currency": state["currency"],
            "note": text, "visibility": visible, "request_id": request_id,
            "settlement_id": settlement_id, "created_at": when}


def request_record(state, requester, payer, count, text, when, request_id=None,
                   status="pending", payment_id=None):
    return {"request_id": request_id or new_id(), "requester_id": requester["id"],
            "requester_handle": requester["handle"], "payer_id": payer["id"],
            "payer_handle": payer["handle"], "amount": count, "currency": state["currency"],
            "note": text, "status": status, "payment_id": payment_id, "created_at": when}


def build_fixture(body):
    """Build detached replacement. Never replay seeded receipts against net balances."""
    state = empty_state()
    currency = field(body, "currency")
    require(currency in CURRENCIES)
    units = fixture_number(body, "minor_units", 0, 3)
    require(CURRENCIES[currency] == units)
    state.update(currency=currency, minor_units=units)
    users = field(body, "users", list)
    payments = optional_list(body, "payments")
    requests = optional_list(body, "requests")
    operators = optional_list(body, "settlement_operator_ids")
    emails, handles = set(), set()
    for source in users:
        require(type(source) is dict, 400, "malformed_request", "User must be an object")
        uid = identifier(field(source, "id"))
        email, handle = field(source, "email"), field(source, "handle")
        require(HANDLE.fullmatch(handle) and email not in emails and handle not in handles)
        require(uid not in state["users"])
        user = {"id": uid, "email": email, "handle": handle,
                "display_name": field(source, "display_name"),
                "balance": fixture_number(source, "balance", 0, MAX_BALANCE),
                "password_hash": password_hash(field(source, "password"))}
        state["users"][uid] = user
        emails.add(email)
        handles.add(handle)
    state["seed_total"] = sum(u["balance"] for u in state["users"].values())
    state["opening_balances"] = {uid: u["balance"] for uid, u in state["users"].items()}
    for source in payments:
        require(type(source) is dict, 400, "malformed_request", "Payment must be an object")
        pid = identifier(field(source, "id"))
        sender = state["users"].get(field(source, "from_user_id"))
        receiver = state["users"].get(field(source, "to_user_id"))
        require(sender is not None and receiver is not None and sender != receiver)
        require(pid not in state["payments"])
        state["payments"][pid] = payment_record(
            state, sender, receiver, integer(source.get("amount"), 0, MAX_AMOUNT),
            note(source), visibility(source), now(), pid)
    for source in requests:
        require(type(source) is dict, 400, "malformed_request", "Request must be an object")
        rid = identifier(field(source, "id"))
        requester = state["users"].get(field(source, "requester_id"))
        payer = state["users"].get(field(source, "payer_id"))
        require(requester is not None and payer is not None and requester != payer)
        status = field(source, "status") if "status" in source else "pending"
        require(status in STATUSES and rid not in state["requests"])
        state["requests"][rid] = request_record(
            state, requester, payer, integer(source.get("amount"), 0, MAX_AMOUNT), note(source),
            now(), rid, status)
    require(all(type(v) is str for v in operators), 400, "malformed_request", "Operator IDs must be strings")
    require(all(v in state["users"] for v in operators))
    state["operators"] = list(dict.fromkeys(operators))
    # A fixture may contain historical terminal requests without a payment link;
    # the fixture contract does not require a link field. Import validates this
    # through an explicit list of historical request identities below.
    state["historical_requests"] = list(state["requests"])
    state["historical_payments"] = list(state["payments"])
    return state


def validate_import(source):
    """Validate a detached full snapshot, then return its normalized owned state.

    Nothing in the live service is touched on failure. Indexes are derived only
    after this succeeds. Exported retry bodies use the exact typed JSON encoding
    above; their response snapshots remain independent of current records.
    """
    def normalize(value):
        if type(value) is Decimal:
            require(value.is_finite() and value == value.to_integral_value())
            return int(value)
        if type(value) is dict:
            return {k: normalize(v) for k, v in value.items()}
        if type(value) is list:
            return [normalize(v) for v in value]
        return value

    def obj(value):
        require(type(value) is dict)
        return value

    def string(value):
        require(type(value) is str)
        return value

    def keys(value, required):
        obj(value)
        require(set(required) <= set(value))

    def bounded(value, low=0, high=MAX_AMOUNT):
        require(type(value) is int and low <= value <= high)

    def valid_identity(encoded):
        # Verify canonical typed-body encoding without reconstructing lossy floats.
        require(type(encoded) is list and encoded)
        tag = encoded[0]
        require(type(tag) is str)
        if tag == "null":
            require(len(encoded) == 1)
        elif tag == "bool":
            require(len(encoded) == 2 and type(encoded[1]) is bool)
        elif tag == "string":
            require(len(encoded) == 2 and type(encoded[1]) is str)
        elif tag == "number":
            require(len(encoded) == 4 and type(encoded[1]) is int and encoded[1] in (0, 1)
                    and type(encoded[2]) is list and encoded[2]
                    and all(type(d) is int and 0 <= d <= 9 for d in encoded[2])
                    and type(encoded[3]) is int)
            require(encoded[2] == [0] and encoded[1] == 0 and encoded[3] == 0
                    or encoded[2][0] != 0 and encoded[2][-1] != 0)
        elif tag == "array":
            require(len(encoded) == 2 and type(encoded[1]) is list)
            for item in encoded[1]:
                valid_identity(item)
        elif tag == "object":
            require(len(encoded) == 2 and type(encoded[1]) is list)
            names = []
            for pair in encoded[1]:
                require(type(pair) is list and len(pair) == 2 and type(pair[0]) is str)
                names.append(pair[0])
                valid_identity(pair[1])
            require(names == sorted(set(names)))
        else:
            raise APIError()

    try:
        state = normalize(source)
        required = set(empty_state())
        keys(state, required)
        require(type(state["currency"]) is str and state["currency"] in CURRENCIES)
        require(type(state["minor_units"]) is int and state["minor_units"] == CURRENCIES[state["currency"]])
        for name in ("users", "payments", "requests", "settlements", "tokens", "opening_balances"):
            obj(state[name])
        for name in ("operators", "idempotency", "historical_requests", "historical_payments"):
            require(type(state[name]) is list)
        users = state["users"]
        handles, emails = set(), set()
        for uid, user in users.items():
            identifier(uid)
            keys(user, ("id", "email", "handle", "display_name", "balance", "password_hash"))
            require(user["id"] == uid)
            email, handle = string(user["email"]), string(user["handle"])
            require(HANDLE.fullmatch(handle) and email not in emails and handle not in handles)
            string(user["display_name"])
            bounded(user["balance"], 0, MAX_BALANCE)
            hashed = user["password_hash"]
            keys(hashed, ("algorithm", "salt", "digest"))
            require(hashed["algorithm"] == "scrypt"
                    and type(hashed["salt"]) is str and re.fullmatch(r"[0-9a-f]{32}", hashed["salt"])
                    and type(hashed["digest"]) is str and re.fullmatch(r"[0-9a-f]{64}", hashed["digest"]))
            # The service never retains unknown user fields (including plaintext password).
            users[uid] = {k: user[k] for k in ("id", "email", "handle", "display_name", "balance", "password_hash")}
            users[uid]["password_hash"] = {k: hashed[k] for k in ("algorithm", "salt", "digest")}
            handles.add(handle)
            emails.add(email)
        require(type(state["seed_total"]) is int and state["seed_total"] >= 0
                and sum(u["balance"] for u in users.values()) == state["seed_total"])
        require(set(state["opening_balances"]) == set(users))
        for balance in state["opening_balances"].values():
            bounded(balance, 0, MAX_BALANCE)
        require(sum(state["opening_balances"].values()) == state["seed_total"])
        require(all(type(v) is str and v in users for v in state["operators"])
                and len(set(state["operators"])) == len(state["operators"]))
        require(all(type(v) is str and v in state["requests"] for v in state["historical_requests"])
                and len(set(state["historical_requests"])) == len(state["historical_requests"]))
        require(all(type(v) is str and v in state["payments"] for v in state["historical_payments"])
                and len(set(state["historical_payments"])) == len(state["historical_payments"]))
        for token, uid in state["tokens"].items():
            require(type(token) is str and token and not re.search(r"\s", token)
                    and type(uid) is str and uid in users)

        def parties(record, id_fields, handle_fields):
            for id_field, handle_field in zip(id_fields, handle_fields):
                uid = record[id_field]
                require(type(uid) is str and uid in users and record[handle_field] == users[uid]["handle"])
            require(record[id_fields[0]] != record[id_fields[1]])

        def common_record(record, identity_field):
            identifier(record[identity_field])
            bounded(record["amount"])
            require(record["currency"] == state["currency"])
            note(record)
            timestamp(record["created_at"])

        payment_fields = ("payment_id", "from_user_id", "from_handle", "to_user_id", "to_handle",
                          "amount", "currency", "note", "visibility", "request_id", "settlement_id", "created_at")
        request_fields = ("request_id", "requester_id", "requester_handle", "payer_id", "payer_handle",
                          "amount", "currency", "note", "status", "payment_id", "created_at")
        for pid, payment in state["payments"].items():
            keys(payment, payment_fields)
            require(payment["payment_id"] == pid)
            common_record(payment, "payment_id")
            visibility(payment)
            parties(payment, ("from_user_id", "to_user_id"), ("from_handle", "to_handle"))
            for name, collection in (("request_id", "requests"), ("settlement_id", "settlements")):
                link = payment[name]
                require(link is None or type(link) is str and link in state[collection])
            require(payment["request_id"] is None or payment["settlement_id"] is None)
            state["payments"][pid] = {k: payment[k] for k in payment_fields}
        for rid, request in state["requests"].items():
            keys(request, request_fields)
            require(request["request_id"] == rid and type(request["status"]) is str and request["status"] in STATUSES)
            common_record(request, "request_id")
            parties(request, ("requester_id", "payer_id"), ("requester_handle", "payer_handle"))
            pid = request["payment_id"]
            if request["status"] != "paid":
                require(pid is None)
            elif pid is None:
                require(rid in state["historical_requests"])
            else:
                require(type(pid) is str and pid in state["payments"])
                payment = state["payments"][pid]
                require(payment["request_id"] == rid and payment["from_user_id"] == request["payer_id"]
                        and payment["to_user_id"] == request["requester_id"]
                        and payment["amount"] == request["amount"] and payment["note"] == request["note"])
            state["requests"][rid] = {k: request[k] for k in request_fields}
        linked_requests = set()
        for payment in state["payments"].values():
            rid = payment["request_id"]
            if rid is not None:
                require(rid not in linked_requests and state["requests"][rid]["status"] == "paid"
                        and state["requests"][rid]["payment_id"] == payment["payment_id"])
                linked_requests.add(rid)
        settlement_members = set()
        for sid, settlement in state["settlements"].items():
            identifier(sid)
            keys(settlement, ("settlement_id", "committed_at", "payments"))
            require(settlement["settlement_id"] == sid)
            timestamp(settlement["committed_at"])
            members = settlement["payments"]
            require(type(members) is list and 1 <= len(members) <= 32)
            for payment in members:
                obj(payment)
                pid = payment.get("payment_id")
                require(type(pid) is str and pid in state["payments"] and pid not in settlement_members
                        and payment == state["payments"][pid] and payment["settlement_id"] == sid
                        and payment["request_id"] is None and payment["created_at"] == settlement["committed_at"])
                settlement_members.add(pid)
        require(all(p["settlement_id"] is None or p["payment_id"] in settlement_members
                    for p in state["payments"].values()))
        expected_balances = dict(state["opening_balances"])
        historical = set(state["historical_payments"])
        for pid, payment in state["payments"].items():
            if pid not in historical:
                expected_balances[payment["from_user_id"]] -= payment["amount"]
                expected_balances[payment["to_user_id"]] += payment["amount"]
        require(all(users[uid]["balance"] == balance for uid, balance in expected_balances.items()))

        def original_request(receipt):
            keys(receipt, request_fields)
            rid = receipt["request_id"]
            require(type(rid) is str and rid in state["requests"] and receipt["status"] == "pending"
                    and receipt["payment_id"] is None)
            current = state["requests"][rid]
            require(all(receipt[k] == current[k] for k in request_fields if k not in ("status", "payment_id")))

        retries = set()
        for entry in state["idempotency"]:
            keys(entry, ("user_id", "method", "path", "key", "body_key", "response"))
            require(type(entry["user_id"]) is str and entry["user_id"] in users and entry["method"] == "POST")
            path, key = string(entry["path"]), string(entry["key"])
            require(1 <= len(key) <= 255)
            identity = (entry["user_id"], "POST", path, key)
            require(identity not in retries)
            retries.add(identity)
            encoded_text = string(entry["body_key"])
            encoded = json.loads(encoded_text)
            valid_identity(encoded)
            require(encoded[0] == "object" and encoded_text == json.dumps(encoded, ensure_ascii=True, separators=(",", ":")))
            response = obj(entry["response"])
            caller = entry["user_id"]
            if path == "/requests":
                original_request(response)
                require(response["requester_id"] == caller)
            elif path == "/splits":
                keys(response, ("split_id", "amount", "currency", "note", "shares", "requests", "created_at"))
                identifier(response["split_id"])
                bounded(response["amount"], 1)
                require(response["currency"] == state["currency"])
                note(response)
                timestamp(response["created_at"])
                shares = response["shares"]
                require(type(shares) is list and shares and type(response["requests"]) is list)
                q, r = divmod(response["amount"], len(shares))
                names, wanted = set(), []
                handle_index = {u["handle"]: u for u in users.values()}
                for i, share in enumerate(shares):
                    keys(share, ("handle", "amount"))
                    handle = string(share["handle"])
                    require(handle in handle_index and handle not in names)
                    bounded(share["amount"])
                    require(share["amount"] == q + int(i < r))
                    names.add(handle)
                    if handle_index[handle]["id"] != caller:
                        wanted.append(share)
                require(len(wanted) == len(response["requests"]))
                for receipt, share in zip(response["requests"], wanted):
                    original_request(receipt)
                    require(receipt["requester_id"] == caller and receipt["payer_handle"] == share["handle"]
                            and receipt["amount"] == share["amount"] and receipt["note"] == response["note"]
                            and receipt["created_at"] == response["created_at"])
            elif path == "/settlements":
                sid = response.get("settlement_id")
                require(type(sid) is str and sid in state["settlements"] and response == state["settlements"][sid]
                        and caller in state["operators"])
            else:
                pay = re.fullmatch(r"/requests/([^/]+)/pay", path)
                require(path == "/payments" or pay is not None)
                pid = response.get("payment_id")
                require(type(pid) is str and pid in state["payments"] and response == state["payments"][pid]
                        and response["from_user_id"] == caller and response["settlement_id"] is None)
                require(response["request_id"] == (unquote(pay.group(1)) if pay else None))
        return {k: state[k] for k in required}
    except (APIError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise APIError(message="Invalid portable state") from None


class Service:
    def __init__(self):
        self.lock = threading.RLock()
        self.generation = 0  # Local monotonic fence, never exported/imported or reset.
        self.state = empty_state()
        self.reindex()

    def reindex(self):
        self.by_handle = {u["handle"]: u for u in self.state["users"].values()}
        self.by_email = {u["email"]: u for u in self.state["users"].values()}
        self.retries = {(r["user_id"], r["method"], r["path"], r["key"]): r
                        for r in self.state["idempotency"]}

    def replace(self, state):
        self.state = state
        self.reindex()
        self.generation += 1

    def authenticate(self, header):
        require(type(header) is str, 401, "unauthenticated", "Bearer token required")
        match = re.fullmatch(r"Bearer ([^\s]+)", header, re.IGNORECASE)
        uid = self.state["tokens"].get(match.group(1)) if match else None
        require(uid in self.state["users"], 401, "unauthenticated", "Unknown bearer token")
        return self.state["users"][uid]

    def session(self, user):
        token = secrets.token_urlsafe(32)
        self.state["tokens"][token] = user["id"]
        return {"user_id": user["id"], "display_name": user["display_name"], "token": token}

    def signup_fields(self, body):
        email, password = field(body, "email"), field(body, "password")
        name = field(body, "display_name")
        require(email.count("@") == 1 and all(email.split("@")) and len(password) >= 8)
        handle = re.sub(r"[^a-z0-9_]", "_", email.split("@", 1)[0].lower())[:20]
        return email, password, name, handle

    def signup_available(self, email, handle):
        require(email not in self.by_email, 409, "email_taken", "Email already registered")
        require(handle not in self.by_handle, 409, "handle_taken", "Derived handle already registered")

    def prepare(self, method, path, body):
        """No live mutations, no KDF while holding the live-state lock.

        Controls are validated against their detached inputs. Auth briefly reads
        live indexes, releases the lock for hashing, then revalidates in auth().
        All other routes defer processing to the locked route, preserving retry
        conflict/replay precedence over business validation/current resources.
        """
        if method != "POST":
            return None
        if path == "/_test/reset":
            return build_fixture(body)
        if path == "/_test/import":
            require(body.get("track") == "pocketful" and type(body.get("format_version")) in (int, Decimal)
                    and body.get("format_version") == 1 and type(body.get("state")) is dict)
            return validate_import(body["state"])
        if path == "/auth/signup":
            email, password, _, handle = self.signup_fields(body)
            with self.lock:
                self.signup_available(email, handle)
            return {"password_hash": password_hash(password)}
        if path == "/auth/login":
            email, password = field(body, "email"), field(body, "password")
            with self.lock:
                user = self.by_email.get(email)
                require(user is not None, 401, "unauthenticated", "Email or password not recognized")
                prepared = {"generation": self.generation, "email": email,
                            "user_id": user["id"], "password_hash": dict(user["password_hash"])}
            prepared["matched"] = password_matches(password, prepared["password_hash"])
            return prepared
        return None

    def auth(self, path, body, prepared):
        email, password = field(body, "email"), field(body, "password")
        user = self.by_email.get(email)
        if path == "/auth/login":
            # Check the fence even for a wrong-password result. Reused IDs/hashes
            # cannot disguise any intervening replacement (ABA). Recapture and
            # reverify current credentials outside this lock, without a retry cap.
            if (self.generation != prepared["generation"] or prepared["email"] != email
                    or user is None or user["id"] != prepared["user_id"]
                    or user["password_hash"] != prepared["password_hash"]):
                raise CredentialChanged()
            require(prepared["matched"], 401, "unauthenticated", "Email or password not recognized")
            return 200, self.session(user)
        email, _, name, handle = self.signup_fields(body)
        self.signup_available(email, handle)
        uid = new_id()
        while uid in self.state["users"]:
            uid = new_id()
        user = {"id": uid, "email": email, "handle": handle, "display_name": name,
                "balance": 0, "password_hash": prepared["password_hash"]}
        self.state["users"][user["id"]] = user
        self.state["opening_balances"][user["id"]] = 0
        self.by_handle[handle] = self.by_email[email] = user
        return 201, self.session(user)

    def find_handle(self, value):
        require(type(value) is str, 400, "malformed_request", "Handle must be a string")
        require(HANDLE.fullmatch(value), message="Invalid handle")
        user = self.by_handle.get(value)
        require(user is not None, 404, "not_found", "No such handle")
        return user

    def transfer_values(self, body, sender=None):
        count, text, visible = amount(body), note(body), visibility(body)
        if sender is None:
            sender = self.find_handle(field(body, "from_handle"))
        receiver = self.find_handle(field(body, "to_handle"))
        require(sender["id"] != receiver["id"], 422, "self_payment", "Cannot pay yourself")
        return sender, receiver, count, text, visible

    def resulting_balances(self, transfers):
        changes = {}
        for sender, receiver, count, *_ in transfers:
            changes[sender["id"]] = changes.get(sender["id"], 0) - count
            changes[receiver["id"]] = changes.get(receiver["id"], 0) + count
        result = {uid: self.state["users"][uid]["balance"] + delta for uid, delta in changes.items()}
        require(all(v >= 0 for v in result.values()), 409, "insufficient_funds", "Insufficient funds")
        require(all(v <= MAX_BALANCE for v in result.values()), message="Balance range exceeded")
        return result

    def commit_money(self, balances, payments):
        # All final values have been checked. Never apply individual settlement debits.
        for uid, balance in balances.items():
            self.state["users"][uid]["balance"] = balance
        for payment in payments:
            self.state["payments"][payment["payment_id"]] = payment

    def create_request(self, caller, body):
        count, text = amount(body), note(body)
        payer = self.find_handle(field(body, "payer_handle"))
        require(payer["id"] != caller["id"], 422, "self_request", "Cannot request from yourself")
        request = request_record(self.state, caller, payer, count, text, now())
        self.state["requests"][request["request_id"]] = request
        return request

    def request_action(self, caller, rid, action, body):
        visible = visibility(body) if action == "pay" else None
        request = self.state["requests"].get(rid)
        require(request is not None, 404, "not_found", "No such request")
        role = "requester_id" if action == "cancel" else "payer_id"
        require(caller["id"] == request[role], 403, "forbidden", "Wrong request party")
        terminal = {"cancel": "cancelled", "decline": "declined"}.get(action)
        if terminal and request["status"] == terminal:
            return request
        require(request["status"] == "pending", 409, "request_not_pending", "Request is terminal")
        if terminal:
            request["status"] = terminal
            return request
        receiver = self.state["users"][request["requester_id"]]
        transfer = (caller, receiver, request["amount"], request["note"], visible)
        balances = self.resulting_balances([transfer])
        payment = payment_record(self.state, *transfer, now(), request_id=rid)
        self.commit_money(balances, [payment])
        request.update(status="paid", payment_id=payment["payment_id"])
        return payment

    def split(self, caller, body):
        count, text = amount(body), note(body)
        handles = field(body, "participant_handles", list)
        require(all(type(h) is str for h in handles), 400, "malformed_request", "Handles must be strings")
        require(handles and len(set(handles)) == len(handles))
        users = [self.find_handle(h) for h in handles]
        q, r = divmod(count, len(handles))
        shares = [{"handle": h, "amount": q + int(i < r)} for i, h in enumerate(handles)]
        when = now()
        requests = [request_record(self.state, caller, u, s["amount"], text, when)
                    for u, s in zip(users, shares) if u["id"] != caller["id"]]
        result = {"split_id": new_id(), "amount": count, "currency": self.state["currency"],
                  "note": text, "shares": shares, "requests": requests, "created_at": when}
        for request in requests:
            self.state["requests"][request["request_id"]] = request
        return result

    def settlement(self, body):
        entries = body.get("transfers")
        require(type(entries) is list and 1 <= len(entries) <= 32 and
                all(type(entry) is dict for entry in entries), message="Invalid transfer batch")
        # Validation is sequential in input order, entirely before the funds check.
        transfers = [self.transfer_values(entry) for entry in entries]
        balances = self.resulting_balances(transfers)
        sid, when = new_id(), now()
        payments = [payment_record(self.state, *transfer, when, settlement_id=sid) for transfer in transfers]
        result = {"settlement_id": sid, "committed_at": when, "payments": payments}
        self.commit_money(balances, payments)
        self.state["settlements"][sid] = result
        return result

    def write(self, path, caller, body, key):
        require(key is not None and key != "", 400, "missing_idempotency_key", "Idempotency-Key required")
        require(1 <= len(key) <= 255, message="Invalid Idempotency-Key length")
        identity = (caller["id"], "POST", path, key)
        body_key = body_identity(body)
        old = self.retries.get(identity)
        if old is not None:
            require(old["body_key"] == body_key, 409, "idempotency_key_reuse", "Key claimed by another body")
            return 200, old["response"]
        if path == "/payments":
            transfer = self.transfer_values(body, caller)
            balances = self.resulting_balances([transfer])
            result = payment_record(self.state, *transfer, now())
            self.commit_money(balances, [result])
        elif path == "/requests":
            result = self.create_request(caller, body)
        elif path == "/splits":
            result = self.split(caller, body)
        elif path == "/settlements":
            require(caller["id"] in self.state["operators"], 403, "forbidden", "Operator required")
            result = self.settlement(body)
        else:
            rid = unquote(path.split("/")[2])
            result = self.request_action(caller, rid, "pay", body)
        # The snapshot is separate from mutable request/split records. Only successes claim keys.
        entry = {"user_id": caller["id"], "method": "POST", "path": path, "key": key,
                 "body_key": body_key, "response": copy.deepcopy(result)}
        self.state["idempotency"].append(entry)
        self.retries[identity] = entry
        return 201, result

    def listing(self, path, caller, query):
        def count_param(name, default, low, high=None):
            value = query.get(name, [str(default)])[0]
            require(re.fullmatch(r"[0-9]+", value), message="Invalid " + name)
            # Compare decimal lengths before conversion; arbitrarily large offsets are valid.
            digits = value.lstrip("0") or "0"
            if high is not None:
                require(len(digits) <= len(str(high)) and int(digits) <= high)
            if len(digits) > 20:
                return 10**20  # Already beyond any realizable in-memory list.
            result = int(digits)
            require(result >= low)
            return result
        limit = count_param("limit", 50, 1, 200)
        offset = count_param("offset", 0, 0)
        uid = caller["id"]
        if path == "/activity":
            name = "payments"
            values = [p for p in self.state[name].values() if p["visibility"] == "public" or
                      uid in (p["from_user_id"], p["to_user_id"])]
        else:
            name = "requests"
            direction, status = query.get("direction", [None])[0], query.get("status", [None])[0]
            require(direction is None or direction in ("incoming", "outgoing"))
            require(status is None or status in STATUSES)
            values = [r for r in self.state[name].values()
                      if uid in (r["requester_id"], r["payer_id"])
                      and (direction is None or r["payer_id" if direction == "incoming" else "requester_id"] == uid)
                      and (status is None or r["status"] == status)]
        values.sort(key=lambda v: dt.datetime.fromisoformat(v["created_at"].replace("Z", "+00:00").replace("z", "+00:00")), reverse=True)
        page = values[offset:offset + limit]
        return {name: page, "has_more": offset + len(page) < len(values)}

    def route(self, method, path, query, body, authorization, key, prepared=None):
        """Called with lock held through response encoding by the HTTP boundary."""
        if method == "GET" and path == "/health":
            return 200, {"status": "ok"}
        if method == "GET" and path == "/_test/export":
            return 200, {"track": "pocketful", "format_version": 1, "state": self.state}
        if method == "POST" and path == "/_test/reset":
            self.replace(prepared)
            return 204, None
        if method == "POST" and path == "/_test/import":
            self.replace(prepared)
            return 204, None
        if method == "POST" and path in ("/auth/signup", "/auth/login"):
            return self.auth(path, body, prepared)
        caller = self.authenticate(authorization)
        if method == "GET" and path == "/me":
            return 200, {"user_id": caller["id"], "display_name": caller["display_name"],
                         "handle": caller["handle"], "balance": caller["balance"],
                         "currency": self.state["currency"], "minor_units": self.state["minor_units"]}
        if method == "GET" and path in ("/activity", "/requests"):
            return 200, self.listing(path, caller, query)
        action = re.fullmatch(r"/requests/([^/]+)/(pay|decline|cancel)", path)
        if method == "POST" and (path in ("/payments", "/requests", "/splits", "/settlements")
                                  or (action and action.group(2) == "pay")):
            # Nonoperators cannot touch settlements; successful retries still resolve
            # before current permission/resource checks inside write.
            if path == "/settlements" and (caller["id"], "POST", path, key) not in self.retries:
                require(caller["id"] in self.state["operators"], 403, "forbidden", "Operator required")
            return self.write(path, caller, body, key)
        if method == "POST" and action:
            return 200, self.request_action(caller, unquote(action.group(1)), action.group(2), body)
        raise APIError(404, "not_found", "No such endpoint")
