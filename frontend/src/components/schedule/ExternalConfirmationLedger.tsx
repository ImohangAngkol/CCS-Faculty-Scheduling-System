import {useEffect,useState} from "react";
import {listConfirmations,confirmationHistory,confirmationRevision,proposeConfirmation,requestConfirmation,confirmRevision,revokeConfirmation} from "../../api/externalConfirmations";
import type {ConfirmationReview,LedgerHistory,RevisionDetail} from "../../api/externalConfirmations";
import {metadataError} from "../../services/dashboardMetadata";

export default function ExternalConfirmationLedger({review}:{review?:ConfirmationReview}) {
  const [records,setRecords]=useState<Awaited<ReturnType<typeof listConfirmations>>>();
  const [selected,setSelected]=useState("");const [history,setHistory]=useState<LedgerHistory>();
  const [revision,setRevision]=useState("");const [detail,setDetail]=useState<RevisionDetail>();const [current,setCurrent]=useState<RevisionDetail>();
  const [reason,setReason]=useState("");const [error,setError]=useState("");const [message,setMessage]=useState("");
  const [eligibleFor,setEligibleFor]=useState<{review:ConfirmationReview;selected:string;revision:string;reload:number;reason:string}>();const [busy,setBusy]=useState(false);const [reload,setReload]=useState(0);
  const eligible=!!eligibleFor&&eligibleFor.review===review&&eligibleFor.selected===selected&&eligibleFor.revision===revision&&eligibleFor.reload===reload&&eligibleFor.reason===reason;
  function chooseRecord(value:string){setSelected(value);setHistory(undefined);setRevision("");setDetail(undefined);setCurrent(undefined);setEligibleFor(undefined);}
  function chooseRevision(value:string){setRevision(value);setDetail(undefined);setEligibleFor(undefined);}
  function refresh(){setRecords(undefined);setHistory(undefined);setRevision("");setDetail(undefined);setCurrent(undefined);setError("");setEligibleFor(undefined);setReload(v=>v+1);}
  useEffect(()=>{const abort=new AbortController();void listConfirmations(abort.signal).then(setRecords).catch(e=>{if(!abort.signal.aborted)setError(metadataError(e,"Durable ledger unavailable. Contact the system administrator; no success is claimed."));});return ()=>abort.abort();},[reload]);
  useEffect(()=>{const abort=new AbortController();if(selected)void confirmationHistory(selected,abort.signal).then(async value=>{if(abort.signal.aborted)return;setHistory(value);if(value.record.current_revision_id){const snapshot=await confirmationRevision(value.record.current_revision_id,abort.signal);if(!abort.signal.aborted)setCurrent(snapshot);}}).catch(e=>{if(!abort.signal.aborted)setError(metadataError(e,"Could not load history."));});return ()=>abort.abort();},[selected,reload]);
  useEffect(()=>{const abort=new AbortController();if(revision)void confirmationRevision(revision,abort.signal).then(v=>{if(!abort.signal.aborted)setDetail(v);}).catch(e=>{if(!abort.signal.aborted)setError(metadataError(e,"Could not load revision."));});return ()=>abort.abort();},[revision]);
  async function act(kind:"propose"|"request"|"confirm"|"revoke") {
    setError("");setMessage("");setEligibleFor(undefined);setBusy(true);
    try {
      const version=history?.record.version??0;
      if(kind==="propose"&&review){const id=selected||crypto.randomUUID();await proposeConfirmation(id,version,reason,review);chooseRecord(id);setMessage("Proposed revision stored. This is not institutional confirmation.");refresh();}
      else if(kind==="request"&&review&&revision){const result=await requestConfirmation(revision,version,reason,review);setEligibleFor(result.eligible&&review?{review,selected,revision,reload,reason}:undefined);setMessage(result.state+": "+result.message+(result.blocker?" ("+result.blocker+")":""));}
      else if(kind==="confirm"&&review&&revision){await confirmRevision(revision,version,reason,review);setMessage("Confirmation recorded by server authorization. Not active in GA.");refresh();}
      else if(kind==="revoke"&&selected){await revokeConfirmation(selected,version,reason);setMessage("Revocation recorded; prior history retained. No older revision was restored.");refresh();}
    } catch(e){setError(metadataError(e,"Operation rejected or persistence unavailable. Reload history before retrying; no success is claimed."));}
    finally{setBusy(false);}
  }
  return <section aria-label="Durable GEC confirmation ledger" className="min-w-0 space-y-3 rounded-xl border border-teal-300 bg-white p-5">
    <h2 className="text-xl font-semibold text-teal-900">GEC confirmation and revision history</h2>
    <p>Durable proposals and authorized decision records · Not active in GA. Administrator role and verified evidence alone do not grant institutional confirmation authority.</p>
    {!records&&!error&&<p role="status">Loading durable ledger…</p>}
    {error&&<p role="alert" className="break-words text-red-900">{error}</p>}
    <button type="button" className="ccs-btn-secondary" disabled={busy} onClick={refresh}>Reload ledger history</button>
    {records&&<><p>{records.confirmation_policy}</p>{!records.records.length&&<p>No durable GEC records exist.</p>}{records.has_more&&<p>Only the first 100 records are shown; additional records require a future paginated view.</p>}
      <label className="block">Record<select aria-label="GEC ledger record" className="block w-full min-w-0 rounded border p-2" value={selected} onChange={e=>chooseRecord(e.target.value)}><option value="">New record</option>{records.records.map(r=><option key={r.id} value={r.id}>{r.supplier} · {r.academic_year} · {r.term} · {r.status} · {r.id}</option>)}</select></label>
      <label className="block">Proposal / decision reason<input aria-label="GEC decision reason" className="block w-full min-w-0 rounded border p-2" maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      <button type="button" className="ccs-btn-secondary" disabled={busy||!review||!reason.trim()||(!!selected&&!history)} onClick={()=>void act("propose")}>Store current review as proposed revision</button>
      {!review&&<p>Assess and prepare the current D7/D8 metadata before storing a proposal. Refresh discards temporary preview receipts; stored history remains available.</p>}
    </>}
    {history&&<><p>Record version {history.record.version} · Status {history.record.status} · Current revision {history.record.current_revision_id||"None"}. Current evidence: NOT RECHECKED; historical confirmation is not a fresh trust assessment.</p>
      <label className="block">Revision<select aria-label="GEC ledger revision" className="block w-full min-w-0 rounded border p-2" value={revision} onChange={e=>chooseRevision(e.target.value)}><option value="">Choose revision</option>{history.revisions.map(r=><option key={r.id} value={r.id}>{r.state} · {r.id} · {r.reason}</option>)}</select></label>
      <ul className="space-y-2 break-all text-sm">{history.events.map(e=><li key={e.id}>Decision {e.sequence} · {e.action} · {e.created_at} · Actor {e.actor_id} · Policy {e.policy_reference} · Revision {e.revision_id} · Evidence digest {e.evidence_digest} · {e.reason}</li>)}</ul>
      <button type="button" className="ccs-btn-secondary" disabled={busy||!review||!revision||!reason.trim()} onClick={()=>void act("request")}>Validate revision and request confirmation authority</button>
      {eligible&&<button type="button" className="ccs-btn-primary" disabled={busy||!review||!reason.trim()} onClick={()=>void act("confirm")}>Perform server-authorized confirmation</button>}
      {history.record.status==="CONFIRMED"&&<button type="button" className="ccs-btn-secondary" disabled={busy||!reason.trim()} onClick={()=>void act("revoke")}>Request authorized revocation</button>}
    </>}
    {detail&&<div className="break-words text-sm"><h3 className="font-semibold">Selected proposal / historical revision</h3><p>Digest: <span className="break-all">{detail.content_digest}</span> · Evidence snapshot is historical, not current authority.</p><div className="max-w-full overflow-x-auto"><table className="w-full text-left"><thead><tr><th>Source row</th><th>Selected candidate</th><th>Current confirmed candidate</th></tr></thead><tbody>{detail.content.candidate.rows.map(row=>{const before=current?.content.candidate.rows.find(r=>r.source_row===row.source_row);return <tr key={row.source_row}><td>{row.source_row}</td><td>{row.original.subject_code} · {row.sections.map(r=>r.label||r.original).join(", ")} · {row.original.days.join(", ")} {row.original.start}–{row.original.end} · {row.original.room} · {row.original.instructor}</td><td>{before?before.original.subject_code+" · "+before.original.days.join(", ")+" "+before.original.start+"–"+before.original.end:"No matching current row"}</td></tr>;})}</tbody></table></div></div>}
    {busy&&<p role="status">Revalidating current source, authority and durable revision…</p>}{message&&<p role="status" className="break-words text-teal-900">{message}</p>}
  </section>;
}
