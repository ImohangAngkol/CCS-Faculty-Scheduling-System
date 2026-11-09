import {useEffect,useRef,useState} from "react";
import {Link,Navigate} from "react-router-dom";
import {useAuth} from "../context/AuthContext";
import {accountHome} from "../services/auth";
import AccountMenu from "../components/common/AccountMenu";
import MetadataState from "../components/dashboard/MetadataState";
import ConvergenceChart from "../components/ga/ConvergenceChart";
import {researchCapabilities,researchRuns,researchDetail,researchEvents} from "../api/researchObservations";
import type {ResearchDetail,ResearchEvent,ResearchRun} from "../api/researchObservations";
const box="rounded-xl border border-slate-200 bg-white p-5 space-y-3";
const message="Research observations unavailable or access denied. An isolated authorized source is required. No operation was performed.";
export default function ResearchConsole(){
  const {user,status,error,refresh}=useAuth();
  if(status==="loading")return <MetadataState title="Verifying session" description="Checking your account."/>;
  if(status==="error")return <MetadataState title="Session unavailable" description={error} retry={()=>void refresh()}/>;
  if(!user)return <Navigate to="/login" replace/>;
  return <Console key={user.id}/>;
}
function Console(){
  const {user}=useAuth();const [attempt,retry]=useState(0),[offset,setOffset]=useState(0),[selected,select]=useState<string>();
  const [view,setView]=useState<{key:string;items:ResearchRun[];next:number|null;error?:string}>();const key=`${offset}:${attempt}`;
  useEffect(()=>{const abort=new AbortController();void(async()=>{try{await researchCapabilities(abort.signal);const rows=await researchRuns(offset,abort.signal);if(!abort.signal.aborted)setView({key,items:rows.items,next:rows.next_offset});}catch{if(!abort.signal.aborted)setView({key,items:[],next:null,error:message});}})();return()=>abort.abort();},[offset,key]);
  const current=view?.key===key?view:undefined;
  return <div className="min-h-screen bg-slate-50"><AccountMenu/><main className="mx-auto max-w-6xl space-y-5 p-4 sm:p-8">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5 space-y-2"><h1 className="text-2xl font-bold text-teal-950">Isolated research console</h1><p>Read-only fictional GA research. Not institutional authorization or publication.</p><p className="font-semibold text-amber-900">Production admission and Saved Best promotion: BLOCKED · Continuous Optimization: DISABLED · Active restore: BLOCKED · Seven-day readiness: NO-GO</p><Link to={accountHome(user!)} className="text-teal-800 underline">Return to dashboard</Link></header>
    <section className={box}><h2 className="text-lg font-bold text-teal-900">Research run history</h2><button className="ccs-btn-secondary" onClick={()=>{select(undefined);retry(n=>n+1);}}>Refresh run history</button>
      {!current?<MetadataState title="Loading research observations" description="Checking scoped read access."/>:current.error?<MetadataState title="Research source unavailable" description={current.error} retry={()=>retry(n=>n+1)}/>:!current.items.length?<p role="status">No research runs in your authorized scope.</p>:<ul className="space-y-2">{current.items.map(r=><li key={r.run_id}><button className="w-full break-all rounded-lg border p-3 text-left hover:border-teal-600" aria-pressed={selected===r.run_id} onClick={()=>select(r.run_id)}>{r.run_id} · {r.state} · Best penalty: {r.best_so_far_fitness===null?"Unavailable":String(r.best_so_far_fitness)}</button></li>)}</ul>}
      <div className="flex gap-3"><button className="ccs-btn-secondary" disabled={!offset} onClick={()=>{select(undefined);setOffset(n=>Math.max(0,n-10));}}>Previous runs</button><button className="ccs-btn-secondary" disabled={!current?.next} onClick={()=>{select(undefined);setOffset(current!.next!);}}>More runs</button></div>
    </section>
    {selected&&current&&!current.error&&<Detail key={`${selected}:${key}`} run={selected}/>}
  </main></div>;
}
function Detail({run}:{run:string}){
  const [attempt,retry]=useState(0),[view,setView]=useState<{key:number;data?:ResearchDetail;error?:string}>();
  const [extra,setExtra]=useState<{key:number;items:ResearchEvent[];next:number|null;error?:string}>();
  useEffect(()=>{const abort=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;let polls=0;
    const load=async()=>{try{const data=await researchDetail(run,abort.signal);if(abort.signal.aborted)return;setView({key:attempt,data});
      if(["RUNNING","RESUMING","PAUSING","STOPPING"].includes(data.overview.state)&&polls++<6)timer=setTimeout(()=>void load(),10000);
    }catch{if(!abort.signal.aborted)setView({key:attempt,error:message});}};
    void load();return()=>{abort.abort();if(timer)clearTimeout(timer);};
  },[run,attempt]);
  const current=view?.key===attempt?view:undefined,data=current?.data;
  if(!current)return <MetadataState title="Loading selected run" description="Reading durable observations."/>;
  if(!data)return <MetadataState title="Run observations unavailable" description={current.error??message} retry={()=>{setExtra(undefined);retry(n=>n+1);}}/>;
  const detail=data.overview,events=extra?.key===attempt?extra.items:data.telemetry.items,next=extra?.key===attempt?extra.next:data.telemetry.next_after;
  return <section className={box} aria-label="Selected research run"><h2 className="text-xl font-bold text-teal-900">Run overview</h2><p className="break-all">{run}</p><p>State: <strong>{detail.state}</strong> ({detail.state_classification.toLowerCase()}) · Worker record: {detail.worker_state}</p><p>Termination/interruption reason: {detail.reason??"Unavailable / not recorded"}</p><p>Generation: {detail.generation??"Unavailable"} · Best-so-far penalty: <strong>{detail.best_so_far_fitness===null?"Unavailable":String(detail.best_so_far_fitness)}</strong></p><p>Current fitness: unavailable (not exposed). Satisfaction metrics: unavailable (not emitted).</p>
    <button className="ccs-btn-secondary" onClick={()=>{setExtra(undefined);retry(n=>n+1);}}>Refresh selected observations</button><p className="text-sm text-slate-600">Active runs receive at most six automatic refreshes, ten seconds apart. Reads stop on error, terminal state or navigation.</p>
    <div className="rounded border border-teal-200 bg-teal-50 p-4"><h3 className="font-semibold">Trusted context summary</h3><p>{detail.context_qualification}</p><p>{data.provenance.context.academic_year} · {data.provenance.context.term} · {data.provenance.context.dataset_identity}</p><dl className="space-y-1 text-xs">{Object.entries(data.provenance.context).map(([k,v])=><div key={k} className="break-all"><dt className="inline font-semibold">{k}: </dt><dd className="inline">{v}</dd></div>)}</dl><p className="break-all text-xs">Context identity: {detail.context_id}</p><p>Technical fictional input verification does not establish institutional approval.</p></div>
    <h3 className="font-semibold">Recorded fitness history</h3>{data.fitness.availability==="OBSERVED"?<><ConvergenceChart key={run} history={data.fitness.points.map(p=>({...p,input_fingerprint:detail.context_id,configuration_fingerprint:data.provenance.configuration_fingerprint}))}/><table className="w-full text-left text-sm"><caption>Exact recorded best-ever penalties; lower is better.</caption><thead><tr><th>Generation</th><th>Best-ever penalty</th></tr></thead><tbody>{data.fitness.points.map(p=><tr key={p.generation}><td>{p.generation}</td><td>{String(p.best_ever_fitness)}</td></tr>)}</tbody></table></>:<p role="status">Generation-level fitness history unavailable: no verified history was recorded.</p>}
    <h3 className="font-semibold">Execution timeline</h3><p className="text-sm">{data.observation_notice}</p><ol className="space-y-2">{events.map(e=><li className="rounded border p-3 text-sm" key={e.sequence}>#{e.sequence} · {e.worker_state??e.recovery_state??"Recorded observation"} · {new Date(e.observed_at*1000).toISOString()}<p>{e.exit_reason??e.reason??"No reason recorded"}</p><p>Generation {e.generation??"unavailable"} · Best {e.best_so_far_fitness===null||e.best_so_far_fitness===undefined?"unavailable":String(e.best_so_far_fitness)}</p><p>{e.generation_and_best_classification??e.classification??"Unavailable"}</p></li>)}</ol>{!events.length&&<p>No persisted telemetry is available.</p>}
    {next!==null&&<MoreEvents key={`${run}:${attempt}:${next}`} run={run} after={next} context={detail.context_id} onPage={page=>setExtra({key:attempt,items:[...events,...page.items],next:page.next_after})}/>}
    <h3 className="font-semibold">Checkpoint metadata</h3><p>Sequence {detail.checkpoint_sequence} · Active restoration unavailable.</p><p className="break-all text-xs">{detail.checkpoint_fingerprint??"No checkpoint recorded"}</p>
  </section>;
}
function MoreEvents({run,after,context,onPage}:{run:string;after:number;context:string;onPage:(page:Awaited<ReturnType<typeof researchEvents>>)=>void}){
  const pending=useRef<AbortController|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  useEffect(()=>()=>{pending.current?.abort();},[]);
  async function load(){
    pending.current?.abort();const c=new AbortController();pending.current=c;setBusy(true);setError("");
    try{const page=await researchEvents(run,after,context,c.signal);if(!c.signal.aborted)onPage(page);}
    catch{if(!c.signal.aborted)setError(message);}
    finally{if(!c.signal.aborted)setBusy(false);}
  }
  return <><button className="ccs-btn-secondary" disabled={busy} onClick={()=>void load()}>More observations</button>{error&&<p role="alert">{error}</p>}</>;
}
