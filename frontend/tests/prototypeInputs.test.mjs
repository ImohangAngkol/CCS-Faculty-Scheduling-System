import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {weightCommand, freezeCommand, neutralPreference} from '../src/prototypeInputs/model.mjs';
const flags = {contract: 'fictional-input-preparation-v1', production_admission: 'BLOCKED', optimizer_executed: false};
const view = {...flags, policy: {revision: 1}, minimum_revision: 2, minimum_digest: 'a'.repeat(64),
  weights_revision: 1, weights_digest: 'b'.repeat(64), preferences_digest: 'c'.repeat(64)};
test('Chair command changes only supplied original coefficients with pinned revision', () => {
  assert.deepEqual(weightCommand(view, '{"subject_penalty":0}', 'nonce'), {request_id: 'nonce', expected_revision: 1, penalties: {subject_penalty: 0}});
});
for (const raw of ['{"absolute_max_teaching_load":99}', '{"total_workload_target":12}', '{"subject_penalty":-1}',
  '{"subject_penalty":true}', '{"subject_penalty":0.5}', '{"subject_penalty":100001}', '{}', '[]', 'null']) {
  test(`reject unsupported coefficient input ${raw}`, () => assert.throws(() => weightCommand(view, raw, 'nonce')));
}
test('frozen preparation pins minimum weights and preference versions', () => {
  assert.deepEqual(freezeCommand(view, 'nonce'), {request_id: 'nonce', minimum_revision: 2, minimum_digest: 'a'.repeat(64),
    weights_revision: 1, weights_digest: 'b'.repeat(64), preferences_digest: 'c'.repeat(64)});
});
test('unverified selection cannot prepare', () => assert.throws(() => freezeCommand({...view, minimum_digest: null}, 'nonce')));
test('neutral initial editor does not silently activate preferences', () => {
  const value = neutralPreference();
  assert.equal(value.use_subject_preference, false); assert.equal(value.use_day_preference, false);
  assert.equal(value.use_time_preference, false); assert.deepEqual(value.preferred_subjects, []);
});
test('actual API calls, safe rendering, serialized changes and no native controls', () => {
  const source = readFileSync(new URL('../src/prototypeInputs/console.mjs', import.meta.url), 'utf8');
  assert.ok(source.includes("'/api/prototype/inputs/weights/approve'"));
  assert.ok(source.includes('/api/prototype/inputs/preferences/'));
  assert.ok(source.includes("'/api/prototype/inputs/prepare'"));
  assert.ok(source.includes('if (busy) return'));
  assert.ok(source.includes("querySelectorAll('input, textarea')"));
  assert.ok(source.includes("el('faculty').value !== code"));
  assert.ok(source.includes("el('faculty').addEventListener('input'"));
  assert.ok(source.includes("searchParams.get('preparation')"));
  assert.equal(source.includes('innerHTML'), false); assert.equal(source.includes('/scheduling/runs'), false);
  assert.equal(source.includes('setInterval'), false);
});
