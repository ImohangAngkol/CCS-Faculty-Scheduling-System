export function generatedView(run) {
  if (run?.contract !== 'fictional-scheduling-continuation-v1' || run.production_admission !== 'BLOCKED' ||
      run.institutional_promotion !== false || run.native_verified !== false || run.browser_verified !== false) {
    throw new Error('Unverified prototype contract.');
  }
  if (!run.generated) return {state: run.state, fitness: null, feasible: false, schedule: null};
  const result = run.result;
  if (result?.generated !== true || result.execution_mode !== 'ACTUAL_ORIGINAL_GA_OFFLINE_IN_PROCESS' ||
      result.receipt?.verification_status !== 'VERIFIED' || !Number.isFinite(result.original_result?.best_fitness) ||
      !Array.isArray(result.original_result.schedule) || !result.qualification) throw new Error('Generated observation evidence missing.');
  return {state: run.state, fitness: result.original_result.best_fitness,
    feasible: result.qualification.fully_feasible_under_captured_policy === true, schedule: result.original_result.schedule};
}
export function decisionFor(run, action, explanation, nonce) {
  const view = generatedView(run);
  if (!['COMPLETED', 'STOPPED'].includes(run.state) || !view.schedule ||
      !['APPROVE', 'REJECT', 'REQUEST_REVISION'].includes(action) ||
      !/^[a-f0-9]{64}$/.test(run.latest_candidate_fingerprint) || (run.reviews?.length ?? 0) !== 0 ||
      typeof explanation !== 'string' || explanation.trim().length < 10 || explanation.length > 1000) {
    throw new Error('Select a terminal undecided generated candidate and provide a review explanation.');
  }
  if (action === 'APPROVE' && !view.feasible) throw new Error('Mandatory constraint violations block approval.');
  return {request_id: nonce, expected_review: 0, candidate_fingerprint: run.latest_candidate_fingerprint,
    decision: action, explanation};
}
