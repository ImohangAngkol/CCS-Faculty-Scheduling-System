import {useEffect,useState} from "react";
import {Link,useSearchParams} from "react-router-dom";
import {constrainedStatus,currentConstraints,startConstrained,constrainedRun,controlConstrained,constrainedError} from "../../api/constrainedGA";
import type {ConstraintSet,ConstrainedRun,SeedMode} from "../../api/constrainedGA";

const button="rounded-lg border border-teal-700 px-3 py-2 text-sm font-medium text-teal-800 disabled:opacity-40";

export default function ConstrainedRunPanel(){
  const [params,setParams]=useSearchParams(),runId=params.get("v2run")??"";
  const [year,setYear]=useState(""),[term,setTerm]=useState(""),[seed,setSeed]=useState<SeedMode>("fresh");
  const [population,setPopulation]=useState(10),[generations,setGenerations]=useState(5);
  const [scope,setScope]=useState<ConstraintSet|null>(null),[job,setJob]=useState<ConstrainedRun|null>(null);
  const [notice,setNotice]=useState("Checking V2 availability…"),[error,setError]=useState(""),[busy,setBusy]=useState(false),[refresh,setRefresh]=useState(0);
  useEffect(()=>{const abort=new AbortController();constrainedStatus(abort.signal).then(value=>setNotice(value.message)).catch(reason=>{if(!abort.signal.aborted)setNotice(constrainedError(reason));});return()=>abort.abort();},[]);
  useEffect(()=>{
    if(!runId)return;
    const abort=new AbortController();let timer:ReturnType<typeof setTimeout>;
    async function poll(){try{const value=await constrainedRun(runId,abort.signal);if(abort.signal.aborted)return;setJob(value);setError("");if(value.execution_active)timer=setTimeout(poll,1000);}catch(reason){if(!abort.signal.aborted){setJob(null);setError(constrainedError(reason));}}}
    void poll();return()=>{abort.abort();clearTimeout(timer);};
  },[runId,refresh]);
  async function check(){setBusy(true);setError("");setScope(null);try{setScope(await currentConstraints(year,term));}catch(reason){setError(constrainedError(reason));}finally{setBusy(false);}}
  async function start(){if(!scope)return;setBusy(true);setError("");try{const value=await startConstrained(scope,seed,{population_size:population,generations});setJob(value);setParams(previous=>{const next=new URLSearchParams(previous);next.set("v2run",value.run_id);return next;});}catch(reason){setError(constrainedError(reason));setScope(null);}finally{setBusy(false);}}
  async function control(action:"pause"|"resume"|"stop"){setBusy(true);setError("");try{setJob(await controlConstrained(runId,action));setRefresh(v=>v+1);}catch(reason){setError(constrainedError(reason));}finally{setBusy(false);}}
  const currentJob=job?.run_id===runId?job:null;
  return <section aria-label="Constrained V2 scheduling" className="space-y-4 rounded-xl border border-teal-200 bg-teal-50/50 p-5">
    <h2 className="text-lg font-semibold text-teal-900">Confirmed GEC constraints — V2</h2>
    <p className="text-sm text-slate-700">{notice}</p>
    <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">V2 results remain GA-generated proposals. Constrained generation does not constitute Chair approval or an official schedule. Legacy V1 controls remain below.</p>
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-sm">Academic year<input aria-label="V2 academic year" value={year} onChange={e=>{setYear(e.target.value);setScope(null);}} placeholder="Sourced YYYY-YYYY" maxLength={40} className="mt-1 block rounded-lg border border-slate-300 bg-white p-2"/></label>
      <label className="text-sm">Term<input aria-label="V2 term" value={term} onChange={e=>{setTerm(e.target.value);setScope(null);}} placeholder="Exact sourced term" maxLength={120} className="mt-1 block rounded-lg border border-slate-300 bg-white p-2"/></label>
      <button className={button} disabled={busy||!year.trim()||!term.trim()||currentJob?.execution_active} onClick={()=>void check()}>Check confirmed constraints</button>
    </div>
    {scope&&<div className="space-y-2 text-sm"><p>{scope.commitments} fixed weekly commitments; {scope.revisions.length} current confirmed revisions.</p><p className="break-all">Constraint set: {scope.constraint_digest}</p><div className="flex flex-wrap gap-3"><label>V2 population (2–50)<input aria-label="V2 population" type="number" min={2} max={50} value={population} onChange={e=>setPopulation(Number(e.target.value))} className="ml-2 w-20 rounded border bg-white p-2"/></label><label>V2 generations (1–100)<input aria-label="V2 generations" type="number" min={1} max={100} value={generations} onChange={e=>setGenerations(Number(e.target.value))} className="ml-2 w-20 rounded border bg-white p-2"/></label></div><label>Requested seed <select aria-label="V2 requested seed" value={seed} onChange={e=>setSeed(e.target.value as SeedMode)} className="rounded border bg-white p-2"><option value="fresh">Fresh V2 population</option><option value="saved">Validate saved V1 seed</option><option value="uploaded">Validate uploaded seed</option></select></label><p>Incompatible requested seeds are rejected; no automatic fallback is used. Server retry limits remain bounded.</p><button className={button} disabled={busy||currentJob?.execution_active||!Number.isInteger(population)||population<2||population>50||!Number.isInteger(generations)||generations<1||generations>100} onClick={()=>void start()}>Start constrained V2</button></div>}
    {busy&&<p role="status">Checking the current constraint boundary…</p>}
    {error&&<div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error} <button className={button} disabled={busy} onClick={()=>runId?setRefresh(v=>v+1):void check()}>Retry V2</button></div>}
    {currentJob&&<div className="space-y-2 text-sm"><p role="status">V2: {currentJob.status} · Generation {currentJob.generation??"not yet committed"}</p>{currentJob.error&&<p role="alert">{currentJob.error.code}: {currentJob.error.message}</p>}<div className="flex flex-wrap gap-2">
      {currentJob.execution_active&&<><button className={button} disabled={busy} onClick={()=>void control("pause")}>Pause V2</button><button className={button} disabled={busy} onClick={()=>void control("stop")}>Stop V2</button></>}
      {!currentJob.execution_active&&currentJob.status==="PAUSED"&&<><button className={button} disabled={busy} onClick={()=>void control("resume")}>Resume V2</button><button className={button} disabled={busy} onClick={()=>void control("stop")}>Stop V2</button></>}
      <Link className={button} to={`/admin/schedules?v2run=${encodeURIComponent(runId)}`}>View V2 proposal</Link><Link className={button} to={`/admin/analysis?v2run=${encodeURIComponent(runId)}`}>V2 fitness and provenance</Link>
    </div><dl>{Object.entries(currentJob.diagnostics).map(([code,count])=><div key={code}><dt className="inline">{code}: </dt><dd className="inline">{count}</dd></div>)}</dl></div>}
  </section>;
}
