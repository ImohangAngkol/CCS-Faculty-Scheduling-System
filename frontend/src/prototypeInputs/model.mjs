export const penalties = new Set(['subject_penalty', 'time_penalty', 'day_penalty', 'preparation_penalty',
  'load_balance_penalty', 'daily_load_penalty', 'gap_penalty', 'lecture_lab_penalty',
  'underload_penalty', 'overload_penalty', 'heavy_overload_penalty']);
export function weightCommand(view, text, id) {
  if (view?.contract !== 'fictional-input-preparation-v1' || view.production_admission !== 'BLOCKED' ||
      !Number.isInteger(view.policy?.revision)) throw new Error('Reload the server weight policy first.');
  const values = JSON.parse(text);
  if (!values || Array.isArray(values) || !Object.keys(values).length ||
      !Object.entries(values).every(([k, v]) => penalties.has(k) && Number.isSafeInteger(v) && v >= 0 && v <= 100000)) {
    throw new Error('Use only listed original penalty coefficients and whole numbers from 0 to 100000.');
  }
  return {request_id: id, expected_revision: view.policy.revision, penalties: values};
}
export function freezeCommand(view, id) {
  if (view?.contract !== 'fictional-input-preparation-v1' || view.production_admission !== 'BLOCKED' ||
      view.optimizer_executed !== false || !Number.isInteger(view.minimum_revision) || !Number.isInteger(view.weights_revision) ||
      !['minimum_digest', 'weights_digest', 'preferences_digest'].every(k => /^[a-f0-9]{64}$/.test(view[k] ?? ''))) {
    throw new Error('Reload the server preparation selection first.');
  }
  return {request_id: id, minimum_revision: view.minimum_revision, minimum_digest: view.minimum_digest,
    weights_revision: view.weights_revision, weights_digest: view.weights_digest, preferences_digest: view.preferences_digest};
}
export const neutralPreference = () => ({faculty_priority: 1, preferred_subjects: [], preferred_days: [],
  subject_importance: 0, day_importance: 0, time_importance: 0, use_subject_preference: false,
  use_day_preference: false, use_time_preference: false, use_gap_preference: false, use_lecture_lab_preference: false});
