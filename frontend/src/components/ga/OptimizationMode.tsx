import {useEffect,useState} from "react";
import {Link} from "react-router-dom";
import {getContinuousReadiness} from "../../services/continuousOptimization";
import type {ContinuousReadiness,OptimizationMode as Mode} from "../../services/continuousOptimization";

export default function OptimizationMode({mode,onChange,population,fresh,runId}:{mode:Mode;onChange:(mode:Mode)=>void;population:number;fresh:number;runId:string|null}){
  const [attempt,setAttempt]=useState(0);
  const [result,setResult]=useState<{key:number;data:ContinuousReadiness}|null>(null),[error,setError]=useState<{key:number;message:string}|null>(null);
  const data=result?.key===attempt?result.data:null,message=error?.key===attempt?error.message:null;
  useEffect(()=>{if(mode!=="continuous")return;const abort=new AbortController();getContinuousReadiness(abort.signal).then(data=>{if(!abort.signal.aborted)setResult({key:attempt,data});}).catch(reason=>{if(!abort.signal.aborted)setError({key:attempt,message:reason instanceof Error?reason.message:"Continuous readiness unavailable. No run was started."});});return()=>abort.abort();},[mode,attempt]);
  return <section aria-label="Optimization mode" className="space-y-4 rounded-xl border border-teal-200 bg-white p-5 shadow-sm">
    <h2 className="text-lg font-semibold text-teal-950">Optimization Mode</h2>
    <fieldset className="flex flex-wrap gap-5"><legend className="sr-only">Select an optimization mode</legend>{([['fixed','Fixed Generations'],['continuous','Continuous Optimization']] as const).map(([value,label])=><label key={value} className="flex items-center gap-2"><input type="radio" name="optimizationMode" value={value} checked={mode===value} onChange={()=>{setAttempt(a=>a+1);onChange(value);}}/>{label}</label>)}</fieldset>
    {mode==="fixed"?<p className="text-sm text-slate-600">Existing fixed-generation execution, parameters, checkpoints and backend-confirmed monitoring remain in use. Mode selection never starts a run.</p>:<div className="space-y-3" aria-label="Continuous optimization foundation">
      <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">Continuous Mode is unavailable in this release. No continuous worker, run or checkpoint has been created. A large generation limit or repeated fixed runs would not establish continuous optimization.</p>
      <dl className="grid gap-3 text-sm sm:grid-cols-2"><div><dt>Population size (existing fixed draft)</dt><dd>{population}</dd></div><div><dt>Fresh chromosomes (existing fixed draft)</dt><dd>{fresh}</dd></div></dl>
      {!data&&!message&&<p role="status" className="animate-pulse rounded bg-slate-100 p-3">Checking continuous-mode prerequisites...</p>}
      {message&&<p role="alert" className="rounded bg-red-50 p-3 text-sm">{message}</p>}
      <button type="button" className="ccs-btn-secondary" onClick={()=>setAttempt(a=>a+1)}>Retry continuous readiness</button>
      {data&&<><h3 className="font-semibold">Execution blockers</h3><ul className="list-disc space-y-2 pl-5 text-sm">{data.requirements.map(r=><li key={r.code}><strong>{r.code.replaceAll('_',' ')}</strong>: {r.message}</li>)}</ul>
        <p className="text-sm">U5D receipt capability: {data.receipt_capability}. Actual optimizer consumption: {data.input_consumption}. Institutional authority: {data.institutional_authorization}.</p>
        <details className="rounded border border-slate-200 p-3 text-sm"><summary>Lifecycle and required safeguards (not active)</summary><p className="mt-2">Contract vocabulary only: {data.lifecycle.states.join(' → ')}. This list is not a run history; continuous lifecycle commands are unavailable.</p><ul className="mt-2 list-disc pl-5">{data.safeguards.required.map(s=><li key={s}>{s.replaceAll('_',' ')}</li>)}</ul><p className="mt-2">Optional stopping conditions, resource budgets, storage quotas, checkpoint recovery and stop confirmation require an approved versioned worker before activation. No limits are represented as enforced here.</p></details>
      </>}
      <button type="button" className="ccs-btn-primary" disabled aria-describedby="continuous-mode-blocked">Start Optimization — unavailable</button>
      <p id="continuous-mode-blocked" className="text-sm">Continuous start/pause/resume/stop are not installed. Existing fixed-run controls below operate only on their backend-confirmed run. No receipt is promoted, no schedule is approved and no historical Saved Best is changed by this mode.</p>
      {runId&&<Link className="inline-block text-sm text-teal-800 underline" to={`/admin/analysis?view=advanced&run=${encodeURIComponent(runId)}&candidate=best_ever`}>Inspect existing run analysis</Link>}
    </div>}
  </section>;
}
