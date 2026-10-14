import {test} from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import {preferenceError, updateFacultyPreference} from '../src/api/preferences.ts';

test('authentication, storage and validation errors are shown accurately', () => {
  for (const [status,detail] of [[401,'Authentication is not configured; no changes were saved.'],[503,'Storage is corrupt; existing data preserved.'],[403,'You may only update your own faculty preferences.']]) {
    const error=new axios.AxiosError('request failed');error.response={status,data:{detail}};
    assert.equal(preferenceError(error,'fallback'),detail);
  }
  const error=new axios.AxiosError('invalid');error.response={status:422,data:{detail:[{msg:'Extra inputs are not permitted'}]}};
  assert.match(preferenceError(error,'fallback'),/Review.*Extra inputs/);
  assert.equal(preferenceError(new Error('offline'),'Retry loading'),'Retry loading');
});

test('disabled flags and optional null fields round trip without client identity headers', async () => {
  const before=axios.put;
  const draft={use_day_preference:false,use_time_preference:false,preferred_start_time:null,preferred_end_time:null};
  axios.put=async(url,data,options)=>{assert.match(url,/\/preferences\/0$/);assert.equal(options,undefined);assert.deepEqual(data,draft);return {data:{faculty_code:0,...data}};};
  try {assert.deepEqual(await updateFacultyPreference(0,draft),{faculty_code:0,...draft});}
  finally {axios.put=before;}
});

test('a denied save rejects instead of returning fabricated success',async()=>{
  const before=axios.put;
  const failure=new axios.AxiosError('unauthorized');failure.response={status:401,data:{detail:'Authentication required'}};
  axios.put=async()=>{throw failure;};
  try {await assert.rejects(updateFacultyPreference(0,{}),error=>error===failure);}
  finally {axios.put=before;}
});
