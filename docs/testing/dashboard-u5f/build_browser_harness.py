"""Derive a new test-only harness without modifying unfinished Live Center work."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'frontend/tests/liveOptimization.browser.test.mjs').read_text(encoding='utf-8')
s="import {readinessFixture} from './continuousOptimization.fixtures.mjs';\nimport {runContinuousScenarios} from './continuousOptimization.scenarios.mjs';\n"+s
s=s.replace("'./liveOptimization.fixtures.mjs'","'./continuousOptimizationRun.fixtures.mjs'")
s=s.replace('ga-live-center-','u5f-browser-').replace('LIVE_CENTER_EVIDENCE_DIR','U5F_EVIDENCE_DIR')
s=s.replace('Live Optimization Center with fictional intercepted lifecycle responses','U5F readiness and existing fixed lifecycle with fictional HTTP')
s=s.replace('{accept:true}','{accept:!mode.cancelConfirm}')
s=s.replace("const selector = /console|research/.test(name) ? '[data-testid=\"live-ga-monitor\"] [role=\"tabpanel\"]:not([hidden])' : '[data-testid=\"live-ga-monitor\"]';", "const selector = name.includes('fixed') ? '[data-testid=\"live-ga-monitor\"]' : '[aria-label=\"Optimization mode\"]';")
needle="      else if(path==='/api/ga/latest')"
assert s.count(needle)==1
s=s.replace(needle,"""      else if(path==='/api/ga/continuous/readiness'){
        if(mode.readinessHold)await eventually(()=>!mode.readinessHold,'Fictional readiness release');
        status=mode.readinessError?503:200;body=mode.readinessError?{detail:'Fictional readiness unavailable'}:readinessFixture();
        if(mode.forgedReadiness)body.executable=true;
      }
"""+needle,1)
a=s.index("    await check('LC-B01");b=s.index('  }finally{',a)
s=s[:a]+"    await runContinuousScenarios({check,go,text,click,capture,command,evaluate,eventually,resize,requests,mode:()=>mode,runId,confirmations:()=>confirmations});\n    assert.deepEqual(errors,[]);\n"+s[b:]
with (ROOT/'frontend/tests/continuousOptimization.browser.test.mjs').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
