"""Fictional bootstrap around existing test child entrypoints, source unchanged."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from benchmarks.retention_runtime import runtime,data_guard


def main():
    runtime()
    from benchmarks import scaled_python as bench
    kind=sys.argv[1];arguments=sys.argv[2:]
    with bench.synthetic_scoring(([],[],[]),[],bench.runtime()[3]().to_dict()),data_guard():
        if kind=='checkpoint':
            from tests.d10 import resume_v2_child
            sys.argv=[resume_v2_child.__file__,*arguments]
            resume_v2_child.main();return 0
        if kind=='benchmark':
            sys.argv=[bench.__file__,*arguments]
            return bench.main()
        raise RuntimeError('UNREVIEWED_CHILD_ENTRY_REJECTED')


if __name__=='__main__':raise SystemExit(main())
