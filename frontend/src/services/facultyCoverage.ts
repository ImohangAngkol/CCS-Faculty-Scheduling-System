import {facultyKey, formatFacultyName} from "../components/schedule/facultyDisplay.ts";
import {facultyOrder} from "../components/schedule/scheduleOrder.ts";

type Metadata = {faculty_code: number | string; instructor_type?: string};
type Assignment = {faculty: string; faculty_name?: string};
type Analysis = {Faculty_Code: number | string};
export type CoverageMember = {key: string; label: string; assignments: number; sources: string[]; external: boolean};

/** Available metadata/report membership, not proof of an authoritative semester cohort. */
export function facultyCoverage(metadata: readonly Metadata[], assignments: readonly Assignment[], analysis: readonly Analysis[] = []): CoverageMember[] {
  const members = new Map<string, CoverageMember>();
  function add(value: unknown, source: string, name?: string) {
    if ((typeof value !== "string" && typeof value !== "number") || (typeof value === "number" && !Number.isFinite(value))) return;
    const key = facultyKey(String(value));
    if (!key || key === "undefined" || key === "null") return;
    const member = members.get(key) ?? {key, label: formatFacultyName(key, name), assignments: 0, sources: [], external: key.startsWith("external:")};
    if (!member.sources.includes(source)) member.sources.push(source);
    if (source === "schedule") {member.assignments++; member.label = formatFacultyName(key, name);}
    members.set(key, member);
  }
  metadata.filter(row => row.instructor_type !== "preassigned_external").forEach(row => add(row.faculty_code, "metadata"));
  analysis.filter(row => !String(row.Faculty_Code).startsWith("external:")).forEach(row => add(row.Faculty_Code, "recorded analysis"));
  assignments.forEach(row => add(row.faculty, "schedule", row.faculty_name));
  return [...members.values()].sort((a, b) => facultyOrder(a.key, b.key));
}
