import {readFileSync} from 'node:fs';
const fixture=JSON.parse(readFileSync(new URL('../../docs/testing/dashboard-u5e/fictional-api.json',import.meta.url),'utf8'));
export const run=fixture.run_id;
export const analysisFixture=(mode='current')=>structuredClone(fixture[mode]);
