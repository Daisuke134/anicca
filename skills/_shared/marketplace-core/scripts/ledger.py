"""Receipt-backed, provider-independent ledger event normalization.

This module is deliberately limited to pure normalization.  It validates one
marketplace contract, removes provider-specific fields, and returns the
immutable event shape consumed by a later ledger store.
"""

from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time
from typing import Any, Dict, List, Mapping, Optional

try:
    from .contracts import (  # type: ignore
        ApplicationIntent,
        ApplicationReceipt,
        ContractReceipt,
        ContractValidationError,
        DeliveryIntent,
        DeliveryReceipt,
        Opportunity,
        PaymentReceipt,
        WorkEvent,
        parse_contract,
    )
except (ImportError, ValueError):
    try:
        from contracts import (  # type: ignore
            ApplicationIntent,
            ApplicationReceipt,
            ContractReceipt,
            ContractValidationError,
            DeliveryIntent,
            DeliveryReceipt,
            Opportunity,
            PaymentReceipt,
            WorkEvent,
            parse_contract,
        )
    except ImportError:
        _CONTRACTS_PATH = Path(__file__).with_name("contracts.py")
        _CONTRACTS_SPEC = importlib.util.spec_from_file_location(
            "marketplace_core_contracts_for_ledger", _CONTRACTS_PATH
        )
        if _CONTRACTS_SPEC is None or _CONTRACTS_SPEC.loader is None:
            raise ImportError("marketplace_contracts_module_unavailable")
        _CONTRACTS_MODULE = importlib.util.module_from_spec(_CONTRACTS_SPEC)
        sys.modules[_CONTRACTS_SPEC.name] = _CONTRACTS_MODULE
        _CONTRACTS_SPEC.loader.exec_module(_CONTRACTS_MODULE)
        ApplicationIntent = _CONTRACTS_MODULE.ApplicationIntent
        ApplicationReceipt = _CONTRACTS_MODULE.ApplicationReceipt
        ContractReceipt = _CONTRACTS_MODULE.ContractReceipt
        ContractValidationError = _CONTRACTS_MODULE.ContractValidationError
        DeliveryIntent = _CONTRACTS_MODULE.DeliveryIntent
        DeliveryReceipt = _CONTRACTS_MODULE.DeliveryReceipt
        Opportunity = _CONTRACTS_MODULE.Opportunity
        PaymentReceipt = _CONTRACTS_MODULE.PaymentReceipt
        WorkEvent = _CONTRACTS_MODULE.WorkEvent
        parse_contract = _CONTRACTS_MODULE.parse_contract


class LedgerError(ValueError):
    """Base class for ledger normalization and persistence errors."""


class ReceiptRequiredError(LedgerError):
    """Raised when a proposed action lacks an authoritative receipt."""


class UnsupportedLedgerEvent(LedgerError):
    """Raised when a source state cannot become a ledger event."""


class IdempotencyConflict(LedgerError):
    """Raised when one ledger identity is reused with conflicting content."""

    code = "idempotency_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class LedgerSchemaError(LedgerError):
    """Raised when a source value is not a valid marketplace contract."""


@dataclass(frozen=True)
class LedgerEvent:
    schema_version: int
    idempotency_key: str
    event_type: str
    platform: str
    external_id: str
    source_record_type: str
    source_idempotency_key: Optional[str]
    content_sha256: str
    fingerprint_sha256: str
    occurred_at: str
    observed_at: str
    receipt_id: Optional[str]
    amount_minor: Optional[int]
    currency: Optional[str]


_RECEIPT_ONLY_WORK_EVENTS = frozenset(
    {
        "application_submitted",
        "application_verified",
        "delivery_submitted",
        "delivery_verified",
        "payment_received",
    }
)
_SUPPORTED_WORK_EVENTS = frozenset(
    {"message_received", "order_awarded", "artifact_verified"}
)
_ALLOWED_EVENT_TYPES = frozenset(
    {
        "opportunity_seen",
        "application_submitted",
        "application_verified",
        "message_received",
        "order_awarded",
        "artifact_verified",
        "delivery_submitted",
        "delivery_verified",
        "payment_received",
    }
)


