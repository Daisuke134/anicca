"""Inspect the REAL CC-BY-4.0 BCIO OWL file. Do not vendor it.

External dependency: clone the official HumanBehaviourChangeProject/ontologies
repo to a temporary directory, then pass --owl to this script.

No API, no training, no human information, no graph DB.

Run: python3 bcio_owl_snapshot_audit.py --owl /path/to/bcio.owl
"""
from __future__ import annotations
from xml.etree import ElementTree as ET
from hashlib import sha256
from pathlib import Path
import argparse
import json

RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
OWL = "{http://www.w3.org/2002/07/owl#}"
EXAMPLES = {
    "BCIO_001000": "behaviour change intervention scenario",
    "BCIO_003000": "behaviour change intervention",
    "BCIO_006133": "behavioural motivation",
    "BCIO_007024": "self-monitor behaviour BCT",
    "BCIO_050829": "purchasing behaviour",
    "BCIO_050937": "behavioural goal",
    "BCIO_051025": "intervention context",
}

def run(path: Path) -> dict:
    raw=path.read_bytes()
    root=ET.fromstring(raw)
    class_nodes=root.findall(f".//{OWL}Class")
    labels={}
    for item in class_nodes:
        uri=item.attrib.get(RDF+"about","")
        label=item.find(RDFS+"label")
        if uri and label is not None and label.text:
            labels[uri.rsplit("/",1)[-1]]=label.text.strip()
    sampled={}
    for bcio_id,expected in EXAMPLES.items():
        got=labels.get(bcio_id)
        if got!=expected:
            raise AssertionError((bcio_id,got,expected))
        sampled[bcio_id]={"label":got,
                          "iri":f"http://humanbehaviourchange.org/ontology/{bcio_id}"}
    return {
        "source_repo":"https://github.com/HumanBehaviourChangeProject/ontologies",
        "license":"Creative Commons Attribution 4.0 International, attribution required",
        "source_bytes":len(raw),
        "source_sha256":sha256(raw).hexdigest(),
        "owl_class_declarations_including_imports":len(class_nodes),
        "mapped_label_examples":sampled,
        "scope":"verified OWL vocabulary labels only; not a deployed prediction model",
        "intervention_effect_validated":False,
    }

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--owl",type=Path,required=True)
    args=parser.parse_args()
    result=run(args.owl)
    out=Path(__file__).resolve().parent.parent/"evidence/BCIO_REAL_OWL_SNAPSHOT_AUDIT.json"
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
