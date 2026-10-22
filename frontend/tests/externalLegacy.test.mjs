import {test} from 'node:test';
import assert from 'node:assert/strict';
import {previewFile,reviewExternal,prepareExternalHandoff,handoffIdentity} from '../src/api/externalSchedules.ts';
import {apiClient} from '../src/services/apiSession.ts';
import {makeSource,makeProjection} from './externalReview.fixtures.mjs';
import {makeHandoff} from './externalHandoff.fixtures.mjs';
const metadata={supplier:'Fictional College',source_reference:'Fictional letter',academic_term:'Unverified term',status:'draft'};
const legacy={adapter_version:'d6.1',metadata_origin:'administrator_supplied_unverified',metadata,rows:[{source_row:2,year_level:'1',section:'Imported section',course_number:'SYN-GEC101',schedule:'7:30AM - 9:00AM MTH',parse_state:'parsed',discrepancies:[]}]};
async function post(fn,action){const old=apiClient.post;apiClient.post=fn;try{await action();}finally{apiClient.post=old;}}
test('legacy is explicit and metadata stays in bounded JSON body, not URL params',async()=>{
 const raw='Year Level,Section,Course Number,Schedule\n1,SYN-A,EXAMPLE,7:30AM - 9:00AM MTH\n';
 await post(async(url,body,options)=>{assert.ok(url.endsWith('/preview-file'));assert.equal(options.params.import_format,'legacy_gec');assert.deepEqual(Object.keys(options.params).sort(),['filename','import_format']);assert.deepEqual(body.metadata,metadata);assert.equal(atob(body.content_base64),raw);assert.equal(options.headers['Content-Type'],'application/json');return {data:{...makeSource(),legacy}};},async()=>assert.deepEqual((await previewFile(new File([raw],'fictional.csv'),undefined,metadata)).legacy,legacy));
});
test('canonical uploads retain raw-byte transport and default format',async()=>{
 const file=new File(['canonical'],'fictional.csv');await post(async(url,body,options)=>{assert.equal(body,file);assert.deepEqual(options.params,{filename:file.name});return {data:makeSource()};},async()=>previewFile(file));
});
test('legacy rejects XLSX and excessive bytes before any request',async()=>{
 await post(()=>assert.fail('No request'),async()=>{await assert.rejects(previewFile(new File(['x'],'fictional.xlsx'),undefined,metadata),/Legacy/);await assert.rejects(previewFile(new File(['x'.repeat(1048577)],'fictional.csv'),undefined,metadata),/1 MiB/);});
});
test('review and handoff retain legacy provenance and all mappings',async()=>{
 const source={...makeSource(),legacy};const mappings=[{source_row:2,sections:[{reference_index:0,target_id:'section-a'}]}];
 await post(async(url,body)=>{assert.equal(body.review_token,source.review_token);assert.deepEqual(body.mappings,mappings);const review={...makeProjection(source,mappings),legacy};if(url.endsWith('/review'))return {data:review};const value=await makeHandoff(source,mappings);value.review=review;value.preview_id=await handoffIdentity(review);return {data:value};},async()=>{assert.deepEqual((await reviewExternal(source,mappings)).legacy,legacy);assert.deepEqual((await prepareExternalHandoff(source,mappings)).review.legacy,legacy);});
});
test('changed or omitted legacy originals fail provenance even with a new handoff hash',async()=>{
 const source={...makeSource(),legacy};for(const altered of [null,{...legacy,rows:[{...legacy.rows[0],schedule:'altered'}]}]){
 await post(async()=>{const value=await makeHandoff(source);value.review.legacy=altered;value.preview_id=await handoffIdentity(value.review);return {data:value};},async()=>assert.rejects(prepareExternalHandoff(source,[]),/provenance/));}
});
test('unsupported legacy state or administrator confirmation metadata cannot pass the DTO',async()=>{
 for(const changed of [{...legacy,metadata_origin:'institutionally_approved'},{...legacy,rows:[{...legacy.rows[0],parse_state:'confirmed'}]}])await post(async()=>({data:{...makeSource(),legacy:changed}}),async()=>assert.rejects(previewFile(new File(['x'],'fictional.csv'),undefined,metadata)));
});
