import type {ReviewMeeting} from "../../api/externalSchedules.ts";

export type ReviewFilters = {section: string; supplier: string; subject: string; intent: string; references: string};
export const emptyReviewFilters: ReviewFilters = {section: "", supplier: "", subject: "", intent: "", references: ""};
export function resources(row: ReviewMeeting) {return [...row.sections, row.room, row.instructor];}
export function hasResourceOverlap(row: ReviewMeeting) {return row.discrepancies.some(d => d.code.includes("OVERLAP"));}
export function filterReviewRows(rows: ReviewMeeting[], filter: ReviewFilters): ReviewMeeting[] {
  return rows.filter(row => {
    const refs = resources(row), pending = refs.some(r => r.state !== "resolved" && r.state !== "missing_optional");
    return (!filter.section || row.sections.some(r => r.id === filter.section || (!r.id && "source:" + r.original === filter.section)))
      && (!filter.supplier || row.original.supplier === filter.supplier)
      && (!filter.subject || row.original.subject_code === filter.subject)
      && (!filter.intent || row.original.status === filter.intent)
      && (!filter.references || (filter.references === "resolved" ? !pending
        : filter.references === "pending" ? pending : refs.some(r => r.state === filter.references)));
  });
}
const weekdays: Record<string, number> = {M: 1, T: 2, W: 3, TH: 4, F: 5, S: 6};
export function reviewCalendarEvents(rows: ReviewMeeting[]) {
  return rows.filter(row => row.calendar_supported).flatMap(row => row.original.days.map(day => ({
    id: String(row.source_row) + ":" + day, daysOfWeek: [weekdays[day]],
    startTime: row.original.start, endTime: row.original.end,
    title: row.original.subject_code, backgroundColor: hasResourceOverlap(row) ? "#fff1f2" : "#f0fdfa",
    borderColor: hasResourceOverlap(row) ? "#be123c" : "#0f766e", textColor: "#134e4a",
    extendedProps: {meeting: row},
  })));
}
