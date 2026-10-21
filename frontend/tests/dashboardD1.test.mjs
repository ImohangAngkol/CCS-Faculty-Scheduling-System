import {test} from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import {apiClient} from '../src/services/apiSession.ts';
import {loadSubjectCatalog, loadOwnFaculty, metadataError, searchSubjects, meetingPatternLabel} from '../src/services/dashboardMetadata.ts';
import {subjects, faculty, binding} from './dashboardD1.fixtures.mjs';

async function withGet(implementation, action) {
  const before = apiClient.get;
  apiClient.get = implementation;
  try {await action();} finally {apiClient.get = before;}
}
const failure = status => {const error = new axios.AxiosError('request failed'); error.response = {status, data: {detail: 'not echoed'}}; return error;};

test('catalog reads the existing endpoint with cancellation and preserves all source records', async () => {
  const signal = new AbortController().signal;
  const before = structuredClone(subjects);
  await withGet(async (url, options) => {
    assert.ok(url.endsWith('/api/subjects/available')); assert.equal(options.signal, signal);
    return {data: {data: subjects}};
  }, async () => assert.deepEqual(await loadSubjectCatalog(signal), subjects));
  assert.deepEqual(subjects, before);
});
test('catalog distinguishes a genuine empty response from malformed or duplicate records', async () => {
  await withGet(async () => ({data: {data: []}}), async () => assert.deepEqual(await loadSubjectCatalog(), []));
  for (const data of [null, {}, [{...subjects[0], components: null}], [subjects[0], subjects[0]]])
    await withGet(async () => ({data: {data}}), async () => assert.rejects(loadSubjectCatalog(), /incomplete or inconsistent/));
});
test('code and title search is case-insensitive and does not filter out unassigned or ineligible subjects', () => {
  assert.deepEqual(searchSubjects(subjects, ' syn101 '), [subjects[0]]);
  assert.deepEqual(searchSubjects(subjects, 'SEMINAR'), [subjects[1]]);
  assert.deepEqual(searchSubjects(subjects, 'no match'), []);
  assert.deepEqual(searchSubjects(subjects, ''), subjects);
});
test('component labels preserve paired durations, days and continuous laboratory requirements', () => {
  assert.match(meetingPatternLabel(subjects[0].components[0].meeting_patterns[0]), /2 meetings per week · 90 minutes each · Continuous · Monday \/ Thursday; Tuesday \/ Friday/);
  assert.match(meetingPatternLabel(subjects[0].components[1].meeting_patterns[0]), /1 meeting per week · 180 minutes each · Continuous · Wednesday/);
  assert.equal(subjects[1].components[0].meeting_patterns.length, 0);
});
test('profile reads only the bound UUID, preserving legacy code zero and abort signal', async () => {
  const signal = new AbortController().signal;
  await withGet(async (url, options) => {
    assert.ok(url.endsWith('/api/faculty/' + binding.faculty_id)); assert.equal(options.signal, signal);
    return {data: {data: faculty}};
  }, async () => assert.deepEqual(await loadOwnFaculty(binding, signal), faculty));
});
test('profile rejects a different UUID, a renumbered identity, external or malformed metadata', async () => {
  for (const row of [{...faculty, faculty_id: 'other'}, {...faculty, faculty_code: 1}, {...faculty, instructor_type: 'preassigned_external'}, {...faculty, specializations: null}, null])
    await withGet(async () => ({data: {data: row}}), async () => assert.rejects(loadOwnFaculty(binding), /does not match/));
});
test('missing metadata does not select another faculty or fabricate a record', async () => {
  let calls = 0;
  await withGet(async () => {calls++; throw failure(404);}, async () => assert.equal(await loadOwnFaculty(binding), null));
  assert.equal(calls, 1);
});
test('unauthorized and unavailable responses fail instead of returning a successful empty catalog or profile', async () => {
  for (const status of [401, 403, 503]) {
    const error = failure(status);
    await withGet(async () => {throw error;}, async () => {
      await assert.rejects(loadSubjectCatalog(), value => value === error);
      await assert.rejects(loadOwnFaculty(binding), value => value === error);
    });
    assert.notEqual(metadataError(error, 'fallback'), 'fallback');
    assert.ok(!metadataError(error, 'fallback').includes('not echoed'));
  }
  assert.equal(metadataError(new axios.AxiosError('network'), 'Retry connection'), 'Retry connection');
});
