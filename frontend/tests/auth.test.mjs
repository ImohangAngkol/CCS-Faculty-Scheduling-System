import {test} from 'node:test';
import assert from 'node:assert/strict';
import {accountHome, authRequest, validateSession, AuthError} from '../src/services/auth.ts';
import {apiClient, apiFetch, setSessionSecurity} from '../src/services/apiSession.ts';

test('role home is derived from server role and malformed binding is rejected',()=>{
  const base={user:{id:'server-user',username:'user@test.invalid',role:'faculty',is_active:true,faculty_id:'uuid',faculty:{faculty_id:'uuid',faculty_code:3}},csrf_token:'csrf',expires_at:'2099-01-01T00:00:00Z'};
  assert.equal(validateSession(base),base);
  assert.equal(accountHome(base.user),'/faculty');
  assert.equal(accountHome({...base.user,role:'admin'}),'/admin');
  assert.throws(()=>validateSession({...base,user:{...base.user,faculty:{faculty_id:'other',faculty_code:0}}}),AuthError);
  assert.throws(()=>validateSession({...base,user:{...base.user,is_active:false}}),AuthError);
  assert.throws(()=>validateSession({...base,user:{...base.user,role:'superuser'}}),AuthError);
});

test('fetch sends cookies, memory-only CSRF and existing GA process headers',async()=>{
  const original=global.fetch;setSessionSecurity('verified-csrf');
  global.fetch=async(url,options)=>{assert.equal(options.credentials,'include');assert.equal(options.headers.get('X-CSRF-Token'),'verified-csrf');assert.equal(options.headers.get('X-GA-Process-ID'),'process');return Response.json({});};
  try {await apiFetch('http://localhost:8000/api/ga/runs/id/pause',{method:'POST',headers:{'X-GA-Process-ID':'process'}});}
  finally {global.fetch=original;setSessionSecurity(null);}
});

test('GET is read-only and axios shares cookie and CSRF transport',async()=>{
  const original=global.fetch;setSessionSecurity('csrf');
  global.fetch=async(url,options)=>{assert.equal(options.credentials,'include');assert.equal(options.headers.get('X-CSRF-Token'),null);return Response.json({});};
  try {await apiFetch('http://localhost:8000/api/auth/me');
    await apiClient.put('/preferences/3',{}, {adapter:async config=>{assert.equal(config.withCredentials,true);assert.equal(config.headers.get('X-CSRF-Token'),'csrf');return {status:200,statusText:'OK',headers:{},config,data:{}};}});
  } finally {global.fetch=original;setSessionSecurity(null);}
});

test('auth errors preserve 401/403/503 and network failures are actionable',async()=>{
  const original=global.fetch;
  try {
    for(const status of [401,403,503]){global.fetch=async()=>Response.json({detail:'specific failure'},{status});await assert.rejects(authRequest('/me'),error=>error.status===status&&error.message==='specific failure');}
    global.fetch=async()=>{throw Error('offline');};await assert.rejects(authRequest('/me'),/Check the backend and identity database/);
  }finally{global.fetch=original;}
});
