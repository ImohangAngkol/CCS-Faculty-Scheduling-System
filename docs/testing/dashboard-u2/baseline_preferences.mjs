// Diagnostic comparison only: serve the pre-U2 UI through Vite load hooks.
// Never rewrite production sources or use a real backend/database.
import {execFileSync,spawn} from 'node:child_process';
import {mkdtemp,mkdir,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {resolve,join,sep} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const directory=await mkdtemp(join(tmpdir(),'u2-ui-baseline-'));
try{
  const names=['frontend/src/components/common/Sidebar.tsx','frontend/src/layouts/AdminLayout.tsx','frontend/src/layouts/FacultyLayout.tsx','frontend/src/components/faculty/FacultyPreferenceEditor.tsx','frontend/src/components/faculty/preferences.css'];
  const sources=Object.fromEntries(names.map(name=>[resolve(root,name).replaceAll('\\','/'),execFileSync('git',['show',`f5262637acfb2d4d063cad1b0de80779a10bcba3:${name}`],{cwd:root,encoding:'utf8'})]));
  // Retain the application's React/Tailwind plugins and scan the frozen UI's
  // original utility classes too; a bare Vite config is not a valid baseline.
  const frozen=join(directory,'frozen-ui');await mkdir(frozen);
  for(const [name,content]of Object.entries(sources))await writeFile(join(frozen,name.split('/').at(-1)),content,{flag:'wx'});
  sources[resolve(root,'frontend/src/index.css').replaceAll('\\','/')]=(await readFile(join(root,'frontend/src/index.css'),'utf8'))+`\n@source ${JSON.stringify(frozen.replaceAll('\\','/'))};\n`;
  const config=join(directory,'vite.config.mjs');
  await writeFile(config,`import base from ${JSON.stringify(resolve(root,'frontend/vite.config.ts').replaceAll('\\','/'))};const sources=${JSON.stringify(sources)};export default {...base,plugins:[...(base.plugins??[]),{name:'u2-frozen-ui-baseline',enforce:'pre',load(id){return sources[id.split('?')[0].replaceAll('\\\\','/')]??null;}}]};\n`,{flag:'wx'});
  let test=await readFile(join(root,'frontend/tests/preferences.browser.test.mjs'),'utf8');
  test=test.replace('from "./preferenceFixtures.mjs"',`from ${JSON.stringify(pathToFileURL(join(root,'frontend/tests/preferenceFixtures.mjs')).href)}`);
  test=test.replace('const frontend = new URL("../", import.meta.url);',`const frontend = new URL(${JSON.stringify(pathToFileURL(join(root,'frontend')+sep).href)});`);
  test=test.replace('"node_modules/vite/bin/vite.js", "--host"',`"node_modules/vite/bin/vite.js", "--config", ${JSON.stringify(config)}, "--host"`);
  test=test.replaceAll("document.querySelector('main').scrollTop",'window.scrollY');
  test=test.replace("var rect=document.querySelector('main').getBoundingClientRect(); ({top:rect.top,bottom:rect.bottom})",'({top:0,bottom:innerHeight})');
  const target=join(directory,'baseline.test.mjs');await writeFile(target,test,{flag:'wx'});
  const child=spawn(process.execPath,['--test',target],{cwd:join(root,'frontend'),env:process.env,windowsHide:true,stdio:'inherit'});
  process.exitCode=await new Promise((resolve,reject)=>{child.once('error',reject);child.once('exit',code=>resolve(code??1));});
}finally{
  const target=resolve(directory);if(!target.startsWith(resolve(tmpdir())+sep)||!target.split(sep).at(-1).startsWith('u2-ui-baseline-'))throw new Error('Unexpected owned temporary path');
  await rm(target,{recursive:true,force:true,maxRetries:5,retryDelay:100});
}
