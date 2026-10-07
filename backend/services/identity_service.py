"""Stable public identities and the frozen numeric-code compatibility map.

This module has no scheduling imports and never allocates identities at runtime.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid5


IDENTITY_FILE = Path(__file__).resolve().parents[1] / "data" / "faculty_identities.json"
IDENTITY_NAMESPACE = UUID("b8935fe0-208f-44c9-9b5c-62f4054cb02c")
CATALOG_SCOPE = "msu-iit:ccs"
# The source files do not contain a reliable term identifier. Do not invent one.
OFFERING_SCOPE = "ccs:first-semester-prototype"


def normalize_code(value):
    return str(value).strip().upper()


@dataclass(frozen=True)
class FacultyIdentity:
    faculty_id: str
    faculty_code: int
    display_code: str
    name: str
    aliases: tuple[str, ...] = ()


def parse_faculty_identities(payload):
    if payload.get("version") != 1:
        raise ValueError("Unsupported faculty identity registry version.")
    identities = []
    ids, codes, names, display_codes = set(), set(), set(), set()
    for row in payload["faculty"]:
        identity = FacultyIdentity(
            faculty_id=str(UUID(row["faculty_id"])),
            faculty_code=int(row["faculty_code"]),
            display_code=row["display_code"].strip(),
            name=row["name"].strip(),
            aliases=tuple(normalize_code(alias) for alias in row.get("aliases", [])),
        )
        source_names = {normalize_code(identity.name), *identity.aliases}
        if (identity.faculty_id in ids or identity.faculty_code in codes
                or identity.display_code in display_codes or source_names & names):
            raise ValueError("Duplicate faculty identity, code, display label, or name alias.")
        if identity.faculty_code < 0 or not identity.display_code or "" in source_names:
            raise ValueError("Faculty identities require a nonnegative code and nonempty labels.")
        ids.add(identity.faculty_id)
        codes.add(identity.faculty_code)
        display_codes.add(identity.display_code)
        names.update(source_names)
        identities.append(identity)
    return tuple(identities)


@lru_cache(maxsize=1)
def load_faculty_identities():
    with IDENTITY_FILE.open(encoding="utf-8") as file:
        return parse_faculty_identities(json.load(file))


def resolve_faculty_identity(reference):
    reference = str(reference).strip()
    for identity in load_faculty_identities():
        if reference == identity.faculty_id or (
            reference.isdecimal() and int(reference) == identity.faculty_code
        ):
            return identity
    raise ValueError(f"Unknown faculty identity: {reference}")


def build_legacy_faculty_codes(source_names, identities=None):
    """Resolve source names against registered codes, never enumeration/order."""
    registry = load_faculty_identities() if identities is None else identities
    by_name = {
        name: identity.faculty_code
        for identity in registry
        for name in {normalize_code(identity.name), *identity.aliases}
    }
    result = {}
    for value in source_names:
        name = normalize_code(value)
        if name not in by_name:
            raise ValueError(
                f"Faculty '{name}' has no stable identity. Register an unused legacy "
                "code and stable ID in faculty_identities.json before loading this faculty."
            )
        result[name] = by_name[name]
    return result


def course_identity(course_code):
    return str(uuid5(IDENTITY_NAMESPACE, f"course:{CATALOG_SCOPE}:{normalize_code(course_code)}"))


def section_identity(section_code):
    return str(uuid5(IDENTITY_NAMESPACE, f"section:{OFFERING_SCOPE}:{normalize_code(section_code)}"))


def offering_identity(course_code, section_code):
    return str(uuid5(
        IDENTITY_NAMESPACE,
        f"offering:{OFFERING_SCOPE}:{normalize_code(course_code)}::{normalize_code(section_code)}",
    ))


def external_instructor_identity(internal_code):
    return str(uuid5(IDENTITY_NAMESPACE, f"instructor:{CATALOG_SCOPE}:{internal_code}"))
