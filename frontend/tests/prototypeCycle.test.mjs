import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {generatedView, decisionFor} from '../src/prototypeCycle/model.mjs';
const flags = {contract: 'fictional-scheduling-continuation-v1', production_admission: 'BLOCKED', institutional_promotion: false,
  native_verified: false, browser_verified: false};
function candidate(feasible = true) { return {...flags, run_id: 'fictional', state: 'COMPLETED', generated: true,
  latest_candidate_fingerprint: 'a'.repeat(64), reviews: [], result: {generated: true, execution_mode: 'ACTUAL_ORIGINAL_GA_OFFLINE_IN_PROCESS',
    receipt: {verification_status: 'VERIFIED'}, original_result: {best_fitness: 0, schedule: [{}]}, qualification: {fully_feasible_under_captured_policy: feasible}}}; }
test('admission is never presented as generated output', () => assert.deepEqual(generatedView({...flags, state: 'ADMITTED_NATIVE_BLOCKED', generated: false}),
  {state: 'ADMITTED_NATIVE_BLOCKED', fitness: null, feasible: false, schedule: null}));
test('real zero fitness remains zero and separate from feasibility', () => { assert.equal(generatedView(candidate(false)).fitness, 0); assert.equal(generatedView(candidate(false)).feasible, false); });
test('constraint violating candidate cannot be approved', () => assert.throws(() => decisionFor(candidate(false), 'APPROVE', 'Sufficient explanation.', 'nonce')));
for (const action of ['APPROVE', 'REJECT', 'REQUEST_REVISION']) test(`bound Chair decision ${action}`, () => {
  const command = decisionFor(candidate(), action, 'Explicit fictional candidate review.', 'nonce');
  assert.equal(command.expected_review, 0); assert.equal(command.candidate_fingerprint, 'a'.repeat(64)); assert.equal(command.decision, action);
});
test('unverified or historical decided candidate cannot bypass review binding', () => {
  assert.throws(() => generatedView({...candidate(), result: null}));
  assert.throws(() => decisionFor({...candidate(), reviews: [{}]}, 'APPROVE', 'Sufficient explanation.', 'nonce'));
  assert.throws(() => decisionFor({...candidate(), state: 'BETWEEN_SEGMENTS'}, 'APPROVE', 'Sufficient explanation.', 'nonce'));
});
test('page has real API calls and no GA execution or restore endpoint', () => {
  const source = readFileSync(new URL('../src/prototypeCycle/console.mjs', import.meta.url), 'utf8');
  assert.equal(source.includes('innerHTML'), false); assert.equal(source.includes('step_offline'), false);
  assert.equal(source.includes('/execute'), false); assert.equal(source.includes('/recover'), false);
  assert.ok(source.includes('/api/prototype/cycle/admissions')); assert.ok(source.includes('/decision'));
  assert.ok(source.includes('/timetable/')); assert.ok(source.includes('/export/'));
  assert.ok(source.includes('selected = null')); assert.ok(source.includes('URL.revokeObjectURL'));
  assert.ok(source.includes('catch (error) { selected = null;'));
});
