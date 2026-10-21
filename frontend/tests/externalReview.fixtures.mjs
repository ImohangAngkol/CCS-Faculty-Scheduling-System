// Fictional HTTP fixtures only; receipt is not a production HMAC.
import {row, metadata as intakeMetadata, preview, issue} from "./externalSchedules.fixtures.mjs";
export const metadata = {...intakeMetadata,
  sections:[{id:"section-a",label:"SYN-A"},{id:"section-b",label:"SYN-B"}],
  rooms:[{id:"room-a",label:"Fictional Room A"},{id:"room-b",label:"Fictional Room B"}],
  instructors:[{id:"faculty-a",label:"Fictional Shared Name"},{id:"faculty-b",label:"Fictional Shared Name"}]};
export const inputs = [
  {...row,sections:["Imported section"],room:"room-a",instructor:"Fictional Shared Name"},
  {...row,subject_code:"SYN-GEC202",title:"Fictional second meeting",sections:["SYN-A"],start:"09:30",end:"10:30",room:"room-a",instructor:"faculty-a",status:"draft"},
  {...row,supplier:"Another Fictional College",subject_code:"SYN-GEC303",sections:["SYN-B"],days:["T"],start:"10:00",end:"11:00",room:"",instructor:""},
  {...row,subject_code:"SYN-INVALID",sections:["Imported section"],start:"invalid",room:"",instructor:""},
];
export function makeSource(rows=inputs) {return {...preview(rows,"csv"),review_token:"public-d4-fictional-receipt"};}
export function makeProjection(source=makeSource(),mappings=[],mode={}) {
  const match=(value,field,selected)=>{
    const choices=mode.unsupported&&field==="room"?[]:metadata[field==="sections"?"sections":field==="room"?"rooms":"instructors"];
    const item=choices.find(c=>c.id===selected||c.id===value||field==="sections"&&c.label===value);
    const state=selected||item?"resolved":!value&&field!=="sections"?"missing_optional":mode.unsupported&&field==="room"?"unsupported":field==="instructor"&&value==="Fictional Shared Name"?"ambiguous":"unresolved";
    const resolved=state==="resolved"?(choices.find(c=>c.id===selected)??item):null;
    return {original:value,id:resolved?.id??null,label:resolved?.label??null,state,method:state==="resolved"?(selected?"explicit":"recognized"):"none",candidate_ids:state==="ambiguous"?["faculty-a","faculty-b"]:[]};
  };
  const rows=source.rows.map(sourceRow=>{
    const m=mappings.find(m=>m.source_row===sourceRow.source_row),original=sourceRow.input;
    const sections=original.sections.map((v,i)=>match(v,"sections",m?.sections?.find(s=>s.reference_index===i)?.target_id));
    const room=match(original.room,"room",m?.room_id),instructor=match(original.instructor,"instructor",m?.instructor_id);
    return {source_row:sourceRow.source_row,original,status:"needs_review",sections,room,instructor,
      discrepancies:[issue("TERM_UNKNOWN")],calendar_supported:original.start!=="invalid"};
  });
  if(rows.length>1)for(const r of rows.slice(0,2)){
    const other=rows[r===rows[0]?1:0];
    if(r.room.id&&r.room.id===other.room.id)r.discrepancies.push(issue("ROOM_OVERLAP","error","room",[other.source_row]));
    if(r.sections[0]?.id&&r.sections[0]?.id===other.sections[0]?.id)r.discrepancies.push(issue("SECTION_OVERLAP","error","sections",[other.source_row]));
    if(r.instructor.id&&r.instructor.id===other.instructor.id)r.discrepancies.push(issue("INSTRUCTOR_OVERLAP","error","instructor",[other.source_row]));
  }
  for(const r of rows){
    if(!r.calendar_supported)r.discrepancies.push(issue("INVALID_TIME","error","start/end"));
    r.status=r.discrepancies.some(d=>d.severity==="error")?"invalid":"needs_review";
  }
  return {schema_version:2,preview_only:true,persisted:false,activated:false,
    source_kind:source.source_kind,source_name:source.source_name,source_sha256:source.source_sha256,
    source_parser_version:"d3.1",projection_version:"d4.1",term_verification:"not_configured",reference_digest:"b".repeat(64),rows};
}