def _canonical_fingerprint(parsed: Any) -> str:
    wire = asdict(parsed)
    wire.pop("observed_at", None)
    canonical = json.dumps(
        wire, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _raise_schema_error(exc: BaseException) -> None:
    raise LedgerSchemaError(str(exc)) from exc


def _parse_source(value: Mapping[str, object]) -> Any:
    try:
        return parse_contract(value)
    except ContractValidationError as exc:
        _raise_schema_error(exc)
    except (KeyError, TypeError, ValueError) as exc:
        _raise_schema_error(exc)
    raise AssertionError("unreachable")


def _build_event(
    parsed: Any,
    event_type: str,
    external_id: str,
    content_sha256: str,
    source_idempotency_key: Optional[str],
    occurred_at: str,
    receipt_id: Optional[str] = None,
    amount_minor: Optional[int] = None,
    currency: Optional[str] = None,
) -> LedgerEvent:
    fingerprint_sha256 = _canonical_fingerprint(parsed)
    idempotency_key = "{}:{}:{}:{}".format(
        parsed.platform, event_type, external_id, content_sha256
    )
    return LedgerEvent(
        schema_version=parsed.schema_version,
        idempotency_key=idempotency_key,
        event_type=event_type,
        platform=parsed.platform,
        external_id=external_id,
        source_record_type=parsed.record_type,
        source_idempotency_key=source_idempotency_key,
        content_sha256=content_sha256,
        fingerprint_sha256=fingerprint_sha256,
        occurred_at=occurred_at,
        observed_at=parsed.observed_at,
        receipt_id=receipt_id,
        amount_minor=amount_minor,
        currency=currency,
    )


def _normalize_opportunity(parsed: Opportunity) -> LedgerEvent:
    content_sha256 = _canonical_fingerprint(parsed)
    return _build_event(
        parsed=parsed,
        event_type="opportunity_seen",
        external_id=parsed.external_id,
        content_sha256=content_sha256,
        source_idempotency_key=None,
        occurred_at=parsed.observed_at,
    )


def _normalize_application_receipt(parsed: ApplicationReceipt) -> LedgerEvent:
    if parsed.status == "submitted":
        event_type = "application_submitted"
    elif parsed.status == "verified":
        event_type = "application_verified"
    else:
        raise UnsupportedLedgerEvent(
            "application receipt status is unsupported: {}".format(parsed.status)
        )
    return _build_event(
        parsed=parsed,
        event_type=event_type,
        external_id=parsed.application_external_id,
        content_sha256=parsed.content_sha256,
        source_idempotency_key=parsed.idempotency_key,
        occurred_at=parsed.observed_at,
    )


def _normalize_contract_receipt(parsed: ContractReceipt) -> LedgerEvent:
    if parsed.status != "accepted":
        raise UnsupportedLedgerEvent(
            "contract receipt status is unsupported: {}".format(parsed.status)
        )
    return _build_event(
        parsed=parsed,
        event_type="order_awarded",
        external_id=parsed.contract_external_id,
        content_sha256=parsed.terms_sha256,
        source_idempotency_key=None,
        occurred_at=parsed.observed_at,
    )


def _normalize_work_event(parsed: WorkEvent) -> LedgerEvent:
    if parsed.event_type in _RECEIPT_ONLY_WORK_EVENTS:
        raise ReceiptRequiredError(
            "work event requires an authoritative receipt: {}".format(
                parsed.event_type
            )
        )
    if parsed.event_type not in _SUPPORTED_WORK_EVENTS:
        raise UnsupportedLedgerEvent(
            "work event type is unsupported: {}".format(parsed.event_type)
        )
    return _build_event(
        parsed=parsed,
        event_type=parsed.event_type,
        external_id=parsed.external_id,
        content_sha256=parsed.content_sha256,
        source_idempotency_key=None,
        occurred_at=parsed.occurred_at,
    )


def _normalize_delivery_receipt(parsed: DeliveryReceipt) -> LedgerEvent:
    if parsed.status == "submitted":
        event_type = "delivery_submitted"
    elif parsed.status == "verified":
        event_type = "delivery_verified"
    else:
        raise UnsupportedLedgerEvent(
            "delivery receipt status is unsupported: {}".format(parsed.status)
        )
    return _build_event(
        parsed=parsed,
        event_type=event_type,
        external_id=parsed.delivery_external_id,
        content_sha256=parsed.artifact_sha256,
        source_idempotency_key=parsed.idempotency_key,
        occurred_at=parsed.observed_at,
    )


def _normalize_payment_receipt(parsed: PaymentReceipt) -> LedgerEvent:
    if parsed.status != "settled":
        raise UnsupportedLedgerEvent(
            "payment receipt status is unsupported: {}".format(parsed.status)
        )
    content_sha256 = _canonical_fingerprint(parsed)
    return _build_event(
        parsed=parsed,
        event_type="payment_received",
        external_id=parsed.payment_external_id,
        content_sha256=content_sha256,
        source_idempotency_key=None,
        occurred_at=parsed.occurred_at,
        receipt_id=parsed.receipt_id,
        amount_minor=parsed.net_amount_minor,
        currency=parsed.currency,
    )


def normalize_event(value: Mapping[str, object]) -> LedgerEvent:
    """Normalize one validated marketplace contract into a ledger event."""

    if not isinstance(value, Mapping):
        _raise_schema_error(
            ContractValidationError(("$: expected_object",))
        )
    if value.get("record_type") == "payment_receipt" and not value.get(
        "receipt_id"
    ):
        raise ReceiptRequiredError("payment receipt requires a non-empty receipt_id")

    parsed = _parse_source(value)
    if isinstance(parsed, Opportunity):
        return _normalize_opportunity(parsed)
    if isinstance(parsed, ApplicationReceipt):
        return _normalize_application_receipt(parsed)
    if isinstance(parsed, ContractReceipt):
        return _normalize_contract_receipt(parsed)
    if isinstance(parsed, WorkEvent):
        return _normalize_work_event(parsed)
    if isinstance(parsed, DeliveryReceipt):
        return _normalize_delivery_receipt(parsed)
    if isinstance(parsed, PaymentReceipt):
        return _normalize_payment_receipt(parsed)
    if isinstance(parsed, (ApplicationIntent, DeliveryIntent)):
        raise ReceiptRequiredError(
            "{} requires an authoritative receipt".format(parsed.record_type)
        )
    raise LedgerSchemaError(
        "unsupported parsed contract type: {}".format(type(parsed).__name__)
    )


_LEDGER_EVENT_COLUMNS = (
    "schema_version",
    "idempotency_key",
    "event_type",
    "platform",
    "external_id",
    "source_record_type",
    "source_idempotency_key",
    "content_sha256",
    "fingerprint_sha256",
    "occurred_at",
    "observed_at",
    "receipt_id",
    "amount_minor",
    "currency",
)
_LEDGER_EVENT_SELECT = ", ".join(_LEDGER_EVENT_COLUMNS)
_EVENT_TYPES_SQL = (
    "'opportunity_seen', 'application_submitted', 'application_verified', "
    "'message_received', 'order_awarded', 'artifact_verified', "
    "'delivery_submitted', 'delivery_verified', 'payment_received'"
)
_PLATFORM_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,31}$")
_SAFE_INTEGER_MAX = 9007199254740991
_LEDGER_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ledger_meta (
    schema_version INTEGER NOT NULL
)
"""
_EVENTS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS marketplace_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version INTEGER NOT NULL CHECK (schema_version = 1),
    idempotency_key TEXT NOT NULL CHECK (
        typeof(idempotency_key) = 'text'
        AND length(CAST(idempotency_key AS BLOB)) > 0
        AND instr(idempotency_key, char(0)) = 0
    ),
    event_type TEXT NOT NULL CHECK (
        typeof(event_type) = 'text'
        AND event_type IN ({event_types})
    ),
    platform TEXT NOT NULL CHECK (
        typeof(platform) = 'text'
        AND length(CAST(platform AS BLOB)) BETWEEN 2 AND 32
        AND instr(platform, char(0)) = 0
        AND substr(platform, 1, 1) GLOB '[a-z]'
        AND substr(platform, 2) NOT GLOB '*[^a-z0-9_-]*'
    ),
    external_id TEXT NOT NULL CHECK (
        typeof(external_id) = 'text'
        AND length(CAST(external_id AS BLOB)) > 0
        AND instr(external_id, char(0)) = 0
    ),
    source_record_type TEXT NOT NULL CHECK (
        typeof(source_record_type) = 'text'
        AND length(CAST(source_record_type AS BLOB)) > 0
        AND instr(source_record_type, char(0)) = 0
    ),
    source_idempotency_key TEXT CHECK (
        source_idempotency_key IS NULL
        OR (
            typeof(source_idempotency_key) = 'text'
            AND length(CAST(source_idempotency_key AS BLOB)) > 0
            AND instr(source_idempotency_key, char(0)) = 0
        )
    ),
    content_sha256 TEXT NOT NULL CHECK (
        typeof(content_sha256) = 'text'
        AND length(CAST(content_sha256 AS BLOB)) = 64
        AND instr(content_sha256, char(0)) = 0
        AND content_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    fingerprint_sha256 TEXT NOT NULL CHECK (
        typeof(fingerprint_sha256) = 'text'
        AND length(CAST(fingerprint_sha256 AS BLOB)) = 64
        AND instr(fingerprint_sha256, char(0)) = 0
        AND fingerprint_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
    occurred_at TEXT NOT NULL CHECK (
        typeof(occurred_at) = 'text'
        AND length(CAST(occurred_at AS BLOB)) > 0
        AND instr(occurred_at, char(0)) = 0
    ),
    observed_at TEXT NOT NULL CHECK (
        typeof(observed_at) = 'text'
        AND length(CAST(observed_at AS BLOB)) > 0
        AND instr(observed_at, char(0)) = 0
    ),
    receipt_id TEXT,
    amount_minor INTEGER,
    currency TEXT,
    UNIQUE (idempotency_key),
    UNIQUE (platform, event_type, external_id),
    CHECK (
        (
            event_type = 'payment_received'
            AND source_record_type = 'payment_receipt'
            AND receipt_id IS NOT NULL
            AND typeof(receipt_id) = 'text'
            AND length(CAST(receipt_id AS BLOB)) > 0
            AND instr(receipt_id, char(0)) = 0
            AND typeof(amount_minor) = 'integer'
            AND amount_minor > 0
            AND amount_minor <= {safe_integer_max}
            AND currency IS NOT NULL
            AND typeof(currency) = 'text'
            AND length(CAST(currency AS BLOB)) = 3
            AND instr(currency, char(0)) = 0
            AND currency NOT GLOB '*[^A-Z]*'
        )
        OR
        (
            event_type <> 'payment_received'
            AND receipt_id IS NULL
            AND amount_minor IS NULL
            AND currency IS NULL
        )
    )
)
""".format(
    event_types=_EVENT_TYPES_SQL,
    safe_integer_max=_SAFE_INTEGER_MAX,
)
_RECEIPT_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS marketplace_events_platform_receipt
ON marketplace_events (platform, receipt_id)
WHERE receipt_id IS NOT NULL
"""
_SOURCE_IDEMPOTENCY_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS marketplace_events_platform_event_source_idempotency
ON marketplace_events (platform, event_type, source_idempotency_key)
WHERE source_idempotency_key IS NOT NULL
"""
# These statements are the only schema accepted for a v1 ledger.  The
# IF-NOT-EXISTS form is used for initialization; SQLite's sqlite_master text
# is compared against the representation produced by these same statements.
_CANONICAL_LEDGER_SCHEMA_SQL = _LEDGER_SCHEMA_SQL
_CANONICAL_EVENTS_SCHEMA_SQL = _EVENTS_SCHEMA_SQL
_CANONICAL_RECEIPT_INDEX_SQL = _RECEIPT_INDEX_SQL
_CANONICAL_SOURCE_IDEMPOTENCY_INDEX_SQL = _SOURCE_IDEMPOTENCY_INDEX_SQL
_SCHEMA_SHAPE_ERROR = "ledger_schema_shape_invalid"
_INITIALIZE_RETRY_SECONDS = 12.0
_INITIALIZE_RETRY_INITIAL_DELAY = 0.01
_INITIALIZE_RETRY_MAX_DELAY = 0.5
_INITIALIZE_LOCK = threading.Lock()


