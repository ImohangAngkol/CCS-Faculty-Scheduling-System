"""Read-only compatibility probes; not a D10 constrained GA implementation.

Existing modules read academic sources at import; suppress that output rather
than archiving institutional rows. All exercised model objects are fictional.
No generation, fitness evaluation, database, saved-result or checkpoint writes.
"""
import ast
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
    from genetic_algorithm.models.Faculty import Faculty
    from genetic_algorithm.models.Room import Room
    from genetic_algorithm.models.Section import Section
    from genetic_algorithm.models.Subject import Subject
    from genetic_algorithm.models.TimeBlock import TimeBlock
    from genetic_algorithm.models.PreassignedAssignment import PreassignedAssignment
    from genetic_algorithm.utils import Functions as schedule
    from genetic_algorithm.operators import mutation, Swap


def source(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def run():
    rng_before = random.getstate()
    checks = []

    faculty = Faculty(900001, 1, eligible_subjects={"SYN101"})
    room = Room("Fictional Room", "Lecture")
    section = Section("SYN-A")
    fblock, rblock, sblock = (resource.time_blocks_monday[3] for resource in (faculty, room, section))
    for block in (fblock, rblock, sblock):
        block.is_available = False
        block.fixed_schedule = True
        block.fixed_course = "SYN-EXTERNAL"
    schedule.reset_complete_schedule([faculty], [], [room])
    assert fblock.is_available and rblock.is_available and not sblock.is_available
    checks.append({"id": "D10-I01", "result": "PASS", "finding": "Reset reopens faculty and room reservations, including a fixed_schedule marker; section reservation survives."})

    subject = Subject("SYN101", "Fictional Seminar", 2, 2, 0, section)
    assert not schedule.section_schedule_is_available(subject, "M", "09:00-10:00", [])
    checks.append({"id": "D10-I02", "result": "PASS", "finding": "Existing section availability check rejects an overlapping fixed section interval."})

    # A detached post-swap-shaped candidate: no conflict among chromosome genes,
    # but the assigned faculty and room each have an external 09:00 commitment.
    subject.section = Section("SYN-B")
    subject.assigned_faculty = faculty
    subject.lecture_room = room
    fblock.is_available = rblock.is_available = False
    block = TimeBlock("09:00", "09:30")
    block.faculty = faculty
    block.room = room.name
    subject.lecture_time_blocks = [("M", block)]
    for module in (mutation, Swap):
        assert not module.chromosome_has_conflicts([subject])
        assert not module.chromosome_has_eligibility_violation([subject])
        assert not module.chromosome_has_load_violation([subject])
    checks.append({"id": "D10-I03", "result": "PASS", "finding": "Both operators' conflict/eligibility/load gates do not detect a separate faculty or room commitment. This partial fixture tests these gates only, not complete-duration validity or successful mutation."})

    declaration_fields = set(PreassignedAssignment.__dataclass_fields__)
    assert declaration_fields == {"instructor_id", "instructor_name", "room_name"}
    checks.append({"id": "D10-I04", "result": "PASS", "finding": "Preassignment declaration has instructor and room identity, with no fixed meeting time or day."})

    checkpoint_text = source("backend/services/ga_checkpoint_service.py")
    checkpoint_ast = ast.parse(checkpoint_text)
    fingerprint = next(n for n in checkpoint_ast.body if isinstance(n, ast.FunctionDef) and n.name == "engine_fingerprint")
    fingerprint_text = ast.get_source_segment(checkpoint_text, fingerprint)
    assert all(name in fingerprint_text for name in ["ga_service.py", "ga_publication_service.py", "ga_progress_service.py", "ga_checkpoint_service.py"])
    assert 'payload["engine_fingerprint"] != evaluation_fingerprint' in checkpoint_text
    original = (ROOT / "backend/services/ga_service.py").read_bytes()
    assert hashlib.sha256(original).digest() != hashlib.sha256(original + b"\n# in-memory hypothetical adapter hook\n").digest()
    checks.append({"id": "D10-I05", "result": "PASS", "finding": "Orchestration/publication/progress source bytes are engine-fingerprinted; loader rejects mismatched engine identity. Hypothetical byte change was computed only in memory."})

    engine = ast.parse(source("backend/services/ga_service.py"))
    loop = next(n for n in engine.body if isinstance(n, ast.FunctionDef) and n.name == "run_genetic_algorithm")
    calls = [(n.lineno, n.func.id) for n in ast.walk(loop) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    save_line = min(line for line, name in calls if name == "save_best_if_better")
    return_line = max(n.lineno for n in ast.walk(loop) if isinstance(n, ast.Return))
    assert save_line < return_line
    assert random.getstate() == rng_before
    checks.append({"id": "D10-I06", "result": "PASS", "finding": "Engine saves best before returning; a router-only check after return would be too late to guard that write. Probes consumed no RNG draws after imports."})
    return {"scope": "Read-only synthetic boundary characterization, not acceptance of confirmed GEC generation", "checks": checks,
            "passed": len(checks), "failed": 0, "GA_generations_executed": 0,
            "fitness_evaluations_executed": 0, "database_connections": 0}


if __name__ == "__main__":
    try:
        print(json.dumps(run(), indent=2))
    except Exception:
        # Do not serialize arbitrary imported exceptions or resource objects.
        print(json.dumps({"result": "FAIL", "message": "Boundary probe failed; inspect the synthetic probe without dumping academic resources."}))
        raise SystemExit(1)
