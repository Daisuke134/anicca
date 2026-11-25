"""Offline projection of explicit goal events into Graphiti edge arguments.
No text extraction, database writes, identity lookup or intervention delivery.
"""
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5


def _utc(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError('timezone-aware datetime required')
    return value.astimezone(timezone.utc)


def _id(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError('canonical opaque UUID required')
    return value


def project(*, owner, branch, event_id, goal_id, kind, observed_at,
            recorded_at, intended_at=None):
    """Owner/branch must be trusted server scopes, not caller-supplied identity.
    Plan is evidence of intent only; completion requires an explicit observation.
    Caller owns consent, retention and source authenticity checks.
    """
    owner, branch, event_id, goal_id = map(_id, (owner, branch, event_id, goal_id))
    observed, recorded = _utc(observed_at), _utc(recorded_at)
    if observed > recorded:
        raise ValueError('future observation')
    if kind not in ('goal_plan', 'goal_completion'):
        raise ValueError('unsupported assertion type')
    if kind == 'goal_completion' and intended_at is not None:
        raise ValueError('planned timestamp is not completion evidence')
    intended = _utc(intended_at) if intended_at is not None else None
    if intended is not None and intended < observed:
        raise ValueError('intention date precedes assertion')
    scope = uuid5(NAMESPACE_URL, 'anicca:graphiti:' + owner + ':' + branch)
    return dict(uuid=str(uuid5(scope, 'event:' + event_id)), group_id=str(scope),
                source_node_uuid=str(uuid5(scope, 'person')),
                target_node_uuid=str(uuid5(scope, 'goal:' + goal_id)),
                name='HAS_PLAN' if kind == 'goal_plan' else 'REPORTED_COMPLETION',
                fact='Explicit reported goal plan' if kind == 'goal_plan' else 'Explicit reported goal completion',
                created_at=recorded, valid_at=observed, invalid_at=None,
                reference_time=observed, attributes={'source_event_id': event_id,
                'assertion_kind': kind, 'recorded_at': recorded.isoformat(),
                'intended_at': intended.isoformat() if intended else None})


def to_edge(**kwargs):
    from graphiti_core.edges import EntityEdge
    return EntityEdge(**project(**kwargs))
