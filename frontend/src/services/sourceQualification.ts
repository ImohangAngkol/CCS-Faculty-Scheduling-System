import {API_BASE, apiFetch as fetch} from "./apiSession.ts";

type TableStatus = "MATCH" | "STALE_OR_DIFFERENT_CACHE" | "CHANGED_DURING_INSPECTION" | "UNVERIFIABLE" | "CACHE_NOT_LOADED";
export type SourceQualification = {
  contract: "ga-source-qualification-inspection-v1"; qualification: "BLOCKED";
  eligible_for_current: false; institutional_approval: "NOT_ESTABLISHED"; source_metadata: null;
  input_fingerprint: string | null; file_set_stable_during_inspection: boolean;
  cached_tables: {source: string; status: TableStatus; row_count?: number}[]; reasons: string[]; scope: string;
};
const sources = new Set(["offerings_source", "fixed_section_source", "qualification_source", "eligibility_source", "domain_source"]);
const statuses = new Set(["MATCH", "STALE_OR_DIFFERENT_CACHE", "CHANGED_DURING_INSPECTION", "UNVERIFIABLE", "CACHE_NOT_LOADED"]);
const reasons = new Set(["INSTITUTIONAL_SOURCE_NOT_CONFIGURED", "RUN_CONSUMPTION_BINDING_UNAVAILABLE", "FULL_TRANSFORMED_MODEL_MAPPING_UNVERIFIED", "SOURCE_SET_UNSTABLE_OR_UNREADABLE"]);
export function validateSourceQualification(value: SourceQualification): SourceQualification {
  if (value?.contract !== "ga-source-qualification-inspection-v1" || value.qualification !== "BLOCKED"
      || value.eligible_for_current !== false || value.institutional_approval !== "NOT_ESTABLISHED" || value.source_metadata !== null
      || !(value.input_fingerprint === null || typeof value.input_fingerprint === "string" && /^[0-9a-f]{64}$/.test(value.input_fingerprint))
      || typeof value.file_set_stable_during_inspection !== "boolean" || !Array.isArray(value.cached_tables) || value.cached_tables.length > sources.size
      || new Set(value.cached_tables.map(row => row.source)).size !== value.cached_tables.length
      || value.cached_tables.some(row => !sources.has(row.source) || !statuses.has(row.status) || row.row_count !== undefined && (!Number.isInteger(row.row_count) || row.row_count < 0))
      || !Array.isArray(value.reasons) || [...reasons].slice(0, 3).some(reason => !value.reasons.includes(reason))
      || value.reasons.some(reason => !reasons.has(reason)) || typeof value.scope !== "string" || !value.scope) {
    throw new Error("Source qualification response is invalid or unsupported. Qualification remains blocked.");
  }
  return value;
}
export async function getSourceQualification(signal?: AbortSignal): Promise<SourceQualification> {
  const response = await fetch(`${API_BASE}/api/ga/source-qualification`, {signal, credentials: "include", cache: "no-store"});
  if (!response.ok) throw new Error(`Source qualification unavailable (${response.status}). No source was approved.`);
  return validateSourceQualification(await response.json());
}
