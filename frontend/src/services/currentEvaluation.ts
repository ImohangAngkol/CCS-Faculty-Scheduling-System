import {API_BASE, apiFetch as fetch} from "./apiSession.ts";

export type Compatibility = "CURRENT" | "CURRENT_COMPATIBLE" | "LEGACY_INCOMPATIBLE" | "UNKNOWN_COMPATIBILITY";
export type AcademicContext = {kind: string; version?: 1; academic_year: string | null; term: string | null;
  academic_year_id?: string; term_id?: string; scope_id?: string; department?: string;
  dataset_id?: string; dataset_revision?: string; input_fingerprint?: string; context_sha256?: string};
export type EvaluationRun = {run_id: string; state: string; classification: Compatibility; reason: string;
  generation: number | null; configuration_fingerprint: string | null; fitness: number | null; chromosome_id: string | null;
  academic_context?: AcademicContext; provenance?: {contract: string; run_start_sha256: string; context_sha256: string; started_at: string}};
export type CurrentEvaluation = {schema_version: 1 | 2; contract: "ga-result-compatibility-v1" | "ga-result-compatibility-v2";
  current_identity: {engine_family: "V1"; engine_version: string; engine_fingerprint: string;
    fitness_policy: "preference-policy-2"; preference_scoring_version: 2; scorer_sha256: string;
    constraint_policy: string; input_fingerprint: string; result_schema_version: 1;
    academic_context: AcademicContext; context_verification?: "VERIFIED" | "UNAVAILABLE"};
  coverage_complete: boolean; current_runs: number | null; best: EvaluationRun | null; runs: EvaluationRun[]; issues: string[];
  saved_chromosome: {classification: "UNKNOWN_COMPATIBILITY"; baseline_eligible: false; reason: string};
  comparison_basis: string; institutional_authorization: "NOT_ESTABLISHED"};
const hash = (value: unknown) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const uuid = (value: unknown) => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
const canonical = (value: unknown): unknown => Array.isArray(value) ? value.map(canonical) : value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([a],[b]) => a.localeCompare(b)).map(([key,item]) => [key,canonical(item)])) : value;
export function validateCurrentEvaluation(value: CurrentEvaluation): CurrentEvaluation {
  const fail = () => {throw new Error("Current evaluation provenance is invalid or unsupported. Historical records remain separate.");};
  const identity = value?.current_identity;
  const v2 = value?.schema_version === 2 && value.contract === "ga-result-compatibility-v2";
  const currentLabel = v2 ? "CURRENT" : "CURRENT_COMPATIBLE";
  if ((!v2 && (value?.schema_version !== 1 || value.contract !== "ga-result-compatibility-v1"))
      || identity?.engine_family !== "V1" || !identity.engine_version || !hash(identity.engine_fingerprint)
      || identity.preference_scoring_version !== 2 || identity.fitness_policy !== "preference-policy-2"
      || !hash(identity.scorer_sha256) || !hash(identity.input_fingerprint) || !identity.constraint_policy
      || identity.result_schema_version !== 1 || !identity.academic_context
      || ![null,"string"].includes(identity.academic_context.academic_year === null ? null : typeof identity.academic_context.academic_year)
      || ![null,"string"].includes(identity.academic_context.term === null ? null : typeof identity.academic_context.term)
      || typeof value.coverage_complete !== "boolean" || !Array.isArray(value.runs) || value.runs.length > 200
      || !Array.isArray(value.issues) || value.issues.some(issue => typeof issue !== "string")
      || value.institutional_authorization !== "NOT_ESTABLISHED" || !value.comparison_basis
      || value.saved_chromosome?.classification !== "UNKNOWN_COMPATIBILITY" || value.saved_chromosome?.baseline_eligible !== false) fail();
  if (v2 && !["VERIFIED","UNAVAILABLE"].includes(identity.context_verification ?? "")) fail();
  if (v2 && identity.context_verification === "VERIFIED") {
    const context = identity.academic_context;
    if (context.version !== 1 || context.kind !== "verified-recorded-context" || !context.academic_year || !context.term
        || !hash(context.context_sha256) || !uuid(context.academic_year_id) || !uuid(context.term_id) || !uuid(context.scope_id)
        || !context.department || !context.dataset_id || !context.dataset_revision || context.input_fingerprint !== identity.input_fingerprint) fail();
  }
  const ids = new Set();
  for (const run of value.runs) {
    if (!uuid(run.run_id) || ids.has(run.run_id) || !run.state || !run.reason
        || ![currentLabel,"LEGACY_INCOMPATIBLE","UNKNOWN_COMPATIBILITY"].includes(run.classification)) fail();
    ids.add(run.run_id);
    if (run.classification === currentLabel) {
      if (identity.academic_context.kind !== "verified-recorded-context" || !identity.academic_context.academic_year || !identity.academic_context.term) fail();
      if (!Number.isInteger(run.generation) || run.generation! < 0 || !hash(run.configuration_fingerprint)
          || !hash(run.chromosome_id) || typeof run.fitness !== "number" || !Number.isFinite(run.fitness)) fail();
      if (v2) {
        const context = identity.academic_context, captured = run.academic_context, proof = run.provenance;
        if (identity.context_verification !== "VERIFIED" || !hash(context.context_sha256)
            || !uuid(context.academic_year_id) || !uuid(context.term_id) || !uuid(context.scope_id)
            || !context.department || !context.dataset_id || !context.dataset_revision
            || context.input_fingerprint !== identity.input_fingerprint
            || !captured || ["kind","version","academic_year","term","academic_year_id","term_id","scope_id","department","dataset_id","dataset_revision","input_fingerprint","context_sha256"].some(key => captured[key as keyof AcademicContext] !== context[key as keyof AcademicContext])
            || proof?.contract !== "ga-run-start-provenance-v1" || !hash(proof.run_start_sha256)
            || proof.context_sha256 !== context.context_sha256 || !Number.isFinite(Date.parse(proof.started_at))) fail();
      }
    } else if (run.fitness !== null || run.chromosome_id !== null) fail();
  }
  const current = value.runs.filter(run => run.classification === currentLabel);
  if (value.coverage_complete ? value.current_runs !== current.length : value.current_runs !== null || value.best !== null) fail();
  const candidates = current.filter(run => run.state === "COMPLETED").sort((a,b) => a.fitness!-b.fitness! || a.run_id.localeCompare(b.run_id));
  const comparable = new Set(candidates.map(run => run.configuration_fingerprint)).size <= 1;
  const expected = value.coverage_complete && comparable ? candidates[0] ?? null : null;
  if (JSON.stringify(canonical(value.best)) !== JSON.stringify(canonical(expected))) fail();
  return value;
}
export async function getCurrentEvaluation(signal?: AbortSignal): Promise<CurrentEvaluation> {
  const response = await fetch(`${API_BASE}/api/ga/current-evaluation`, {signal, credentials: "include", cache: "no-store"});
  if (!response.ok) throw new Error(`Current evaluation unavailable (${response.status}). Retry or inspect Historical Archive.`);
  return validateCurrentEvaluation(await response.json());
}
