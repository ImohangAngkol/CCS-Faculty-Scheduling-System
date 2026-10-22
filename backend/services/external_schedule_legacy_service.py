"""Explicit four-column legacy CSV adapter. No paths, writes, identity allocation or GA calls."""
import re

from schemas.external_schedule import ExternalRow, LegacyMetadata, LegacySourceRow, LegacyProvenance, Discrepancy
from services import external_schedule_service as intake

HEADERS = ("Year Level", "Section", "Course Number", "Schedule")


def parse_schedule(value):
    """Exact AM/PM endpoints and compact M/T/W/TH/F/S/SAT; never infer a meridiem."""
    findings = []
    def issue(code, severity, message):
        findings.append(Discrepancy(code=code, severity=severity, field="Schedule", message=message))
    pattern = r"\s*(\d{1,2}):([0-5]\d)\s*(AM|PM)\s*-\s*(\d{1,2}):([0-5]\d)\s*(AM|PM)\s+([A-Z]+)\s*"
    match = re.fullmatch(pattern, value, re.IGNORECASE)
    if not match:
        ambiguous = bool(re.search(r"\d:\d\d", value)) and not re.search(r"(?:AM|PM).*?(?:AM|PM)", value, re.I)
        state = "ambiguous" if ambiguous else "invalid"
        issue("LEGACY_AMBIGUOUS_SCHEDULE" if ambiguous else "LEGACY_INVALID_SCHEDULE", "review" if ambiguous else "error",
              "Use explicit h:mmAM/PM - h:mmAM/PM followed by compact day codes. Missing meridiems and multiple meetings are never inferred or repaired.")
        return [], "", "", state, findings
    h, m, am, eh, em, eam, token = match.groups()
    if not 1 <= int(h) <= 12 or not 1 <= int(eh) <= 12:
        issue("LEGACY_INVALID_TIME", "error", "12-hour clock hours must be 1–12. No correction was applied.")
        return [], "", "", "invalid", findings
    start = (int(h) % 12 + (12 if am.upper() == "PM" else 0))*60 + int(m)
    end = (int(eh) % 12 + (12 if eam.upper() == "PM" else 0))*60 + int(em)
    text = token.upper(); days = []; state = "parsed"
    if text == "SAT":
        days = ["S"]
    else:
        while text:
            day = "TH" if text.startswith("TH") else text[0]
            if day not in intake.DAYS:
                state = "unsupported"
                issue("LEGACY_UNSUPPORTED_DAY", "review", "Unsupported compact day pattern. Sunday and arbitrary day aliases are not supported.")
                days = []; break
            days.append(day); text = text[len(day):]
        if len(days) != len(set(days)):
            state = "ambiguous"
            issue("LEGACY_AMBIGUOUS_DAYS", "review", "Repeated day tokens require source clarification. Days were not silently deduplicated.")
    if start >= end:
        state = "invalid"
        issue("LEGACY_INVALID_INTERVAL", "error", "End must be later than start on the same day. Verify AM/PM with the supplier; no repair was applied.")
    elif start % 30 or end % 30 or start < 450 or end > 1320:
        if state == "parsed": state = "unsupported"
        issue("LEGACY_UNSUPPORTED_GRID", "review", "Outside the existing 07:30–22:00 half-hour grid. No rounding or availability changes were made.")
    return days, f"{start//60:02}:{start%60:02}", f"{end//60:02}:{end%60:02}", state, findings


def parse_legacy(raw, filename, metadata=None):
    metadata = metadata or LegacyMetadata()
    originals = []
    def records(source):
        try: _, header = next(source)
        except StopIteration: intake.fail("EMPTY_IMPORT", "The legacy file has no header.")
        if len(header) != 4 or set(header) != set(HEADERS):
            intake.fail("INVALID_LEGACY_COLUMNS", "Legacy CSV requires exactly Year Level, Section, Course Number, Schedule, each once.")
        rows, lines = [], []
        for line, cells in source:
            if len(rows) >= intake.MAX_ROWS: intake.fail("ROW_LIMIT", "Preview is limited to 200 rows. No partial preview was accepted.")
            if len(cells) != 4: intake.fail("MALFORMED_ROW", "Every legacy source row must match its four-column header.")
            if any(len(v) > 1000 or intake._unsafe_text(v) for v in cells):
                intake.fail("UNSAFE_CELL", "Unsafe or oversized legacy cell. No rows were accepted.")
            values = dict(zip(header, cells))
            if len(values["Section"].strip()) > 120 or len(values["Course Number"].strip()) > 40:
                intake.fail("INVALID_ROW_STRUCTURE", "Legacy subject/section fields exceed preview limits.")
            days, start, end, state, issues = parse_schedule(values["Schedule"])
            issues.append(Discrepancy(code="LEGACY_INCOMPLETE_METADATA", severity="review", field="metadata",
                message="Four-column source has no title, supplier, term, room, instructor or confirmation history. Added metadata is administrator-supplied and unverified; not ready for confirmation."))
            rows.append(ExternalRow(**metadata.model_dump(), subject_code=values["Course Number"].strip(),
                                    sections=[values["Section"].strip()], days=days, start=start, end=end))
            lines.append(line)
            originals.append(LegacySourceRow(source_row=line, year_level=values["Year Level"], section=values["Section"],
                course_number=values["Course Number"], schedule=values["Schedule"], parse_state=state, discrepancies=issues))
        if not rows: intake.fail("EMPTY_IMPORT", "The legacy file contains no schedule rows.")
        return rows, lines
    rows, lines = intake._csv(raw, records)
    provenance = LegacyProvenance(metadata=metadata, rows=originals)
    return intake.validate(rows, "csv", filename, raw, lines, _legacy=provenance)
