import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {validateSourceQualification} from '../src/services/sourceQualification.ts';
import {qualificationFixture} from './sourceQualification.fixtures.mjs';

test('matching cached tables remain BLOCKED without source authority and run consumption evidence',()=>{
  const value=validateSourceQualification(qualificationFixture());
  assert.equal(value.eligible_for_current,false);assert.equal(value.institutional_approval,'NOT_ESTABLISHED');
});
for(const state of ['STALE_OR_DIFFERENT_CACHE','UNVERIFIABLE','CACHE_NOT_LOADED','CHANGED_DURING_INSPECTION'])test(`cache ${state} cannot promote eligibility`,()=>{
  const data=qualificationFixture();data.cached_tables[0].status=state;
  assert.equal(validateSourceQualification(data).qualification,'BLOCKED');
});
for(const [field,value] of [['eligible_for_current',true],['qualification','CURRENT'],['institutional_approval','APPROVED'],['source_metadata',{dataset_id:'Fictional claim'}],['input_fingerprint','invalid'],['reasons',[]]])test(`invalid ${field} fails closed`,()=>{
  assert.throws(()=>validateSourceQualification({...qualificationFixture(),[field]:value}));
});
test('unknown sources, duplicate rows and unsafe reason codes are rejected',()=>{
  for(const change of [value=>value.cached_tables.push(value.cached_tables[0]),value=>value.cached_tables[0].source='private/path.csv',value=>value.reasons.push('<script>untrusted</script>')]){
    const value=qualificationFixture();change(value);assert.throws(()=>validateSourceQualification(value));
  }
});
test('the UI has observation retry but no authority or dataset editing controls',async()=>{
  const source=await readFile(new URL('../src/components/ga/SourceQualification.tsx',import.meta.url),'utf8');
  for(const text of ['Retry source inspection','BLOCKED','does not prove complete optimizer inputs','institutional approval is not established','No values are inferred'])assert.ok(source.includes(text));
  assert.doesNotMatch(source,/<input|<select|dangerouslySetInnerHTML|method:.*POST/);
});
