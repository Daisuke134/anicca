"""Offline annotation boundary; no change to Manager assignment or delivery."""
import json
from pathlib import Path

CATALOG = Path(__file__).with_name('bcto_subset.json')


def annotate(candidate, technique_ids, *, reviewer):
    """Attach explicit research coding, never infer BCT from candidate kind.

    Empty coding is unclassified, except a valid no-action candidate.
    Review identity is provenance, not proof of semantic validity or efficacy.
    """
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError('missing coding provenance')
    if not isinstance(technique_ids, list) or any(type(t) is not str for t in technique_ids):
        raise ValueError('expected list of ontology IDs')
    if len(set(technique_ids)) != len(technique_ids) or not set(technique_ids) <= set(catalog['terms']):
        raise ValueError('duplicate or unknown ontology ID')
    if candidate['kind'] == 'none':
        if technique_ids or candidate['text'] != '':
            raise ValueError('no action cannot be coded as delivered BCT')
        status = 'NO_ACTION'
    else:
        if not isinstance(candidate['text'], str) or not candidate['text'].strip():
            raise ValueError('empty intervention')
        status = 'PROPOSED_CODING' if technique_ids else 'UNCLASSIFIED'
    return {'candidate_id': candidate['id'], 'bct_ids': technique_ids[:],
            'coding_status': status, 'coded_by': reviewer,
            'ontology_revision': catalog['revision'], 'effect_validated': False}
