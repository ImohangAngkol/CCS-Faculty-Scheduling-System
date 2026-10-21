"""Opt-in identity comparison only; never imports metadata_service or the GA."""
from uuid import UUID, uuid5

from schemas.academic import IdentityProjection, ProjectionComparison
from services.identity_service import IDENTITY_NAMESPACE, normalize_code


def scoped_course_id(scope_key: str, course_code: str) -> UUID:
    return uuid5(IDENTITY_NAMESPACE, f"course:{scope_key}:{normalize_code(course_code)}")


def scoped_section_id(identity_scope: str, section_code: str) -> UUID:
    return uuid5(IDENTITY_NAMESPACE, f"section:{identity_scope}:{normalize_code(section_code)}")


def scoped_offering_id(identity_scope: str, course_code: str, section_code: str) -> UUID:
    return uuid5(IDENTITY_NAMESPACE, f"offering:{identity_scope}:{normalize_code(course_code)}::{normalize_code(section_code)}")


def compare_projections(expected: IdentityProjection, actual: IdentityProjection) -> ProjectionComparison:
    if (expected.scope_id, expected.term_id) != (actual.scope_id, actual.term_id):
        raise ValueError("Explicit scope/term mismatch; no fallback.")
    def index(projection):
        result = {}
        for row in projection.records:
            key = f"{row.kind}:{row.id}"
            if key in result:
                raise ValueError("Duplicate identity in projection.")
            result[key] = row
        return result
    left, right = index(expected), index(actual)
    missing = tuple(sorted(left.keys() - right.keys()))
    unexpected = tuple(sorted(right.keys() - left.keys()))
    changed = tuple(sorted(key for key in left.keys() & right.keys() if left[key] != right[key]))
    return ProjectionComparison(equal=not (missing or unexpected or changed), missing=missing,
                                unexpected=unexpected, changed=changed)
