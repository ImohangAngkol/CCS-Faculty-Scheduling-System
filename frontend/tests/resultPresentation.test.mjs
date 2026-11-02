import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {evaluationRecords, isVerifiedCurrent, penaltyLabel, progressSeries} from '../src/services/resultPresentation.ts';
import {displaySchedule, facultyOrder} from '../src/components/schedule/scheduleOrder.ts';

const row = (fields = {}) => ({faculty: '1', subject: 'FIC100', section: 'FIC1', type: 'Lecture', day: 'Monday', start: '08:00', end: '09:00', room: 'Fictional1', title: 'Fictional subject', ...fields});
const point = (generation, best, ever = best, average = best) => ({generation, generation_best_fitness: best, best_ever_fitness: ever, average_fitness: average, run_id: 'fictional-run', input_fingerprint: 'fictional-input', configuration_fingerprint: 'fictional-config'});
test('timestamps, fitness, self-declared compatibility and arbitrary versions never prove currency', () => {
  for (const record of [null, {}, {exists: true, fitness: 810, created_at: '2099-01-01'}, {compatible: true, engine_version: 'current', fitness_policy: 'latest'}]) assert.equal(isVerifiedCurrent(record), false);
});
test('current list is empty; archive preserves records, order, values and original lifecycle labels', () => {
  const records = ['COMPLETED', 'INTERRUPTED', 'FAILED', 'PAUSED'].map((state, index) => Object.freeze({state, run_id: `fictional-${index}`, created_at: '2026-01-01', fitness: index}));
  assert.deepEqual(evaluationRecords(records, 'current'), []);
  const archive = evaluationRecords(records, 'archive'); assert.deepEqual(archive, records); assert.notEqual(archive, records);
  assert.ok(archive.every((record, index) => record === records[index]));
});
test('missing/invalid penalty is a dash; a measured zero remains zero', () => {
  for (const value of [null, undefined, NaN, Infinity, '', '0']) assert.equal(penaltyLabel(value), '—');
  assert.equal(penaltyLabel(0), '0'); assert.equal(penaltyLabel(810), '810');
});
test('faculty numbers sort numerically including Faculty prefix and legacy decimal codes', () => {
  assert.deepEqual(['10', 'Faculty 2', '1.0', 'Fictional Lecturer'].sort(facultyOrder), ['1.0', 'Faculty 2', '10', 'Fictional Lecturer']);
});
test('subject and section codes use natural ordering', () => {
  const rows = [row({subject: 'FIC10'}), row({subject: 'FIC2', section: 'FIC10'}), row({subject: 'FIC2', section: 'FIC2'})];
  assert.deepEqual(displaySchedule(rows).map(r => [r.subject, r.section]), [['FIC2','FIC2'], ['FIC2','FIC10'], ['FIC10','FIC1']]);
});
test('hierarchy is faculty, subject, section, component then day/time/room', () => {
  const rows = [row({faculty: '2', subject: 'AAA1'}), row({type: 'Laboratory'}), row({day: 'Tuesday'}), row(), row({type: 'Other'}), row({start: '9:00', end: '10:00'}), row({room: 'Fictional2'})];
  assert.deepEqual(displaySchedule(rows), [rows[3], rows[6], rows[5], rows[2], rows[1], rows[4], rows[0]]);
});
test('all rows and original row identities survive sorting without input mutation or merged lecture/lab', () => {
  const rows = Object.freeze([Object.freeze(row({faculty: '10'})), Object.freeze(row({type: 'Laboratory'})), Object.freeze(row())]);
  const before = JSON.stringify(rows), sorted = displaySchedule(rows);
  assert.equal(JSON.stringify(rows), before); assert.equal(sorted.length, 3); assert.equal(new Set(sorted).size, 3); assert.notEqual(sorted, rows);
  assert.ok(sorted.every(item => rows.includes(item)));
});
test('nonnumeric faculty, unknown days, invalid clocks and equal keys have deterministic ordering', () => {
  const rows = [row({faculty:'Fictional Z'}), row({faculty:'Fictional A', start:'invalid'}), row({faculty:'Fictional A', start:'08:00'}), row({faculty:'Fictional A', day:'Unknown'})];
  assert.deepEqual(displaySchedule(rows), [rows[2], rows[1], rows[3], rows[0]]);
  assert.deepEqual(displaySchedule([...rows].reverse()), displaySchedule(rows));
});
test('each series uses its own starting penalty and raw penalties remain byte-equivalent', () => {
  const history = [point(0, 100, 90, 200), point(1, 80, 70, 150)]; const before = JSON.stringify(history);
  const lines = progressSeries(history); assert.deepEqual(lines.map(line => line.points[1].reduction), [20,20,50]);
  assert.deepEqual(lines.map(line => line.points[1].percent), [20,20/90*100,25]);
  assert.equal(JSON.stringify(history), before); assert.deepEqual(lines.map(line => line.points[1].penalty), [80,70,150]);
});
test('zero baseline gives true absolute deterioration without dividing by zero', () => {
  const points = progressSeries([point(0,0),point(1,5)])[0].points;
  assert.equal(points[1].reduction, -5); assert.equal(points[1].percent,null); assert.equal(points[0].reduction,0);
});
test('deterioration is never clamped or forced monotone', () => {
  const points = progressSeries([point(0,100),point(1,80),point(2,110)])[0].points;
  assert.deepEqual(points.map(p => p.reduction), [0,20,-10]); assert.equal(points[2].percent,-10);
});
test('first valid finite observation per series skips invalid samples without coercion', () => {
  const points = progressSeries([point(0,NaN),point(1,null),point(2,10),point(3,5)])[0].points;
  assert.deepEqual(points.map(p => p.reduction), [null,null,0,5]);
  assert.deepEqual(progressSeries([point(0,Infinity)])[0].points[0], {generation:0,penalty:null,reduction:null,percent:null});
});
test('negative starting penalty never yields a misleading percentage', () => {
  assert.equal(progressSeries([point(0,-2),point(1,-3)])[0].points[1].percent,null);
});
test('run, configuration and input changes are rejected rather than joined', () => {
  for (const field of ['run_id','input_fingerprint','configuration_fingerprint','engine_fingerprint','fitness_policy_id']) assert.throws(() => progressSeries([{...point(0,10),[field]:'initial'},{...point(1,5), [field]:'other'}]), /Cannot compare/);
});
test('partially supplied identity and explicitly noncomparable observations fail closed', () => {
  assert.throws(() => progressSeries([point(0,10), {...point(1,5),run_id:undefined}]), /Cannot compare/);
  assert.throws(() => progressSeries([point(0,10), {...point(1,5),metrics_comparable:false}]), /not comparable/);
});
test('different calls use independent same-run baselines', () => {
  assert.equal(progressSeries([point(0,100),point(1,90)])[0].points[1].reduction,10);
  assert.equal(progressSeries([point(0,50),point(1,49)])[0].points[1].reduction,1);
});
test('pagination uses preceding run observations and rejects incompatible prefixes', () => {
  const prefix = [point(0,100),point(1,80)], page = [point(50,70)];
  assert.equal(progressSeries(page,prefix)[0].points[0].reduction,30);
  assert.throws(() => progressSeries(page,[{...point(0,100),run_id:'other'}]), /Cannot compare/);
});
test('malformed or out-of-order generation identity is rejected', () => {
  for (const rows of [[point(-1,1)],[point(0.5,1)],[point(1,10),point(0,8)],[point(0,10),point(0,8)]]) assert.throws(() => progressSeries(rows), /ordered and unique/);
});
test('empty measurements stay empty without fabricated observations', () => assert.ok(progressSeries([]).every(line => line.points.length === 0)));
test('saved page has current empty state and an explicitly gated historical baseline', async () => {
  const source = await readFile(new URL('../src/pages/admin/ChromosomeViewer.tsx', import.meta.url),'utf8');
  assert.match(source,/No Current Best Chromosome/); assert.match(source,/Run the current Genetic Algorithm to generate/);
  assert.match(source,/!isVerifiedCurrent\(savedBest\)/); assert.match(source,/getSavedBestDownloadUrl/); assert.match(source,/analyzeUploadedChromosome/);
  const generate = await readFile(new URL('../src/pages/admin/GenerateSchedule.tsx', import.meta.url),'utf8');
  assert.doesNotMatch(generate,/preferred === "saved"/); assert.match(generate,/!isVerifiedCurrent\(savedBest\)/);
});
test('chart modes, exact values, explanatory labels, accessible points and independent baseline loading are wired', async () => {
  const source = await readFile(new URL('../src/components/ga/ConvergenceChart.tsx', import.meta.url),'utf8');
  for (const label of ['Optimization Progress','Penalty Reduction','Generation','Higher improvement indicates a greater reduction in scheduling penalties.','Raw Fitness Penalty','Original penalty','Absolute improvement','Percentage improvement']) assert.ok(source.includes(label));
  assert.match(source,/useState<ChartMode>\("improvement"\)/); assert.match(source,/tabIndex=\{0\}/);
  const history = await readFile(new URL('../src/pages/admin/GenerationHistory.tsx',import.meta.url),'utf8');
  assert.match(history,/Current Evaluation/); assert.match(history,/Historical Archive/); assert.match(history,/No Current GA Runs Yet/);
  const prefix = await readFile(new URL('../src/components/ga/RecordedProgress.tsx',import.meta.url),'utf8');
  assert.match(prefix,/start < offset/); assert.match(prefix,/no page-local baseline was substituted/);
});
