const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export function submission(context, requestId) {
  const view = context?.workload;
  if (context?.contract !== 'prototype-minimum-qualified-execution-v1' ||
      context.production_admission !== 'BLOCKED' || context.search_time_minimum_enforcement !== false ||
      !view?.scope || !hash(view.bundle_fingerprint) || !hash(view.policy?.digest) ||
      !hash(context.configuration_fingerprint) || !Number.isInteger(view.policy.revision)) {
    throw new Error('Unverified scheduling context. Refresh before starting.');
  }
  return {request_id: requestId, academic_year: view.scope.academic_year, term: view.scope.term,
    catalog_revision: view.scope.catalog_revision, minimum_revision: view.policy.revision,
    minimum_digest: view.policy.digest, prepared_bundle_fingerprint: view.bundle_fingerprint,
    configuration_fingerprint: context.configuration_fingerprint};
}

export function present(run) {
  if (run?.contract !== 'prototype-minimum-qualified-execution-v1' || run.production_admission !== 'BLOCKED' ||
      run.institutional_saved_best_promotion !== false || run.active_restore !== false ||
      run.search_time_minimum_enforcement !== false) throw new Error('Run contract rejected.');
  const labels = {INPUT_INFEASIBLE: 'Input infeasible: insufficient eligible teaching units.',
    RESOURCE_BLOCKED: 'Not launched: available RAM failed the 3 GiB gate.',
    RUN_FAILED: 'Execution failed; no qualified candidate.', INTERRUPTED: 'Execution interrupted; no qualified candidate.',
    CANDIDATE_CONSTRAINT_VIOLATING: 'Candidate generated: mandatory minimum violated. Not fully feasible.',
    CANDIDATE_FULLY_FEASIBLE: 'Candidate satisfies original hard constraints and captured individual minima.'};
  if (run.result && (!Number.isFinite(run.result.original_GA_fitness) ||
      !Array.isArray(run.result.qualification?.faculty) || !Array.isArray(run.result.schedule))) {
    throw new Error('Incomplete candidate evidence.');
  }
  if (run.fully_feasible === true && (run.state !== 'CANDIDATE_FULLY_FEASIBLE' ||
      run.result?.qualification?.fully_feasible_under_captured_policy !== true)) {
    throw new Error('Unsupported feasibility claim.');
  }
  return {message: run.evidence_error ? 'Candidate verification unavailable. Retry status; do not restart.' :
      labels[run.state] ?? `Run state: ${run.execution_state ?? run.state}. Status refresh does not launch or resume.`,
    fitness: run.result?.original_GA_fitness ?? null,
    faculty: run.result?.qualification?.faculty ?? [],
    schedule: run.result?.schedule ?? null};
}
