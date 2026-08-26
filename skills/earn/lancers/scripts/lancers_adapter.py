"""Pure normalization for public Lancers work cards.

The adapter accepts provider-shaped dictionaries produced by the read-only
HTML parser and returns the shared marketplace ``Opportunity`` wire shape.
It never performs network, browser, credential, or persistence work.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, DecimalException
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit


_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_MAX_TEXT_LENGTH = 200_000
_MISSING = object()
_RFC3339_RE = re.compile(
    r"^[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])[Tt]"
    r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]+)?"
    r"(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])$"
)
_DECIMAL_TEXT_RE = re.compile(r"^[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$")
_ID_RE = re.compile(r"^[1-9][0-9]{0,511}$")
_DETAIL_URL_RE = re.compile(r"^/work/detail/([1-9][0-9]{0,511})$")
_CURRENCY_EXPONENTS = {"JPY": 0}


class LancersProjectError(ValueError):
    """Privacy-safe, stable validation failure for one public work card."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise LancersProjectError(code) from None


_CONTRACTS_MODULE_NAME = "_anicca_lancers_marketplace_contracts_v1"
_CONTRACTS: Any = None


def _load_contracts() -> Any:
    global _CONTRACTS
    if _CONTRACTS is not None:
        return _CONTRACTS
    contract_path = (
        Path(__file__).resolve().parents[3]
        / "_shared"
        / "marketplace-core"
        / "scripts"
        / "contracts.py"
    )
    spec = importlib.util.spec_from_file_location(_CONTRACTS_MODULE_NAME, contract_path)
    if spec is None or spec.loader is None:
        raise ImportError("lancers_contracts_unavailable")
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(_CONTRACTS_MODULE_NAME, _MISSING)
    sys.modules[_CONTRACTS_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is _MISSING:
            sys.modules.pop(_CONTRACTS_MODULE_NAME, None)
        else:
            sys.modules[_CONTRACTS_MODULE_NAME] = previous
    _CONTRACTS = module
    return module


def _text(value: object, code: str, *, max_length: int = _MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        _fail(code)
    normalized = value.strip()
    if not normalized or len(normalized) > max_length:
        _fail(code)
    if any(ord(character) < 0x20 and character not in "\n\r\t" for character in normalized):
        _fail(code)
    if any(0x7F <= ord(character) <= 0x9F for character in normalized):
        _fail(code)
    return normalized


def _observed_at(value: object) -> str:
    if not isinstance(value, str) or _RFC3339_RE.fullmatch(value) is None:
        _fail("observed_at_invalid")
    candidate = value[:10] + "T" + value[11:]
    if candidate[-1] in "Zz":
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except (TypeError, ValueError, OverflowError):
        _fail("observed_at_invalid")
    if parsed.tzinfo is None:
        _fail("observed_at_invalid")
    return value


def _external_id(value: object) -> str:
    if isinstance(value, bool):
        _fail("project_id_invalid")
    if isinstance(value, int):
        if value <= 0 or value > _MAX_SAFE_INTEGER:
            _fail("project_id_invalid")
        return str(value)
    if isinstance(value, str):
        normalized = value.strip()
        if _ID_RE.fullmatch(normalized) is None:
            _fail("project_id_invalid")
        try:
            if int(normalized, 10) > _MAX_SAFE_INTEGER:
                _fail("project_id_invalid")
        except (TypeError, ValueError, OverflowError):
            _fail("project_id_invalid")
        return normalized
    _fail("project_id_invalid")
    return ""


def _url(value: object, external_id: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("project_url_invalid")
    raw = value.strip()
    parsed = urlsplit(raw)
    if parsed.scheme not in {"https"} or parsed.netloc not in {"www.lancers.jp", "lancers.jp"}:
        _fail("project_url_invalid")
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        _fail("project_url_invalid")
    match = _DETAIL_URL_RE.fullmatch(parsed.path)
    if match is None or match.group(1) != external_id:
        _fail("project_url_invalid")
    return "https://www.lancers.jp" + parsed.path


def _category(value: object) -> str:
    if isinstance(value, str):
        return _text(value, "project_category_invalid", max_length=512)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        values = []
        for item in value:
            if not isinstance(item, str):
                _fail("project_category_invalid")
            clean = item.strip()
            if clean:
                values.append(clean)
        if values:
            return ", ".join(dict.fromkeys(values))
    _fail("project_category_invalid")
    return ""


def _buyer(value: object) -> Optional[str]:
    if value is None or value is _MISSING:
        return None
    return _text(value, "project_buyer_invalid", max_length=512)


def _currency(value: object, *, required: bool) -> Optional[str]:
    if value is _MISSING or value is None:
        if required:
            _fail("project_currency_invalid")
        return None
    if not isinstance(value, str) or value not in _CURRENCY_EXPONENTS:
        _fail("project_currency_invalid")
    return value


def _minor_units(value: object, exponent: int) -> int:
    if isinstance(value, bool):
        _fail("project_budget_invalid")
    if isinstance(value, int):
        if value < 0 or value > _MAX_SAFE_INTEGER:
            _fail("project_budget_invalid")
        return value * (10**exponent) if value <= _MAX_SAFE_INTEGER // (10**exponent) else _fail("project_budget_invalid")
    if isinstance(value, Decimal):
        decimal_value = value
    elif isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if not normalized or len(normalized) > 128 or _DECIMAL_TEXT_RE.fullmatch(normalized) is None:
            _fail("project_budget_invalid")
        try:
            decimal_value = Decimal(normalized)
        except (DecimalException, TypeError, ValueError):
            _fail("project_budget_invalid")
    elif isinstance(value, float):
        # Provider HTML is parsed as text; accepting finite floats is useful to
        # callers while Decimal(str()) avoids binary rounding surprises.
        try:
            decimal_value = Decimal(str(value))
        except (DecimalException, TypeError, ValueError):
            _fail("project_budget_invalid")
    else:
        _fail("project_budget_invalid")
    if not decimal_value.is_finite() or decimal_value < 0:
        _fail("project_budget_invalid")
    try:
        scaled = decimal_value * (10**exponent)
    except (DecimalException, ArithmeticError, OverflowError):
        _fail("project_budget_invalid")
    if scaled != scaled.to_integral_value() or scaled > _MAX_SAFE_INTEGER:
        _fail("project_budget_invalid")
    return int(scaled)


def _budget_type(value: object) -> str:
    if value is None or value is _MISSING or value == "":
        return "unknown"
    if not isinstance(value, str):
        _fail("project_type_invalid")
    normalized = value.strip().lower()
    if normalized in {"fixed", "project", "プロジェクト", "タスク", "固定"}:
        return "fixed"
    if normalized in {"hourly", "time", "時間報酬", "時間単価"}:
        return "hourly"
    if normalized in {"contest", "competition", "コンペ"}:
        return "contest"
    if normalized in {"bounty", "懸賞"}:
        return "bounty"
    return "unknown"


def _budget(project: Mapping[str, object]) -> Tuple[str, Optional[int], Optional[int], Optional[str]]:
    raw_min = project.get("budget_min", _MISSING)
    raw_max = project.get("budget_max", _MISSING)
    supplied = raw_min is not _MISSING or raw_max is not _MISSING
    if not supplied:
        return _budget_type(project.get("budget_type", _MISSING)), None, None, None
    if raw_min is _MISSING:
        raw_min = raw_max
    if raw_max is _MISSING:
        raw_max = raw_min
    if raw_min is None and raw_max is None:
        return _budget_type(project.get("budget_type", _MISSING)), None, None, None
    currency = _currency(project.get("currency", _MISSING), required=True)
    assert currency is not None
    exponent = _CURRENCY_EXPONENTS[currency]
    minimum = _minor_units(raw_min, exponent)
    maximum = _minor_units(raw_max, exponent)
    if minimum > maximum:
        _fail("project_budget_invalid")
    return _budget_type(project.get("budget_type", _MISSING)), minimum, maximum, currency


def normalize_project(project: Mapping[str, object], *, observed_at: str) -> Dict[str, object]:
    """Normalize one public Lancers card into a validated Opportunity dict."""

    if not isinstance(project, Mapping):
        _fail("project_not_mapping")
    observation = _observed_at(observed_at)
    external_id = _external_id(project.get("id", _MISSING))
    title = _text(project.get("title", _MISSING), "project_title_invalid")
    description = _text(project.get("description", _MISSING), "project_description_invalid")
    category = _category(project.get("category", _MISSING))
    buyer = _buyer(project.get("buyer_external_id", _MISSING))
    budget_type, budget_min, budget_max, currency = _budget(project)
    result: Dict[str, object] = {
        "schema_version": 1,
        "record_type": "opportunity",
        "platform": "lancers",
        "external_id": external_id,
        "title": title,
        "description": description,
        "url": _url(project.get("url", _MISSING), external_id),
        "category": category,
        "budget_type": budget_type,
        "budget_min_minor": budget_min,
        "budget_max_minor": budget_max,
        "currency": currency,
        "buyer_external_id": buyer,
        "observed_at": observation,
    }
    contracts = _load_contracts()
    try:
        contracts.parse_contract(result)
    except contracts.ContractValidationError:
        _fail("project_contract_invalid")
    return result


def normalize_projects(
    projects: Sequence[Mapping[str, object]], *, observed_at: str
) -> Tuple[List[Dict[str, object]], List[str]]:
    """Normalize provider cards, retaining order and privacy-safe rejection codes."""

    if isinstance(projects, (str, bytes, bytearray)) or not isinstance(projects, Sequence):
        _fail("projects_not_sequence")
    _observed_at(observed_at)
    normalized: List[Dict[str, object]] = []
    rejected: List[str] = []
    for index, project in enumerate(projects):
        try:
            normalized.append(normalize_project(project, observed_at=observed_at))
        except LancersProjectError as error:
            rejected.append(f"{index}:{error.code}")
    return normalized, rejected


def normalize_contract_receipt(source: Mapping[str, object], *, observed_at: str) -> Dict[str, object]:
    """Map one officially funded working project to the shared contract receipt."""

    if not isinstance(source, Mapping) or source.get("source_kind") != "project":
        _fail("contract_source_invalid")
    if source.get("status") != "進行中" or source.get("funding_status") != "escrow_confirmed":
        _fail("contract_funding_unverified")
    project_id = _external_id(source.get("project_id", _MISSING))
    proposal_id = _external_id(source.get("proposal_id", _MISSING))
    price = source.get("price_jpy")
    if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or price > _MAX_SAFE_INTEGER:
        _fail("contract_terms_invalid")
    due = source.get("delivery_due_on")
    try:
        if not isinstance(due, str) or datetime.strptime(due, "%Y-%m-%d").strftime("%Y-%m-%d") != due:
            _fail("contract_terms_invalid")
    except ValueError:
        _fail("contract_terms_invalid")
    proposal = _text(source.get("proposal_text", _MISSING), "contract_terms_invalid", max_length=10000)
    terms = {"price_jpy": price, "delivery_due_on": due, "proposal_text": proposal}
    receipt: Dict[str, object] = {
        "schema_version": 1,
        "record_type": "contract_receipt",
        "platform": "lancers",
        "application_external_id": proposal_id,
        "work_external_id": project_id,
        "contract_external_id": f"project:{project_id}",
        "status": "accepted",
        "terms_sha256": hashlib.sha256(
            json.dumps(terms, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "observed_at": _observed_at(observed_at),
    }
    contracts = _load_contracts()
    try:
        contracts.parse_contract(receipt)
    except contracts.ContractValidationError:
        _fail("contract_receipt_invalid")
    return receipt


__all__ = ["LancersProjectError", "normalize_contract_receipt", "normalize_project", "normalize_projects"]
