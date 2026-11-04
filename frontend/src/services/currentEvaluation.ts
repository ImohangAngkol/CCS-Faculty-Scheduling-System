import {API_BASE, apiFetch as fetch} from "./apiSession.ts";

export type Compatibility = "CURRENT_COMPATIBLE" | "LEGACY_INCOMPATIBLE" | "UNKNOWN_COMPATIBILITY";
export type EvaluationRun = {run_id: string; state: string; classification: Compatibility; reason: string;
  generation: number | null; configuration_fingerprint: string | null; fitness: number | null; chromosome_id: string | null};
export type CurrentEvaluation = {schema_version: 1; contract: "ga-result-compatibility-v1";
  current_identity: {engine_family: "V1"; engine_version: string; engine_fingerprint: string;
    fitness_policy: "preference-policy-2"; preference_scoring_version: 2; scorer_sha256: string;
    constraint_policy: string; input_fingerprint: string; result_schema_version: 1;
    academic_context: {kind: string; academic_year: string | null; term: string | null}};
  coverage_complete: boolean; current_runs: number | null; best: EvaluationRun | null; runs: EvaluationRun[]; issues: string[];
  saved_chromosome: {classification: "UNKNOWN_COMPATIBILITY"; baseline_eligible: false; reason: string};
  comparison_basis: string; institutional_authorization: "NOT_ESTABLISHED"};
const hash = (value: unknown) => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const uuid = (value: unknown) => typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
export function validateCurrentEvaluation(value: CurrentEvaluation): CurrentEvaluation {
  const fail = () => {throw new Error("Current evaluation provenance is invalid or unsupported. Historical records remain separate.");};
  const identity = value?.current_identity;
  if (value?.schema_version !== 1 || value.contract !== "ga-result-compatibility-v1"
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
  const ids = new Set();
  for (const run of value.runs) {
    if (!uuid(run.run_id) || ids.has(run.run_id) || !run.state || !run.reason
        || !["CURRENT_COMPATIBLE","LEGACY_INCOMPATIBLE","UNKNOWN_COMPATIBILITY"].includes(run.classification)) fail();
    ids.add(run.run_id);
    if (run.classification === "CURRENT_COMPATIBLE") {
      if (identity.academic_context.kind !== "verified-recorded-context" || !identity.academic_context.academic_year || !identity.academic_context.term) fail();
      if (!Number.isInteger(run.generation) || run.generation! < 0 || !hash(run.configuration_fingerprint)
          || !hash(run.chromosome_id) || typeof run.fitness !== "number" || !Number.isFinite(run.fitness)) fail();
    } else if (run.fitness !== null || run.chromosome_id !== null) fail();
  }
  const current = value.runs.filter(run => run.classification === "CURRENT_COMPATIBLE");
  if (value.coverage_complete ? value.current_runs !== current.length : value.current_runs !== null || value.best !== null) fail();
  const candidates = current.filter(run => run.state === "COMPLETED").sort((a,b) => a.fitness!-b.fitness! || a.run_id.localeCompare(b.run_id));
  const comparable = new Set(candidates.map(run => run.configuration_fingerprint)).size <= 1;
  const expected = value.coverage_complete && comparable ? candidates[0] ?? null : null;
  if (expected ? !value.best || Object.keys(expected).some(key => value.best![key as keyof EvaluationRun] !== expected[key as keyof EvaluationRun]) : value.best !== null) fail();
  return value;
}
export async function getCurrentEvaluation(signal?: AbortSignal): Promise<CurrentEvaluation> {
  const response = await fetch(`${API_BASE}/api/ga/current-evaluation`, {signal, credentials: "include", cache: "no-store"});
  if (!response.ok) throw new Error(`Current evaluation unavailable (${response.status}). Retry or inspect Historical Archive.`);
  return validateCurrentEvaluation(await response.json());
}
