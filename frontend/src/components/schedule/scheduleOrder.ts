import {facultyKey} from "./facultyDisplay.ts";

const collator = new Intl.Collator("en", {numeric: true, sensitivity: "base"});
export function naturalOrder(a: string, b: string): number {
  return collator.compare(a, b) || (a < b ? -1 : a > b ? 1 : 0);
}
export function facultyOrder(a: string, b: string): number {
  const left = facultyKey(a), right = facultyKey(b);
  const ln = /^\d+$/.test(left), rn = /^\d+$/.test(right);
  if (ln !== rn) return ln ? -1 : 1;
  return naturalOrder(left, right);
}
type Row = {faculty: string; subject: string; section: string; type: string; day: string; start: string; end: string; room: string; title?: string};
const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
function component(value: string) {
  return /^(lecture|lec)$/i.test(value.trim()) ? 0 : /^(laboratory|lab)$/i.test(value.trim()) ? 1 : 2;
}
function day(value: string) {
  const found = days.findIndex(name => name === value.toLowerCase() || name.slice(0, 3) === value.toLowerCase());
  return found < 0 ? 7 : found;
}
function minutes(value: string) {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value);
  return match && +match[1] < 24 && +match[2] < 60 ? +match[1] * 60 + +match[2] : Infinity;
}
/** New array; original rows/identities/gene order and export order remain untouched. */
export function displaySchedule<T extends Row>(rows: readonly T[]): T[] {
  return [...rows].sort((a, b) => facultyOrder(a.faculty, b.faculty)
    || naturalOrder(a.subject, b.subject) || naturalOrder(a.section, b.section)
    || component(a.type) - component(b.type) || naturalOrder(a.type, b.type)
    || day(a.day) - day(b.day) || naturalOrder(a.day, b.day)
    || (minutes(a.start) === minutes(b.start) ? 0 : minutes(a.start) < minutes(b.start) ? -1 : 1)
    || naturalOrder(a.start, b.start) || naturalOrder(a.room, b.room)
    || naturalOrder(a.end, b.end) || naturalOrder(a.title ?? "", b.title ?? ""));
}
