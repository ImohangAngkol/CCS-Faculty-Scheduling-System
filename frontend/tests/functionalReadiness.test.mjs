import {test} from "node:test";
import assert from "node:assert/strict";
import {apiClient} from "../src/services/apiSession.ts";
import {publishedVersions} from "../src/api/scheduleApplications.ts";

test("independent history loading forwards cancellation without authority claims",async()=>{
 const previous=apiClient.get,controller=new AbortController();
 try{apiClient.get=async(url,options)=>{assert.equal(url,"/api/schedule-applications/versions");assert.equal(options.signal,controller.signal);assert.deepEqual(options.params,{version_id:undefined});return {data:{versions:[],current_version_id:null,source_revision:"fictional-source",read_only:true}};};
 assert.deepEqual((await publishedVersions(undefined,controller.signal)).versions,[]);
 }finally{apiClient.get=previous;}
});
test("a cancelled or denied history read cannot become an empty successful history",async()=>{
 const previous=apiClient.get;
 try{for(const code of ["ERR_CANCELED","403","503"]){const failure=Object.assign(new Error("Fictional unavailable history"),{code});apiClient.get=async()=>{throw failure;};await assert.rejects(publishedVersions(undefined,new AbortController().signal),e=>e===failure);}}
 finally{apiClient.get=previous;}
});
