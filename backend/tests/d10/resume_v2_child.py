"""Private child-process continuation for owned fictional V2 checkpoint tests."""
from contextlib import redirect_stdout,redirect_stderr
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    with open(os.devnull,"w",encoding="utf-8") as sink,redirect_stdout(sink),redirect_stderr(sink):
        from tests.d10.support import templates
        from tests.d10.test_v2_engine import FictionalAuthority,execute
        from services import ga_v2_store as store
        from services.ga_checkpoint_service import canonical
        from schemas.ga_constrained import Parameters
        store.STORE=Path(sys.argv[1])
        payload,snapshot,state=store.read(sys.argv[2])
        assert payload["status"]=="PAUSED"
        execute(templates(compact=True),snapshot,Parameters.model_validate(state["parameters"]),FictionalAuthority(snapshot),sys.argv[2],state=state)
        final,_,_=store.read(sys.argv[2])
        answer={"status":final["status"],"result_sha256":hashlib.sha256(canonical(final["result"])).hexdigest(),
                "scope":"Fictional unit authority; fresh Python process, real operators and JSON V2 continuation, no institutional acceptance"}
    print(json.dumps(answer))


if __name__=="__main__":main()
