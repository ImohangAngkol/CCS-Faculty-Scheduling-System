// Presentation adapters only. Schedule identifiers are preserved in stored data.
export function facultyKey(faculty: string): string {
  const value = String(faculty ?? "").trim().replace(/^Faculty\s+(?=\d)/i, "");
  if (/^\d+(?:\.0+)?$/.test(value) && Number.isSafeInteger(Number(value))) return String(Number(value));
  return value;
}

export function formatFacultyName(faculty: string, displayName?: string): string {
  const key = facultyKey(faculty);
  if (/^\d+$/.test(key)) return `Faculty ${key}`;
  if (key.startsWith("external:")) {
    // Legacy schedule selectors carry only the existing CCS instructor key.
    const name = displayName?.trim() || (key === "external:eddie-bouy-palad" ? "Atty. Eddie Bouy Palad" : "");
    return name ? `${name} · Preassigned Instructor` : "Preassigned Instructor";
  }
  return key || "Unassigned Faculty";
}
