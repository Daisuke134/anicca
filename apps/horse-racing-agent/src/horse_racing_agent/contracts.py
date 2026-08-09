class RegistryDependencyBlocked(RuntimeError):
    """Raised when the CFO registry dependency is not complete."""


def build_horse_racing_candidate(
    *,
    cfo_exact_seven_complete: bool,
    hra6_compliance_receipts_complete: bool,
    requested_live_purchase: bool = False,
) -> dict[str, object]:
    if not cfo_exact_seven_complete:
        raise RegistryDependencyBlocked("CFO-0c exact-seven is incomplete")

    return {
        "registry": "v2",
        "business_id": "horse_racing",
        "candidate_ordinal": 8,
        "depends_on": "CFO-0c exact-seven",
        "live_purchase": "disabled",
    }
