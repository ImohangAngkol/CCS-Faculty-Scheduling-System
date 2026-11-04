"""Import-only fictional loader files for an owned temporary source snapshot.

Empty academic tables deliberately supply NO institutional roster or offerings.
The existing tests install their own fictional model fixtures after imports.
Never accepts the repository's backend/data or an existing application store.
"""
import csv
import hashlib
import json
from pathlib import Path
import tempfile


def prepare(snapshot):
    snapshot=Path(snapshot).resolve();owned=snapshot.parent
    if (snapshot.name!="repository" or owned.parent!=Path(tempfile.gettempdir()).resolve()
            or not owned.name.startswith("u5c-r1-snapshot-") or not (owned/"OWNED-SNAPSHOT.json").is_file()):
        raise ValueError("Fictional bootstrap requires a verified owned temporary snapshot")
    data=snapshot/"backend/data"
    data.mkdir(exist_ok=True)
    headers={
        "first_sem_bsit_subjects.csv":["course no.","course title","units","num of lec hours/week","num of lab hours/week","year_level"],
        "BSIT_Consolidated_Subject_Schedules.csv":["Section","Course Number","Schedule"],
        "Faculty Preferences V2.csv":["Faculty","Day(s)","Subject","New Schedule","Room Assignment"],
        "Faculty Admin, Research and Extension.csv":["Faculty","Admin Load","Research Load","Extension Load","Teaching Load"],
        "faculty_qualifications.csv":["faculty_code","specializations"],
        "faculty_subject_eligibility.csv":["faculty_code","course_no","eligibility_status"],
        "subject_domains.csv":["course_no","primary_domain","secondary_domains"],
    }
    for name,columns in headers.items():
        with (data/name).open("x",encoding="utf-8",newline="") as stream:
            csv.writer(stream).writerow(columns)
    for name,value in {"faculty_identities.json":{"version":1,"faculty":[]},"faculty_preferences.json":{},
        "ga_settings.json":{},"preassigned_assignments.json":{"external_instructors":{},"assignments":[]}}.items():
        with (data/name).open("x",encoding="utf-8",newline="\n") as stream:
            stream.write(json.dumps(value,sort_keys=True)+"\n")
    return {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(data.iterdir())}


def release_bytes(snapshot, recipe):
    """Reproduce verified unchanged release bytes in a TEMP copy, not production.

    Git normalized the pre-existing mixed line endings of frozen legacy sources.
    The recipe contains only positions/hashes, never replacement code or hashes
    to feed the engine. Original strict engine checks still validate the result.
    """
    snapshot=Path(snapshot).resolve();owned=snapshot.parent
    if owned.parent!=Path(tempfile.gettempdir()).resolve() or not owned.name.startswith("u5c-r1-snapshot-") or not (owned/"OWNED-SNAPSHOT.json").is_file():
        raise ValueError("Release-byte fixture requires an owned temporary snapshot")
    for item in recipe["files"]:
        path=(snapshot/item["path"]).resolve()
        if not path.is_relative_to(snapshot/"backend") or path.suffix!=".py":
            raise ValueError("Unexpected release fixture target")
        canonical=path.read_bytes()
        if hashlib.sha256(canonical).hexdigest()!=item["canonical_sha256"]:
            raise ValueError("Canonical source differs from the recorded baseline")
        lines=canonical.splitlines(keepends=True);indices=item["crlf_line_indices"]
        if len(set(indices))!=len(indices) or any(type(i) is not int or i<0 or i>=len(lines) or not lines[i].endswith(b"\n") for i in indices):
            raise ValueError("Invalid exact release newline layout")
        raw=b"".join(line[:-1]+b"\r\n" if i in indices else line for i,line in enumerate(lines))
        if raw.replace(b"\r\n",b"\n")!=canonical or hashlib.sha256(raw).hexdigest()!=item["release_raw_sha256"]:
            raise ValueError("Release source-byte proof failed")
        path.write_bytes(raw)
