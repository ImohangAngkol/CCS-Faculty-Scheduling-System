// Explicitly fictional fixtures, never academic records or active constraints.
export const row = {supplier:"Fictional College",subject_code:"SYN-GEC101",title:"Fictional Seminar",sections:["SYN-A"],
  academic_term:"",days:["M"],start:"09:00",end:"10:00",room:"SYN LEC",instructor:"Synthetic Lecturer 0",
  source_reference:"Fictional memo 1",notes:"Fictional example only",status:"tentative"};
export const metadata = {sections:[{id:"synthetic-section-a",label:"SYN-A"}],rooms:[{id:"SYN LEC",label:"SYN LEC"}],
  instructors:[{id:"synthetic-instructor-0",label:"Synthetic Lecturer 0"}],subjects:[{code:"SYN101",title:"Synthetic programming"}],
  terms:[],term_verification:"not_configured",fixed_section_entries:0,
  limits:{max_bytes:1048576,max_rows:200,max_columns:13,xlsx_sheets:1,max_decompressed_bytes:8388608}};
export const issue = (code, severity="review", field="academic_term", related_rows=[]) => ({code,severity,field,related_rows,message:"Synthetic discrepancy for UI verification."});
export function preview(rows=[row],kind="manual",issues=[issue("TERM_UNKNOWN")]) {
  const match=(value,id)=>({value,id,state:id?"resolved":value?"unresolved":"not_supplied"});
  return {schema_version:1,preview_only:true,persisted:false,activated:false,source_kind:kind,source_name:kind==="manual"?null:"fictional."+kind,
    source_sha256:kind==="manual"?null:"a".repeat(64),parser_version:"d3.1",term_verification:"not_configured",
    rows:rows.map((input,index)=>({source_row:index+(kind==="manual"?1:2),input,status:issues.some(i=>i.severity==="error")?"invalid":"needs_review",
      sections:input.sections.map(v=>match(v,v==="SYN-A"?"synthetic-section-a":null)),
      room:match(input.room,"SYN LEC"),instructor:match(input.instructor,"synthetic-instructor-0"),discrepancies:issues}))};
}
