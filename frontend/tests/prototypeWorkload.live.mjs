// Real Node HTTP + frontend model + FastAPI/session/SQLite. Not a browser test.
import assert from 'node:assert/strict';
import {changeFor, validateView} from '../src/prototypeWorkload/model.mjs';
let wire='';for await(const chunk of process.stdin)wire+=chunk;
const input=JSON.parse(wire);wire='';
assert.equal(new URL(input.base).hostname,'127.0.0.1');
let cookie='',csrf='';const scenarios=[];
async function request(path,method='GET',body,secure=true){
  const response=await fetch(input.base+path,{method,signal:AbortSignal.timeout(10000),headers:{'Content-Type':'application/json',Origin:input.base,...(cookie?{Cookie:cookie}:{}),...(secure&&csrf?{'X-CSRF-Token':csrf}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  return response;
}
async function check(name,fn){await fn();scenarios.push({name,status:'PASS'});}
async function login(username){
  const response=await request('/api/auth/login','POST',{username,password:input.password});assert.equal(response.status,200);
  cookie=response.headers.get('set-cookie').split(';')[0];csrf=(await response.json()).csrf_token;
}
try{
 await check('anonymous denied',async()=>assert.equal((await request('/api/prototype/workload')).status,401));
 await check('real session login',()=>login('editor@fictional.invalid'));
 let view;
 await check('server captured bundle and policy loaded',async()=>{const response=await request('/api/prototype/workload');assert.equal(response.status,200);view=validateView(await response.json());assert.equal(view.policy.revision,input.reopened?1:0);});
 if(!input.reopened){
  const change=changeFor(view,new Map([[1,''],[2,'24']]));
  await check('frontend rejects fractional minimum',async()=>assert.throws(()=>changeFor(view,new Map([[2,'24.5']]))));
  await check('real CSRF rejection',async()=>assert.equal((await request('/api/prototype/workload','PUT',change,false)).status,403));
  await check('persisted save and infeasible12 versus24',async()=>{const response=await request('/api/prototype/workload','PUT',change);assert.equal(response.status,200);assert.equal(response.headers.get('cache-control'),'no-store');view=validateView(await response.json());assert.equal(view.preflight,'MINIMUM_WORKLOAD_INFEASIBLE');assert.equal(view.faculty[1].proven_shortfall,12);assert.equal(view.faculty[0].minimum_teaching_units,null);});
  await check('real reload preserves revision',async()=>assert.equal((await(await request('/api/prototype/workload')).json()).policy.revision,1));
  await check('stale update denied',async()=>assert.equal((await request('/api/prototype/workload','PUT',change)).status,409));
  await check('client department authority rejected',async()=>assert.equal((await request('/api/prototype/workload','PUT',{...change,department_id:'forged'})).status,422));
 }else{
  await check('HTTP listener restart preserves minimum and infeasibility',async()=>{assert.equal(view.faculty[1].minimum_teaching_units,24);assert.equal(view.preflight,'MINIMUM_WORKLOAD_INFEASIBLE');});
 }
 await check('actual frontend assets served',async()=>{const page=await request('/prototype/workload');assert.equal(page.status,200);assert.match(await page.text(),/Teaching workload qualification/);assert.match(await(await request('/prototype/workload/console.mjs')).text(),/changeFor/);});
 await check('logout invalidates session',async()=>{assert.equal((await request('/api/auth/logout','POST')).status,204);assert.equal((await request('/api/prototype/workload')).status,401);});
 await check('real unscoped administrator denied',async()=>{await login('unscoped@fictional.invalid');assert.equal((await request('/api/prototype/workload')).status,403);});
 assert.equal(view.optimizer_executed,false);
 console.log(JSON.stringify({scope:'REAL_LOOPBACK_NODE_HTTP_FRONTEND_MODEL_FASTAPI_COOKIE_SESSION_PRIVATE_SQLITE; NO_BROWSER_OR_GA_WORKER',scenarios,policy_revision:view.policy.revision,policy_digest:view.policy.digest,bundle_fingerprint:view.bundle_fingerprint,optimizer_executed:false,reopened:input.reopened,mocked_HTTP_responses:0}));
}catch(error){console.error('Prototype HTTP acceptance failed: '+error.message);process.exitCode=1;}
finally{input.password='';cookie='';csrf='';}
