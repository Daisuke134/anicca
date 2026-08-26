from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


class MercorOperatorError(ValueError):
    pass


_OPERATOR_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@dataclass(frozen=True)
class MercorOperatorConfig:
    operator_id: str
    profile_path: str
    resume_path: str
    state_root: str
    locales: tuple[str, ...]
    role_families: tuple[str, ...]
    weekly_hours: int
    exclusions: tuple[str, ...]


def operator_state_root(operator_id: str, *, base_root: Path) -> Path:
    if not isinstance(operator_id, str) or not _OPERATOR_ID.fullmatch(operator_id):
        raise MercorOperatorError("operator_id must be a safe 1-64 character identifier")
    root = Path(base_root).expanduser().resolve() / operator_id / "mercor"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def create_operator_config(
    *,
    operator_id: str,
    profile_path: Path,
    resume_path: Path,
    base_root: Path,
    locales: Iterable[str],
    role_families: Iterable[str],
    weekly_hours: int,
    exclusions: Iterable[str] = (),
) -> MercorOperatorConfig:
    profile = Path(profile_path).expanduser().resolve()
    resume = Path(resume_path).expanduser().resolve()
    if not profile.is_file() or not resume.is_file():
        raise MercorOperatorError("profile_path and resume_path must be existing files")
    if not isinstance(weekly_hours, int) or isinstance(weekly_hours, bool) or not 1 <= weekly_hours <= 80:
        raise MercorOperatorError("weekly_hours must be between 1 and 80")

    def clean(values: Iterable[str], name: str) -> tuple[str, ...]:
        cleaned = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
        if not cleaned:
            raise MercorOperatorError(f"{name} must contain at least one value")
        return cleaned

    state_root = operator_state_root(operator_id, base_root=base_root)
    config = MercorOperatorConfig(
        operator_id=operator_id,
        profile_path=str(profile),
        resume_path=str(resume),
        state_root=str(state_root),
        locales=clean(locales, "locales"),
        role_families=clean(role_families, "role_families"),
        weekly_hours=weekly_hours,
        exclusions=tuple(sorted({str(value).strip() for value in exclusions if str(value).strip()})),
    )
    target = state_root / "operator.json"
    temporary = state_root / f".operator.json.tmp-{os.getpid()}"
    temporary.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(target)
    os.chmod(target, 0o600)
    return config
