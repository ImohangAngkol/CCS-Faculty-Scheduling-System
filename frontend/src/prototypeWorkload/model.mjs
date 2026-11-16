export function validateView(value) {
  if (value?.contract !== 'prototype-explicit-minimum-v1' || value.prototype_only !== true ||
      value.production_admission !== 'BLOCKED' || value.optimizer_executed !== false ||
      value.active_restore !== false || value.continuous_optimization !== 'DISABLED' ||
      value.institutional_saved_best_promotion !== false || value.seven_day !== 'NO_GO' ||
      value.input_capture_verification !== 'UNVERIFIED' || value.optimizer_consumption !== 'NOT_ESTABLISHED' ||
      !Number.isInteger(value.policy?.revision) || value.policy.revision < 0 ||
      !/^[a-f0-9]{64}$/.test(value.bundle_fingerprint) || !/^[a-f0-9]{64}$/.test(value.policy.digest) ||
      !Array.isArray(value.faculty) || typeof value.can_configure !== 'boolean' ||
      ![value.scope?.academic_year, value.scope?.term, value.scope?.catalog_revision].every(x => typeof x === 'string' && x.startsWith('FICTIONAL-')) ||
      !['MINIMUM_WORKLOAD_INFEASIBLE', 'NOT_PROVEN_INFEASIBLE'].includes(value.preflight)) {
    throw new Error('Prototype workload contract rejected.');
  }
  const codes = new Set();
  for (const row of value.faculty) {
    if (!Number.isInteger(row.faculty_code) || row.faculty_code < 0 || codes.has(row.faculty_code) ||
        !Number.isFinite(row.soft_target_teaching_units) || !Number.isInteger(row.maximum_teaching_units) ||
        row.maximum_teaching_units < 0 || !Number.isFinite(row.eligible_units) || row.eligible_units < 0 ||
        (row.minimum_teaching_units !== null && (!Number.isInteger(row.minimum_teaching_units) ||
          row.minimum_teaching_units < 0 || row.minimum_teaching_units > row.maximum_teaching_units))) {
      throw new Error('Invalid faculty workload metadata.');
    }
    codes.add(row.faculty_code);
  }
  return value;
}

export function changeFor(view, values) {
  validateView(view);
  if (!view.can_configure) throw new Error('Scoped configuration authority is required.');
  const minimums = [];
  for (const row of view.faculty) {
    const text = String(values.get(row.faculty_code) ?? '').trim();
    if (!text) continue; // Unspecified is never a default minimum24.
    if (!/^\d+$/.test(text) || !Number.isSafeInteger(Number(text)) || Number(text) > row.maximum_teaching_units) {
      throw new Error(`Faculty ${row.faculty_code}: enter a whole number from 0 to ${row.maximum_teaching_units}, or leave blank.`);
    }
    minimums.push({faculty_code: row.faculty_code, minimum_teaching_units: Number(text)});
  }
  return {expected_revision: view.policy.revision, minimums};
}
