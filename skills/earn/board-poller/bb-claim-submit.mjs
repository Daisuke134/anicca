import { privateKeyToAccount } from "viem/accounts";
import { readFileSync } from "node:fs";
const JOB="87b131ee-7102-4d69-a99d-08cff67e9c1a";
const CODE=`class StateMachine:
    def __init__(self, initial_state):
        self._state = initial_state
        self._transitions = {}

    @property
    def state(self):
        return self._state

    def add_transition(self, from_state, event, to_state, guard=None):
        self._transitions.setdefault((from_state, event), []).append((to_state, guard))

    def trigger(self, event, **context):
        candidates = self._transitions.get((self._state, event))
        if not candidates:
            raise ValueError("no transition for event %r from state %r" % (event, self._state))
        for to_state, guard in candidates:
            if guard is None or guard(context):
                self._state = to_state
                return True
        return False
`;
const w=JSON.parse(readFileSync(process.env.HOME+"/.anicca-founder/wallet.json","utf8"));
let pk=w.private_key.startsWith("0x")?w.private_key:"0x"+w.private_key;
const acct=privateKeyToAccount(pk);const addr=acct.address;const API="https://api.bountybook.ai";
const n=await(await fetch(`${API}/auth/nonce?address=${addr}`)).json();
const sig=await acct.signMessage({message:String(n.nonce||n.message||n)});
const v=await(await fetch(`${API}/auth/verify`,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({address:addr,signature:sig})})).json();
const H={Authorization:"Bearer "+v.token,"content-type":"application/json"};
console.log("addr",addr);
const claim=await fetch(`${API}/jobs/${JOB}/claim`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr})});
console.log("CLAIM",claim.status,(await claim.text()).slice(0,200));
const outputData={"state_machine.py":CODE};
const sub=await fetch(`${API}/jobs/${JOB}/submit`,{method:"POST",headers:H,body:JSON.stringify({executorAddress:addr,outputData})});
console.log("SUBMIT",sub.status,(await sub.text()).slice(0,500));
