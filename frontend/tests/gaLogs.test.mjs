import {test} from 'node:test';
import assert from 'node:assert/strict';
import {emptyLogHistory, mergeRunLogs, validateRunLogs, logPollDelay, needsLogReplay} from '../src/services/gaLogs.ts';

const entry = (sequence, message=`line ${sequence}`) => ({sequence,message,timestamp:'2026-10-11T03:00:00Z',line_truncated:false});
const page = (entries, overrides={}) => ({run_id:'run',process_instance_id:'process',log_epoch:'epoch',state:'RUNNING',execution_active:true,
  entries,latest_sequence:entries.at(-1)?.sequence??0,next_sequence:entries.at(-1)?.sequence??0,has_more:false,earlier_logs_truncated:false,cursor_reset:false,...overrides});

test('initial, pause, refresh and resume diagnostics preserve ordering and suppress duplicate sequences',()=>{
  let history=mergeRunLogs(emptyLogHistory(),page([entry(1),entry(2,'GENETIC ALGORITHM PAUSED')],{state:'PAUSED',execution_active:false}));
  history=mergeRunLogs(history,page([entry(2,'GENETIC ALGORITHM PAUSED'),entry(3,'GENETIC ALGORITHM RESUMING'),entry(4,'mutation')]));
  assert.deepEqual(history.entries.map(line=>line.sequence),[1,2,3,4]);
  assert.equal(history.cursor,4);
  const refreshed=mergeRunLogs(emptyLogHistory(),page(history.entries));
  assert.deepEqual(refreshed.entries,history.entries);
});
test('identical text on different sequences remains distinct and the frontend keeps only 500 entries',()=>{
  let history=emptyLogHistory();
  for(let sequence=1;sequence<=600;sequence+=100) history=mergeRunLogs(history,page(Array.from({length:100},(_,i)=>entry(sequence+i,'mutation'))));
  assert.equal(history.entries.length,500);assert.equal(history.entries[0].sequence,101);assert.equal(history.cursor,600);
});
test('cursor advances to delivered entries instead of skipping a response backlog',()=>{
  const first=page([entry(1),entry(2)],{latest_sequence:8,has_more:true});
  assert.equal(mergeRunLogs(emptyLogHistory(),first).cursor,2);
  assert.equal(logPollDelay(first),250);
});
test('restart or buffer eviction resets log epoch without inventing another GA run',()=>{
  const history=mergeRunLogs(emptyLogHistory(),page([entry(12)]));
  const missing=mergeRunLogs(history,page([],{log_epoch:'restarted',cursor_reset:true,earlier_logs_truncated:true,state:'PAUSED',execution_active:false}));
  assert.equal(missing.cursor,0);assert.equal(missing.truncated,true);assert.deepEqual(missing.entries,[]);
  const resumed=mergeRunLogs(missing,page([entry(1,'resuming')],{log_epoch:'restarted'}));
  assert.deepEqual(resumed.entries.map(line=>line.message),['resuming']);
});
test('truncated history notice persists across incremental requests',()=>{
  let history=mergeRunLogs(emptyLogHistory(),page([entry(99)],{earlier_logs_truncated:true}));
  history=mergeRunLogs(history,page([entry(100)]));assert.equal(history.truncated,true);
});
test('buffer epoch change replays from zero even when new sequence numbers exceed the old cursor',()=>{
  const history=mergeRunLogs(emptyLogHistory(),page([entry(2)]));
  assert.equal(needsLogReplay(history,page([entry(3)],{log_epoch:'new'})),true);
  assert.equal(needsLogReplay(history,page([entry(1)],{log_epoch:'new',cursor_reset:true})),false);
});
test('paused monitoring is slower; terminal monitoring drains logs then stops',()=>{
  assert.equal(logPollDelay(page([],{state:'PAUSED',execution_active:false})),5000);
  for(const state of ['STOPPED','COMPLETED','FAILED','INTERRUPTED']) {
    assert.equal(logPollDelay(page([],{state,execution_active:false})),null);
    assert.equal(logPollDelay(page([entry(1)],{state,execution_active:false,latest_sequence:2,has_more:true})),250);
    assert.equal(logPollDelay(page([],{state,execution_active:true})),1000);
  }
});
test('invalid identities, lifecycle, order and cursors are rejected',()=>{
  assert.deepEqual(validateRunLogs(page([entry(1)]),'run','process'),page([entry(1)]));
  for(const value of [page([],{run_id:'other'}),page([],{process_instance_id:'other'}),page([],{state:'invented'}),
    page([entry(2),entry(1)]),page([entry(1),entry(1)]),page([],{next_sequence:4}),page([],{has_more:true}),
    page([entry(1)],{next_sequence:0}),page([{...entry(1),timestamp:'invalid'}])]) {
    assert.throws(()=>validateRunLogs(value,'run','process'),/invalid/);
  }
});
