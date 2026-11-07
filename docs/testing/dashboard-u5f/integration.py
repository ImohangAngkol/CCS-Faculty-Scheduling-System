"""Exact insertions for mixed working files and selective HEAD snapshots."""
def main(raw):
    assert b'continuous_optimization' not in raw
    sep=b'\r\n' if b'\r\n' in raw else b'\n'
    anchor=b'advanced_ga_analysis' if b'from routers import advanced_ga_analysis' in raw else b'ga_evaluation'
    for old,new in [(b'from routers import '+anchor,b'from routers import '+anchor+sep+b'from routers import continuous_optimization'),
        (b'app.include_router('+anchor+b'.router)',b'app.include_router('+anchor+b'.router)'+sep+b'app.include_router(continuous_optimization.router)')]:
        assert raw.count(old)==1;raw=raw.replace(old,new)
    return raw


def generate(raw):
    assert b'import OptimizationMode' not in raw
    sep=b'\r\n' if b'\r\n' in raw else b'\n'
    raw=b'import OptimizationMode from "../../components/ga/OptimizationMode";'+sep+b'import type {OptimizationMode as Mode} from "../../services/continuousOptimization";'+sep+raw
    for old,new in [(b'export default function GenerateSchedule() {',b'export default function GenerateSchedule() {'+sep+b'  const [optimizationMode,setOptimizationMode]=useState<Mode>("fixed");'),
        (b'  async function handleGenerate() {',b'  async function handleGenerate() {'+sep+b'    if(optimizationMode!=="fixed")return; // No continuous execution API exists.'),
        (b'      <ConstrainedRunPanel />',b'      <OptimizationMode mode={optimizationMode} onChange={setOptimizationMode} population={populationSize} fresh={freshChromosomes} runId={activeRunId}/>'+sep+b'      <div hidden={optimizationMode!=="fixed"}><ConstrainedRunPanel /></div>')]:
        assert raw.count(old)==1;raw=raw.replace(old,new,1)
    start=raw.index(b'      {/* SETTINGS CARD */}');start=raw.index(b'      <div',start)
    raw=raw[:start]+b'      <fieldset hidden={optimizationMode!=="fixed"} disabled={optimizationMode!=="fixed"} className="min-w-0">'+sep+raw[start:]
    pos=raw.index(b'<LiveGAMonitor');comment=raw.rfind(b'      {/* ==================================================== */}',0,pos)
    raw=raw[:comment]+b'      </fieldset>'+sep+sep+raw[comment:]
    old=b'onStop={stopGA}';assert raw.count(old)==1
    return raw.replace(old,b'onStop={async()=>{if(canStop&&window.confirm("Stop this fixed-generation run? The backend must confirm stopping; only its validated boundary can be preserved."))await stopGA();}}',1)
