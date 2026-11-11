"""Test an owned committed snapshot; --working-ui adds hashed entry UI bytes.

Neither mode modifies the actual frontend, installs dependencies or stages Git.
"""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
HEAD='e5108dab557c7b274240400e389c144512cbdd54'

def main():
    git=['git','-c','safe.directory='+str(ROOT)]
    assert subprocess.check_output([*git,'rev-parse','HEAD'],cwd=ROOT).decode().strip()==HEAD
    index=hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()
    commands=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5j/run_checks.py'))['COMMANDS']
    selections=[s for s in sys.argv[1:] if s not in {'--working-ui','--checkpoint-ui'}] or ['contracts-all','build','bundle','lint','browser']
    assert all(s in {'contracts-all','frontend','build','bundle','lint','browser','preview-browser','legacy-browser'} for s in selections)
    owned=Path(tempfile.mkdtemp(prefix='u5o-frontend-')).resolve();snapshot=owned/'repository';snapshot.mkdir()
    with (owned/'frontend.tar').open('xb') as f:
        subprocess.run([*git,'-c','core.autocrlf=false','archive',HEAD,'--','frontend'],cwd=ROOT,stdout=f,check=True)
    with tarfile.open(owned/'frontend.tar') as source:
        for m in source.getmembers():assert (snapshot/m.name).resolve().is_relative_to(snapshot) and not m.issym() and not m.islnk()
        source.extractall(snapshot,filter='data')
    ui_hashes={}
    for name in ['frontend/src/researchOperator/console.html', 'frontend/src/researchOperator/console.mjs', 'frontend/tests/researchOperator.test.mjs','frontend/tests/researchOperator.live.mjs','frontend/tests/researchOperator.driver.mjs']:
        raw=(ROOT/name).read_bytes();destination=snapshot/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw);ui_hashes[name]=hashlib.sha256(raw).hexdigest()
    # Existing frontend contracts import this committed fictional DTO fixture.
    fixture='docs/testing/dashboard-u5e/fictional-api.json'
    destination=snapshot/fixture;destination.parent.mkdir(parents=True)
    destination.write_bytes(subprocess.check_output([*git,'show',HEAD+':'+fixture],cwd=ROOT))
    subprocess.run(['cmd','/d','/c','mklink','/J',str(snapshot/'frontend/node_modules'),str(ROOT/'frontend/node_modules')],capture_output=True,check=True)
    allowed={'SYSTEMROOT','WINDIR','PATH','PATHEXT','TEMP','TMP','COMSPEC','LOCALAPPDATA','APPDATA','USERPROFILE','PROGRAMFILES','PROGRAMFILES(X86)'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed};env.update(VITE_API_URL='http://localhost:57999')
    cache=runpy.run_path(str(ROOT/'docs/testing/dashboard-u5pa/isolate_vite_cache.py'))['prepare'](snapshot,owned)
    failed=False
    for selection in selections:
        target=BASE/(datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z')+'-'+selection);target.mkdir(exist_ok=False)
        child_env=dict(env)
        if selection in {'preview-browser','legacy-browser'}:child_env['U5PE_EVIDENCE']=str(target);child_env['U5PC_EVIDENCE']=str(target)
        if selection=='browser':child_env['U5F_EVIDENCE_DIR']=str(target)
        command=commands.get(selection)
        if selection=='preview-browser':command=['node','--test','tests/observationContinuity.browser.test.mjs']
        if selection=='legacy-browser':command=['node','--test','tests/researchConsole.browser.test.mjs']
        if selection=='contracts-all':command=['node','--test','--test-concurrency=1',*[str(p.relative_to(snapshot/'frontend')) for p in sorted((snapshot/'frontend/tests').glob('*.test.mjs')) if '.browser.' not in p.name and '.live.' not in p.name]]
        if selection=='lint' and ui_hashes:
            names=[n.removeprefix('frontend/') for n in ui_hashes if n.endswith(('.ts','.tsx','.mjs'))]
            config=snapshot/'frontend/operator-eslint.config.mjs'
            config.write_text("import js from '@eslint/js';import globals from 'globals';export default [js.configs.recommended,{files:['src/researchOperator/console.mjs'],languageOptions:{globals:globals.browser}},{files:['tests/*.mjs'],languageOptions:{globals:globals.node}}];\n",encoding='utf-8')
            command=['node','node_modules/eslint/bin/eslint.js','--config','operator-eslint.config.mjs',*names]
        start=datetime.now().astimezone().isoformat();tick=time.perf_counter()
        try:
            result=subprocess.run(command,cwd=snapshot/'frontend',env=child_env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=300)
            code=result.returncode;out=result.stdout;err=result.stderr
        except subprocess.TimeoutExpired as error:
            decode=lambda v:v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
            code=124;out=decode(error.stdout);err=decode(error.stderr)+'\nTimeout; owned process cleanup requires review.'
        row=dict(selection=selection,head=HEAD,ui_mode='working-tree' if '--working-ui' in sys.argv else 'committed-u5pd-plus-only-u5pe',ui_overlay_sha256=ui_hashes,command=command,started_at=start,ended_at=datetime.now().astimezone().isoformat(),
            elapsed_seconds=time.perf_counter()-tick,exit_code=code,stdout=out,stderr=err,
            test_cache_isolation=cache,scope='Committed frontend source in owned temporary snapshot; dependencies reused without installation. Browser uses actual Edge/React with intercepted fictional HTTP, not live FastAPI or U5PB worker acceptance. Working-tree UI overlays are qualified only when ui_mode says working-tree; no source file is modified.')
        (target/'command.json').write_text(json.dumps(row,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(selection=selection,exit_code=code,evidence=target.relative_to(ROOT).as_posix())),flush=True)
        if code:failed=True;print(json.dumps(dict(failure_preserved=True,selection=selection)),flush=True)
    assert subprocess.check_output([*git,'rev-parse','HEAD'],cwd=ROOT).decode().strip()==HEAD
    assert hashlib.sha256((ROOT/'.git/index').read_bytes()).hexdigest()==index
    return 1 if failed else 0
if __name__=='__main__':raise SystemExit(main())
