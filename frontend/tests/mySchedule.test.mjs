import {test} from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import {apiClient} from '../src/services/apiSession.ts';
import {getMySchedule} from '../src/services/scheduleService.ts';
import {binding, proposal, missing, empty} from './mySchedule.fixtures.mjs';

async function withGet(implementation, action) {
  const before = apiClient.get; apiClient.get = implementation;
  try {await action();} finally {apiClient.get = before;}
}
test('own timetable uses GET /me with cancellation and no faculty selector', async () => {
  const signal = new AbortController().signal;
  await withGet(async (url, options) => {
    assert.ok(url.endsWith('/api/schedules/me')); assert.ok(!url.includes('?'));
    assert.deepEqual(options, {signal}); return {data: proposal};
  }, async () => assert.deepEqual(await getMySchedule(binding, signal), proposal));
});
test('genuine missing and empty schedules remain distinct', async () => {
  for (const response of [missing, empty]) await withGet(async () => ({data: response}), async () => assert.deepEqual(await getMySchedule(binding), response));
});
test('mismatched UUID/code or contradictory source and assignment states are rejected', async () => {
  for (const data of [{...proposal, faculty_id: '40000000-0000-4000-8000-000000000001'}, {...proposal, faculty_code: 1},
    {...proposal, availability: 'empty'}, {...proposal, assignments: []}, {...missing, assignments: proposal.assignments},
    {...proposal, source: missing.source}])
    await withGet(async () => ({data}), async () => assert.rejects(getMySchedule(binding), /does not match/));
});
test('administrator result fields and unverified timetable formats fail the response boundary', async () => {
  for (const data of [{...proposal, best_fitness: 42}, {...proposal, source: {...proposal.source, label: 'Official schedule'}},
    {...proposal, assignments: [{...proposal.assignments[0], faculty: 'another'}]},
    {...proposal, source: {...proposal.source, saved_at: 'invalid'}},
    {...proposal, assignments: [{...proposal.assignments[0], type: 'Unknown'}]}, null])
    await withGet(async () => ({data}), async () => assert.rejects(getMySchedule(binding), /could not be verified/));
});
test('401, permission denial, stale source and unavailable responses are not successful empty schedules', async () => {
  for (const status of [401, 403, 409, 503]) {
    const error = new axios.AxiosError('synthetic status'); error.response = {status};
    await withGet(async () => {throw error;}, async () => assert.rejects(getMySchedule(binding), value => value === error));
  }
});
