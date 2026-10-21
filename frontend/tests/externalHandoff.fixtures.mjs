// Fictional HTTP projection only; no real backend receipt or validation claim.
import {handoffIdentity,HANDOFF_LABEL} from '../src/api/externalSchedules.ts';
import {makeProjection,makeSource} from './externalReview.fixtures.mjs';
export async function makeHandoff(source=makeSource(),mappings=[]) {
  const review=structuredClone(makeProjection(source,mappings));
  return {schema_version:3,handoff_version:'d5.1',label:HANDOFF_LABEL,preview_only:true,persisted:false,activated:false,approved:false,
    preview_id:await handoffIdentity(review),revalidated_at:'2026-10-21T12:00:00Z',review};
}
