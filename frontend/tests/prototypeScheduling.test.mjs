import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {present, submission} from '../src/prototypeScheduling/model.mjs';
const flags = {contract: 'prototype-minimum-qualified-execution-v1', production_admission: 'BLOCKED',
  institutional_saved_best_promotion: false, active_restore: false, search_time_minimum_enforcement: false};
const context = {...flags, configuration_fingerprint: 'a'.repeat(64), workload: {scope: {academic_year: 'FICTIONAL-YEAR',
  term: 'FICTIONAL-TERM', catalog_revision: 'FICTIONAL-CATALOG'}, bundle_fingerprint: 'b'.repeat(64), policy: {revision: 1, digest: 'c'.repeat(64)}}};
test('submission pins exact server scope revision inputs and configuration', () => {
  const value = submission(context, 'nonce');
  assert.equal(value.term, 'FICTIONAL-TERM'); assert.equal(value.minimum_revision, 1);
  assert.equal(value.configuration_fingerprint, 'a'.repeat(64)); assert.equal(value.minimum_digest, 'c'.repeat(64));
  assert.equal(Object.hasOwn(value, 'fitness'), false);
});
test('missing context cannot start', () => assert.throws(() => submission({}, 'nonce')));
for (const state of ['INPUT_INFEASIBLE', 'RESOURCE_BLOCKED', 'RUN_FAILED', 'INTERRUPTED', 'EXECUTION_UNCERTAIN']) {
  test(`honest state ${state}`, () => {
    const view = present({...flags, state, result: null, fully_feasible: false});
    assert.equal(view.fitness, null); assert.equal(view.schedule, null); assert.ok(view.message);
  });
}
for (const feasible of [false, true]) {
  test(`actual zero fitness and feasibility=${feasible}`, () => {
    const run = {...flags, state: feasible ? 'CANDIDATE_FULLY_FEASIBLE' : 'CANDIDATE_CONSTRAINT_VIOLATING', fully_feasible: feasible,
      result: {original_GA_fitness: 0, schedule: [], qualification: {faculty: [{faculty_code: 2, assigned_units: feasible ? 24 : 0}], fully_feasible_under_captured_policy: feasible}}};
    assert.equal(present(run).fitness, 0); assert.equal(present(run).faculty[0].assigned_units, feasible ? 24 : 0);
  });
}
test('reject an unsupported feasibility claim', () => assert.throws(() => present({...flags, state: 'INPUT_INFEASIBLE', fully_feasible: true})));
test('reject missing candidate metrics and preserve unavailable status', () => {
  assert.throws(() => present({...flags, result: {original_GA_fitness: null}}));
  assert.match(present({...flags, evidence_error: 'UNAVAILABLE'}).message, /verification unavailable/);
});
test('safe rendering and lost-ack reload recovery never repeat Start', () => {
  const source = readFileSync(new URL('../src/prototypeScheduling/console.mjs', import.meta.url), 'utf8');
  assert.equal(source.includes('innerHTML'), false);
  assert.ok(source.includes("searchParams.get('request')"));
  assert.ok(source.includes("url.searchParams.set('request', pending)"));
  assert.ok(source.includes('/api/prototype/scheduling/requests/'));
  assert.ok(source.includes('if (busy) return'));
  assert.equal(source.includes('setInterval'), false);
});