def _raise_storage_error(exc: BaseException) -> None:
    raise LedgerError("ledger_persistence_error") from exc


def _rollback_safely(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("ROLLBACK")
    except sqlite3.Error:
        return None


def _is_transient_sqlite_error(exc: BaseException) -> bool:
    current: Optional[BaseException] = exc
    while current is not None:
        if isinstance(current, sqlite3.OperationalError):
            message = str(current).lower()
            return "locked" in message or "busy" in message
        current = current.__cause__
    return False


def _compact_schema_sql(value: str) -> str:
    """Remove insignificant whitespace while preserving SQL literals/comments."""

    compact: List[str] = []
    in_string = False
    index = 0
    while index < len(value):
        character = value[index]
        if character == "'":
            compact.append(character)
            if in_string and index + 1 < len(value) and value[index + 1] == "'":
                compact.append(value[index + 1])
                index += 2
                continue
            in_string = not in_string
        elif not in_string and character.isspace():
            index += 1
            continue
        else:
            compact.append(character)
        index += 1
    return "".join(compact)


def _raise_schema_shape_error() -> None:
    raise LedgerSchemaError(_SCHEMA_SHAPE_ERROR)


def _schema_master_signature(
    connection: sqlite3.Connection,
) -> tuple:
    rows = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()
    return tuple(
        (
            row[0],
            row[1],
            row[2],
            _compact_schema_sql(row[3]) if isinstance(row[3], str) else row[3],
        )
        for row in rows
    )


def _table_info_signature(
    connection: sqlite3.Connection, table_name: str
) -> tuple:
    rows = connection.execute(
        "PRAGMA table_info({})".format(table_name)
    ).fetchall()
    return tuple(
        (row[1], row[2], row[3], row[4], row[5])
        for row in rows
    )


def _index_signature(connection: sqlite3.Connection, table_name: str) -> tuple:
    index_rows = connection.execute(
        "PRAGMA index_list({})".format(table_name)
    ).fetchall()
    signatures = []
    for index_row in index_rows:
        index_name = index_row[1]
        info_rows = connection.execute(
            """
            SELECT seqno, name
            FROM pragma_index_info(?)
            ORDER BY seqno
            """,
            (index_name,),
        ).fetchall()
        xinfo_rows = connection.execute(
            """
            SELECT seqno, cid, name, "desc", coll
            FROM pragma_index_xinfo(?)
            ORDER BY seqno
            """,
            (index_name,),
        ).fetchall()
        signatures.append(
            (
                index_name,
                index_row[2],
                index_row[3],
                index_row[4],
                tuple((row[0], row[1]) for row in info_rows),
                tuple(tuple(row) for row in xinfo_rows),
            )
        )
    signatures.sort(key=lambda signature: signature[0])
    return tuple(signatures)


def _schema_snapshot(connection: sqlite3.Connection) -> tuple:
    return (
        _schema_master_signature(connection),
        tuple(
            (
                table_name,
                _table_info_signature(connection, table_name),
                _index_signature(connection, table_name),
            )
            for table_name in ("ledger_meta", "marketplace_events")
        ),
    )


def _canonical_schema_snapshot() -> tuple:
    expected = sqlite3.connect(":memory:", isolation_level=None)
    try:
        expected.executescript(_CANONICAL_LEDGER_SCHEMA_SQL)
        expected.executescript(_CANONICAL_EVENTS_SCHEMA_SQL)
        expected.executescript(_CANONICAL_RECEIPT_INDEX_SQL)
        expected.executescript(_CANONICAL_SOURCE_IDEMPOTENCY_INDEX_SQL)
        return _schema_snapshot(expected)
    finally:
        expected.close()


def _validate_schema_shape(connection: sqlite3.Connection) -> None:
    """Reject any pre-existing v1 database that is not exactly canonical."""

    try:
        if _schema_snapshot(connection) != _canonical_schema_snapshot():
            _raise_schema_shape_error()
    except LedgerSchemaError:
        raise
    except (sqlite3.Error, IndexError, TypeError, ValueError):
        _raise_schema_shape_error()


def _initialize(connection: sqlite3.Connection) -> None:
    """Create the v1 ledger schema and reject an unknown metadata version."""

    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(_LEDGER_SCHEMA_SQL)
        connection.execute(_EVENTS_SCHEMA_SQL)
        try:
            connection.execute(_RECEIPT_INDEX_SQL)
            connection.execute(_SOURCE_IDEMPOTENCY_INDEX_SQL)
        except sqlite3.Error as exc:
            if _is_transient_sqlite_error(exc):
                raise
            raise LedgerSchemaError(_SCHEMA_SHAPE_ERROR) from None
        _validate_schema_shape(connection)
        rows = connection.execute(
            "SELECT schema_version FROM ledger_meta"
        ).fetchall()
        if not rows:
            connection.execute(
                "INSERT INTO ledger_meta (schema_version) VALUES (?)", (1,)
            )
        elif len(rows) != 1 or rows[0][0] != 1:
            raise LedgerSchemaError("ledger_schema_version_unsupported")
        connection.execute("COMMIT")
    except LedgerSchemaError:
        _rollback_safely(connection)
        raise
    except sqlite3.Error as exc:
        _rollback_safely(connection)
        _raise_storage_error(exc)


def _chmod_owner_only(path: Path) -> None:
    try:
        path.chmod(0o600)
    except FileNotFoundError:
        return None


def _restore_owner_only_permissions(database: Path) -> None:
    _chmod_owner_only(database)
    for suffix in ("-wal", "-shm"):
        _chmod_owner_only(database.with_name(database.name + suffix))


def _connect(database: Path) -> sqlite3.Connection:
    """Open an owner-only SQLite connection and initialize the v1 schema."""

    path = Path(database)
    try:
        connection = sqlite3.connect(
            str(path), timeout=10, isolation_level=None
        )
    except sqlite3.Error as exc:
        _raise_storage_error(exc)
    deadline = time.monotonic() + _INITIALIZE_RETRY_SECONDS
    delay = _INITIALIZE_RETRY_INITIAL_DELAY
    while True:
        try:
            with _INITIALIZE_LOCK:
                _restore_owner_only_permissions(path)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA busy_timeout = 10000")
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = FULL")
                _initialize(connection)
                _restore_owner_only_permissions(path)
            return connection
        except LedgerSchemaError:
            connection.close()
            raise
        except LedgerError as exc:
            if not _is_transient_sqlite_error(exc):
                connection.close()
                raise
            last_error: BaseException = exc
        except (OSError, sqlite3.Error) as exc:
            if not _is_transient_sqlite_error(exc):
                connection.close()
                _raise_storage_error(exc)
            last_error = exc

        _rollback_safely(connection)
        if time.monotonic() >= deadline:
            connection.close()
            _raise_storage_error(last_error)
        time.sleep(delay)
        delay = min(delay * 2, _INITIALIZE_RETRY_MAX_DELAY)


def _row_to_event(row: Mapping[str, object]) -> LedgerEvent:
    """Convert one selected SQLite row without retaining source payload text."""

    values = {column: row[column] for column in _LEDGER_EVENT_COLUMNS}
    return LedgerEvent(**values)  # type: ignore[arg-type]


def _conflict() -> IdempotencyConflict:
    return IdempotencyConflict()


def append_event(database: Path, value: Mapping[str, object]) -> bool:
    """Persist one normalized event, returning false for an exact replay."""

    event = normalize_event(value)
    database_path = Path(database)
    connection = _connect(database)
    try:
        connection.execute("BEGIN IMMEDIATE")

        business_row = connection.execute(
            """
            SELECT idempotency_key, fingerprint_sha256
            FROM marketplace_events
            WHERE platform = ? AND event_type = ? AND external_id = ?
            """,
            (event.platform, event.event_type, event.external_id),
        ).fetchone()
        if business_row is not None:
            if (
                business_row["idempotency_key"] == event.idempotency_key
                and business_row["fingerprint_sha256"] == event.fingerprint_sha256
            ):
                connection.execute("COMMIT")
                _restore_owner_only_permissions(database_path)
                return False
            raise _conflict()

        idempotency_row = connection.execute(
            """
            SELECT fingerprint_sha256
            FROM marketplace_events
            WHERE idempotency_key = ?
            """,
            (event.idempotency_key,),
        ).fetchone()
        if idempotency_row is not None:
            raise _conflict()

        if event.source_idempotency_key is not None:
            source_idempotency_row = connection.execute(
                """
                SELECT sequence
                FROM marketplace_events
                WHERE platform = ?
                AND event_type = ?
                AND source_idempotency_key = ?
                """,
                (
                    event.platform,
                    event.event_type,
                    event.source_idempotency_key,
                ),
            ).fetchone()
            if source_idempotency_row is not None:
                raise _conflict()

        if event.receipt_id is not None:
            receipt_row = connection.execute(
                """
                SELECT sequence
                FROM marketplace_events
                WHERE platform = ? AND receipt_id = ?
                """,
                (event.platform, event.receipt_id),
            ).fetchone()
            if receipt_row is not None:
                raise _conflict()

        values = tuple(getattr(event, column) for column in _LEDGER_EVENT_COLUMNS)
        bind_markers = ", ".join("?" for _ in _LEDGER_EVENT_COLUMNS)
        connection.execute(
            "INSERT INTO marketplace_events ({}) VALUES ({})".format(
                _LEDGER_EVENT_SELECT, bind_markers
            ),
            values,
        )
        connection.execute("COMMIT")
        _restore_owner_only_permissions(database_path)
        return True
    except IdempotencyConflict:
        _rollback_safely(connection)
        raise
    except sqlite3.Error as exc:
        _rollback_safely(connection)
        _raise_storage_error(exc)
    finally:
        connection.close()


def list_events(database: Path) -> List[LedgerEvent]:
    """Return normalized events in append sequence order."""

    connection = _connect(database)
    try:
        rows = connection.execute(
            "SELECT {} FROM marketplace_events ORDER BY sequence ASC".format(
                _LEDGER_EVENT_SELECT
            )
        ).fetchall()
        return [_row_to_event(row) for row in rows]
    except sqlite3.Error as exc:
        _raise_storage_error(exc)
    finally:
        connection.close()


def _validate_event_type_filter(event_type: Optional[str]) -> None:
    if not isinstance(event_type, str) or event_type not in _ALLOWED_EVENT_TYPES:
        raise LedgerSchemaError("ledger_event_type_invalid")


def _validate_platform_filter(platform: Optional[str]) -> None:
    if not isinstance(platform, str) or _PLATFORM_PATTERN.fullmatch(platform) is None:
        raise LedgerSchemaError("ledger_platform_invalid")


def event_count(database: Path, event_type: Optional[str] = None) -> int:
    """Count all ledger events or one exact allowed event type."""

    if event_type is not None:
        _validate_event_type_filter(event_type)

    connection = _connect(database)
    try:
        if event_type is None:
            row = connection.execute(
                "SELECT COUNT(*) AS event_count FROM marketplace_events"
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT COUNT(*) AS event_count
                FROM marketplace_events
                WHERE event_type = ?
                """,
                (event_type,),
            ).fetchone()
        return int(row["event_count"] if row is not None else 0)
    except sqlite3.Error as exc:
        _raise_storage_error(exc)
    finally:
        connection.close()


def received_totals(
    database: Path, platform: Optional[str] = None
) -> Dict[str, int]:
    """Sum unique received payment receipts by currency without conversion."""

    if platform is not None:
        _validate_platform_filter(platform)

    connection = _connect(database)
    try:
        query = (
            "SELECT currency, amount_minor "
            "FROM marketplace_events "
            "WHERE event_type = ? "
            "AND source_record_type = ? "
            "AND receipt_id IS NOT NULL"
        )
        parameters = ["payment_received", "payment_receipt"]
        if platform is not None:
            query += " AND platform = ?"
            parameters.append(platform)
        query += " ORDER BY currency ASC, sequence ASC"

        rows = connection.execute(query, tuple(parameters)).fetchall()
        totals = {}
        for row in rows:
            currency = str(row["currency"])
            totals[currency] = totals.get(currency, 0) + int(row["amount_minor"])
        return totals
    except sqlite3.Error as exc:
        _raise_storage_error(exc)
    finally:
        connection.close()


__all__ = [
    "IdempotencyConflict",
    "LedgerError",
    "LedgerEvent",
    "LedgerSchemaError",
    "ReceiptRequiredError",
    "UnsupportedLedgerEvent",
    "append_event",
    "event_count",
    "list_events",
    "normalize_event",
    "received_totals",
]
