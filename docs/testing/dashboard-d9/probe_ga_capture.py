"""Instrument a disposable copy of the existing synthetic-HTTP GA browser test.

Only bounded rendering diagnostics are logged. No cookies, storage, requests or
rendered institutional text are printed. The real test and app are unchanged.
The experimental --background mode has an explicit visibility precondition and
is diagnostic only; merely opening/activating another target may not hide this
target in headless Edge. An unmet precondition is retained as a failed experiment.
"""
from pathlib import Path
import subprocess
import sys
from uuid import uuid4
import io
import tarfile
import shutil
import json

ROOT = Path(__file__).resolve().parents[3]
baseline = "--baseline" in sys.argv
foreground = "--foreground" in sys.argv
background = "--background" in sys.argv
owned_root = None
frontend = ROOT / "frontend"
if baseline:
    owned_root = frontend / ".cache" / ("d9-baseline-probe-" + uuid4().hex)
    owned_root.mkdir(parents=True, exist_ok=False)
    archive = subprocess.check_output(["git", "archive", "HEAD", "frontend"])
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        files.extractall(owned_root, filter="data")
    frontend = owned_root / "frontend"
    print("CAPTURE_PROBE_SOURCE pre-D9 D8 HEAD frontend", flush=True)
else:
    print("CAPTURE_PROBE_SOURCE current D9 working tree frontend", flush=True)
source = (frontend / "tests/gaMonitoring.browser.test.mjs").read_text(encoding="utf-8")
source = source.replace('await t.test(', 'await observedTest(')
source = source.replace('    let sequence = 0;', """
    async function observedTest(name,body) {
      return t.test(name,async()=>{
        const before=await evaluate('document.visibilityState');
        try { await body(); }
        finally {
          const after=await evaluate('document.visibilityState');
          if(before!==after)console.log('CAPTURE_PROBE_VISIBILITY_TRANSITION',JSON.stringify({test:name,before,after}));
        }
      });
    }
    let sequence = 0;
""")
if baseline:
    source = source.replace('"node_modules/vite/bin/vite.js"', json.dumps(str(ROOT / "frontend/node_modules/vite/bin/vite.js")))
needle = "const shot=await client.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});"
assert source.count(needle) == 1
probe = """
      BACKGROUND_PROBE
      console.log('CAPTURE_PROBE_BEFORE', JSON.stringify({
        targets:(await client.send('Target.getTargets')).targetInfos.map(t=>({type:t.type,path:new URL(t.url||'about:blank').pathname})),
        layout:await client.send('Page.getLayoutMetrics'),
        rendering:await evaluate(`({ready:document.readyState,visibility:document.visibilityState,
          fonts:document.fonts.status,width:innerWidth,height:innerHeight,x:scrollX,y:scrollY,
          documentWidth:document.documentElement.scrollWidth,documentHeight:document.documentElement.scrollHeight,
          animations:document.getAnimations().length,resources:performance.getEntriesByType('resource').length})`)
      }));
      let shot;
      FOREGROUND_PROBE
      const began=Date.now();
      try {
        shot=await client.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        console.log('CAPTURE_PROBE_SURFACE',JSON.stringify({result:'PASS',elapsed_ms:Date.now()-began}));
      } catch(error) {
        console.log('CAPTURE_PROBE_SURFACE',JSON.stringify({result:'TIMEOUT',elapsed_ms:Date.now()-began}));
        console.log('CAPTURE_PROBE_AFTER',JSON.stringify({layout:await client.send('Page.getLayoutMetrics'),
          responsive:await evaluate('document.readyState') }));
        const recovery=Date.now();
        await client.send('Page.bringToFront');
        await eventually(()=>evaluate('document.visibilityState===\"visible\"'),'Recovery target did not become visible');
        await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
        shot=await client.send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
        console.log('CAPTURE_PROBE_RECOVERY',JSON.stringify({result:'PASS',elapsed_ms:Date.now()-recovery,visibility:await evaluate('document.visibilityState')}));
      }
      if(probeBackgroundTarget)await client.send('Target.closeTarget',{targetId:probeBackgroundTarget});
"""
probe = probe.replace("BACKGROUND_PROBE", r"""
      const probeBackgroundTarget=(await client.send('Target.createTarget',{url:'about:blank',background:false})).targetId;
      const probeSocket=new WebSocket(socket.url.replace(/\/page\/[^/]+$/, '/page/'+probeBackgroundTarget));
      await new Promise((resolve,reject)=>{probeSocket.addEventListener('open',resolve,{once:true});probeSocket.addEventListener('error',reject,{once:true});});
      await cdp(probeSocket).send('Page.bringToFront');
      probeSocket.close();
      await eventually(()=>evaluate('document.visibilityState===\"hidden\"'),'Controlled tab did not hide capture target');
      console.log('CAPTURE_PROBE_CONTROLLED_BACKGROUND',JSON.stringify({visibility:await evaluate('document.visibilityState')}));
""" if background else "const probeBackgroundTarget=null;")
probe = probe.replace("FOREGROUND_PROBE", """
      await client.send('Page.bringToFront');
      await eventually(()=>evaluate('document.visibilityState===\"visible\"'),'Capture target did not become visible');
      await evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))');
      console.log('CAPTURE_PROBE_FOREGROUND',JSON.stringify({visibility:await evaluate('document.visibilityState')}));
""" if foreground else "")
target = frontend / "tests" / ("d9-capture-probe-" + uuid4().hex + ".mjs")
target.write_text(source.replace(needle, probe), encoding="utf-8")
try:
    result = subprocess.run(["node", "--test", str(target)], cwd=frontend)
    sys.exit(result.returncode)
finally:
    target.unlink()
    if owned_root:
        # Only this exact newly owned directory, never a computed parent.
        assert owned_root.resolve().parent == (ROOT / "frontend/.cache").resolve()
        assert owned_root.name.startswith("d9-baseline-probe-")
        shutil.rmtree(owned_root)
