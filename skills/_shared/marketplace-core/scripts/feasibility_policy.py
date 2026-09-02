"""Shared semantic admission policy for gig-market application planners."""


def common_marketplace_feasibility_policy() -> str:
    """Return the provider-neutral policy used to decide whether to apply."""
    return """COMMON MARKETPLACE FEASIBILITY POLICY:
- Apply broadly to every legal opportunity whose required outcome the general agent can truthfully
  complete using computer, browser, coding, research, writing, design, data and other available tools.
- Installed Skills are execution recipes after selection, never an application whitelist. Missing an
  exact Skill, tool history, domain job, testimonial, portfolio item or prior client result is never by
  itself a reason to skip. Compose or build the execution method after contract while making no false
  claim about prior experience.
- Submit is the default for every feasible job, especially high-value work. A proposal is not contract
  acceptance: missing budget/rate, unverified payment, a new client, low hire history, competition,
  high application-token cost, long advertised duration or unclear ordinary implementation details
  are ranking/price/question inputs, never standalone skip reasons. Skip for economics only when the
  official displayed compensation makes every truthful scoped offer clearly negative after cost.
- Skip only when the actual required outcome is illegal/scam, requires unavoidable physical/on-site
  work, mandatory human face/voice/phone/live presence, a legal qualification or immutable identity
  fact that cannot be supplied truthfully, off-platform payment/contact, explicit AI prohibition, or
  scope/deadline/economics the general agent truly cannot complete.
- Preserve scope fidelity: do not make infeasible work appear feasible by silently replacing the
  buyer's required outcome with a smaller or different deliverable. Ask concise pre-contract questions
  when ordinary implementation details are missing.
- Never invent experience or credentials. State verified transferable facts and a concrete plan, but
  missing experience does not convert feasible work into prohibited work."""
