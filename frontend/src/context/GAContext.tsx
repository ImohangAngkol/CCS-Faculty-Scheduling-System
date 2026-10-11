import { GAStreamError, GA_RUN_STATES } from "../services/gaMonitoring";
import type { GAExecutionStatus, GenerationMetrics, GAMonitoringEvent } from "../services/gaMonitoring";
import {
  createContext,
  useContext,
  useEffect,
  useCallback,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  getLatestGAResult,
  runGeneticAlgorithmStream,
  stopGARun,
  getGABackendStatus,
  getGARunState,
  getGARunResult,
  controlGARun,
  getGACheckpointStatus,
  getGARunLogs,
} from "../services/gaService";
import { emptyLogHistory, mergeRunLogs, logPollDelay, needsLogReplay } from "../services/gaLogs";
import { GAControlError, readRunReference, RUN_REFERENCE_KEY } from "../services/gaRecovery";
import type { RunReference, RunSnapshot } from "../services/gaRecovery";

import type {
  BaselineMode,
  GARunData,
} from "../types/ga";


type GAContextType = {
  pauseGA: () => Promise<void>;
  resumeGA: () => Promise<void>;
  canPause: boolean;
  canResume: boolean;
  controlError: string | null;
  pausedRuns: RunSnapshot[];
  selectPausedRun: (run: RunSnapshot) => void;
  activeRunId: string | null;
  recoveryNotice: string | null;
  stopGA: () => Promise<void>;
  canStop: boolean;
  stopError: string | null;
  executionStatus: GAExecutionStatus;
  progressHistory: GenerationMetrics[];

  gaData:
    GARunData | null;


  loading:
    boolean;


  error:
    string | null;


  elapsedSeconds:
    number;


  logs:
    string[];
  logNotice: string | null;
  logConnection: string;


  populationSize:
    number;


  generations:
    number;


  freshChromosomes:
    number;


  runGA: (
    populationSize?: number,
    generations?: number,
    freshChromosomes?: number,
    baselineMode?: BaselineMode
  ) => Promise<void>;


  loadChromosomeData: (
    data: GARunData
  ) => void;


  clearGAData:
    () => void;
};


const GAContext =
  createContext<
    GAContextType | undefined
  >(undefined);


type GAProviderProps = {
  children:
    ReactNode;
};


export function GAProvider({
  children,
}: GAProviderProps) {

  const [
    gaData,
    setGaData,
  ] =
    useState<GARunData | null>(
      null
    );


  const [
    loading,
    setLoading,
  ] =
    useState(true);


  const [
    error,
    setError,
  ] =
    useState<string | null>(
      null
    );


  const [
    elapsedSeconds,
    setElapsedSeconds,
  ] =
    useState(0);


  const [
    logs,
    setLogs,
  ] =
    useState<string[]>([]);


  const [
    populationSize,
    setPopulationSize,
  ] =
    useState(10);


  const [
    generations,
    setGenerations,
  ] =
    useState(2);


  const [
    freshChromosomes,
    setFreshChromosomes,
  ] =
    useState(2);


  const [executionStatus, setExecutionStatus] = useState<GAExecutionStatus>("RECOVERING");
  const [progressHistory, setProgressHistory] = useState<GenerationMetrics[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const activeRunRef = useRef<string | null>(null);
  const processRef = useRef<string | null>(null);
  const [recovery, setRecovery] = useState<RunReference | null>(null);
  const [logReference, setLogReference] = useState<RunReference | null>(null);
  const logHistory = useRef(emptyLogHistory());
  const logIdentity = useRef("");
  const [logNotice, setLogNotice] = useState<string | null>(null);
  const [logConnection, setLogConnection] = useState("Connecting to run logs…");
  const [recoveryNotice, setRecoveryNotice] = useState<string | null>(null);
  const [serverAcceptingStop, setServerAcceptingStop] = useState(true);
  const [serverAcceptingPause, setServerAcceptingPause] = useState(false);
  const [serverAcceptingResume, setServerAcceptingResume] = useState(false);
  const [controlError, setControlError] = useState<string | null>(null);
  const [pausedRuns, setPausedRuns] = useState<RunSnapshot[]>([]);
  const actionPending = useRef(false);
  const [actionSubmitting, setActionSubmitting] = useState(false);
  const controlRevision = useRef(0);
  const [stopError, setStopError] = useState<string | null>(null);
  const [stopSubmitting, setStopSubmitting] = useState(false);
  const statusRef = useRef<GAExecutionStatus>("RECOVERING");
  const stopPending = useRef(false);
  const status = useCallback((value: GAExecutionStatus) => { statusRef.current = value; setExecutionStatus(value); }, []);
  const monitorLogs = useCallback((runId: string, processId: string) => {
    const identity = `${runId}/${processId}`;
    if (identity !== logIdentity.current) {
      logIdentity.current = identity;
      logHistory.current = emptyLogHistory();
      setLogs([]); setLogNotice(null);
    }
    setLogReference(current => current?.run_id === runId && current.process_instance_id === processId
      ? current : {run_id: runId, process_instance_id: processId});
  }, []);

  function rememberRun(runId: string, processInstanceId: string) {
    try { sessionStorage.setItem(RUN_REFERENCE_KEY, JSON.stringify({ run_id: runId, process_instance_id: processInstanceId })); } catch { /* Discovery still works without browser storage. */ }
  }
  const applySnapshot = useCallback((snapshot: RunSnapshot) => {
    if (activeRunRef.current !== snapshot.run_id || processRef.current !== snapshot.process_instance_id) {
      controlRevision.current++;
      stopPending.current = false;
      actionPending.current = false;
      setActionSubmitting(false);
      setStopSubmitting(false);
      setStopError(null);
      setControlError(null);
      setProgressHistory([]);
    }
    activeRunRef.current = snapshot.run_id;
    processRef.current = snapshot.process_instance_id;
    monitorLogs(snapshot.run_id, snapshot.process_instance_id);
    setActiveRunId(snapshot.run_id);
    setServerAcceptingStop(snapshot.accepting_stop);
    setServerAcceptingPause(snapshot.accepting_pause ?? false);
    // An idle PAUSED lifecycle record proves the commit, not current compatibility.
    setServerAcceptingResume(snapshot.state === "PAUSED" ? false : snapshot.accepting_resume ?? false);
    // Reads begun before a control action are discarded by controlRevision.
    // A current backend snapshot overrides every local control intention.
    status(snapshot.state);
    setElapsedSeconds(Math.floor(snapshot.elapsed_ms / 1000));
    if (snapshot.configuration.population_size !== undefined) setPopulationSize(snapshot.configuration.population_size);
    if (snapshot.configuration.generations !== undefined) setGenerations(snapshot.configuration.generations);
    if (snapshot.configuration.fresh_chromosomes !== undefined) setFreshChromosomes(snapshot.configuration.fresh_chromosomes);
    const persisted = snapshot.progress_history;
    if (persisted?.length) setProgressHistory(current => {
      const points = new Map([...current, ...persisted].map(point => [point.generation, point]));
      return [...points.values()].sort((a, b) => a.generation - b.generation);
    });
    const metric = snapshot.latest_progress;
    if (metric) setProgressHistory(current => current.some(item => item.generation === metric.generation) ? current : [...current, metric]);
  }, [status, monitorLogs]);

  function receiveEvent(event: GAMonitoringEvent) {
    if ((event.type === "run_created" || event.type === "run_started") && typeof event.data.process_instance_id === "string") {
      if (processRef.current && processRef.current !== event.data.process_instance_id) throw new GAStreamError("The stream came from a different backend process; run ownership could not be verified.");
      processRef.current = event.data.process_instance_id;
    }
    if (processRef.current) rememberRun(event.run_id, processRef.current);
    if (processRef.current) monitorLogs(event.run_id, processRef.current);
    if ((event.type === "run_created" || event.type === "run_started" || event.type === "run_state_changed") && typeof event.data.accepting_stop === "boolean") setServerAcceptingStop(event.data.accepting_stop);
    if (event.type === "run_created" || event.type === "run_started" || event.type === "run_state_changed") {
      if (typeof event.data.accepting_pause === "boolean") setServerAcceptingPause(event.data.accepting_pause);
      if (typeof event.data.accepting_resume === "boolean") setServerAcceptingResume(event.data.accepting_resume);
    }
    activeRunRef.current = event.run_id;
    setActiveRunId(event.run_id);
    if (event.type === "run_created" || event.type === "run_started") {
      if (!["PAUSE_REQUESTED", "PAUSING", "STOP_REQUESTED", "STOPPING", "STOPPED"].includes(statusRef.current)) {
        const received = event.data.status as typeof GA_RUN_STATES[number];
        status(GA_RUN_STATES.includes(received) ? received : "INITIALIZING");
      }
    }
    if (event.type === "run_state_changed") {
      status(event.data.status as GAExecutionStatus);
      if (["STOP_REQUESTED", "STOPPING", "STOPPED", "COMPLETED", "FAILED"].includes(String(event.data.status))) {
        setRecoveryNotice(null);
        setServerAcceptingResume(false);
      }
      if (typeof event.data.elapsed_ms === "number") setElapsedSeconds(Math.floor(event.data.elapsed_ms / 1000));
    }
    if (event.type === "done" && event.data.status === "STOPPED") status("STOPPED");
    if (event.type === "done" && event.data.status === "PAUSED") status("PAUSED");
    if (event.type === "initial_population_ready" || event.type === "generation_completed") {
      if (["CREATED", "INITIALIZING", "RUNNING"].includes(statusRef.current)) status("RUNNING");
      const metric = event.data;
      setProgressHistory(current => current.some(item => item.generation === metric.generation) ? current : [...current, metric]);
      setElapsedSeconds(Math.floor(metric.elapsed_ms / 1000));
    }
  }

  const runningRef =
    useRef(true);

  const canStop = !stopSubmitting && !!activeRunId && serverAcceptingStop && ["CREATED", "INITIALIZING", "RUNNING", "PAUSE_REQUESTED", "PAUSING", "PAUSED", "RESUMING"].includes(executionStatus);
  const canPause = !actionSubmitting && !stopSubmitting && loading && !!activeRunId && serverAcceptingPause && ["CREATED", "INITIALIZING", "RUNNING"].includes(executionStatus);
  const canResume = !actionSubmitting && !stopSubmitting && !loading && !!activeRunId && serverAcceptingResume && executionStatus === "PAUSED";
  function selectPausedRun(run: RunSnapshot) {
    if (runningRef.current || stopPending.current || actionPending.current) return;
    controlRevision.current++;
    setStopError(null);
    setProgressHistory([]);
    applySnapshot(run);
    rememberRun(run.run_id, run.process_instance_id);
    setControlError(null);
    setRecoveryNotice("Durable paused checkpoint recovered. Checking compatibility before enabling Resume Generation.");
    setRecovery({run_id:run.run_id,process_instance_id:run.process_instance_id});
  }
  async function pauseGA() {
    if (!canPause || !activeRunId || !processRef.current || actionPending.current) return;
    actionPending.current = true;
    setActionSubmitting(true); controlRevision.current++;
    const runId = activeRunId, processId = processRef.current, revision = controlRevision.current;
    setControlError(null);
    setRecoveryNotice("Sending pause request to the backend. Waiting for acknowledgement; the displayed lifecycle is the last confirmed server state.");
    try {
      const ack = await controlGARun(runId, processId, "pause");
      if (activeRunRef.current !== runId || processRef.current !== processId || revision !== controlRevision.current) return;
      if (!ack.accepted) {
        setControlError("Pause was not accepted; the run is already terminal.");
      }
      if (!["PAUSING", "PAUSED", "STOP_REQUESTED", "STOPPING", "STOPPED", "COMPLETED", "FAILED"].includes(statusRef.current)) status(ack.state);
      setRecoveryNotice(null);
    } catch (reason) {
      if (activeRunRef.current === runId && processRef.current === processId && revision === controlRevision.current) {
        setControlError(reason instanceof Error ? reason.message : "Pause could not be requested.");
        setRecoveryNotice("Pause acknowledgement failed. Checking the authoritative backend lifecycle.");
        setRecovery({run_id:runId,process_instance_id:processId});
      }
    } finally {
      if (activeRunRef.current === runId && processRef.current === processId) {
        actionPending.current = false; setActionSubmitting(false);
      }
    }
  }
  async function resumeGA() {
    if (!canResume || !activeRunId || !processRef.current || actionPending.current || stopPending.current) return;
    actionPending.current = true;
    setActionSubmitting(true); controlRevision.current++;
    const runId = activeRunId, processId = processRef.current, revision = controlRevision.current;
    setControlError(null);
    setRecoveryNotice("Resume request submitted. The backend must validate the checkpoint before admitting continuation.");
    setLoading(true); runningRef.current = true;
    try {
      const ack = await controlGARun(runId, processId, "resume");
      if (activeRunRef.current !== runId || processRef.current !== processId || revision !== controlRevision.current) return;
      applySnapshot(ack);
      if (ack.accepted) setPausedRuns(current => current.filter(run => run.run_id !== runId));
      setRecovery({run_id:runId,process_instance_id:processRef.current});
    } catch (reason) {
      if (activeRunRef.current !== runId || processRef.current !== processId || revision !== controlRevision.current) return;
      setServerAcceptingResume(false);
      setControlError(reason instanceof Error ? reason.message : "Resume failed; no fresh population was started.");
      setRecoveryNotice("Resume acknowledgement failed. Checking the authoritative backend lifecycle before enabling any further action.");
      setRecovery({run_id:runId,process_instance_id:processId});
    } finally {
      if (activeRunRef.current === runId && processRef.current === processId) {
        actionPending.current = false; setActionSubmitting(false);
      }
    }
  }
  async function stopGA() {
    if (!canStop || !activeRunId || stopPending.current) return;
    stopPending.current = true;
    controlRevision.current++;
    const requestedRunId = activeRunId, processId = processRef.current, revision = controlRevision.current;
    const previous = statusRef.current;
    setStopSubmitting(true);
    setServerAcceptingResume(false);
    setRecoveryNotice("Sending stop request to the backend. Waiting for acknowledgement; the displayed lifecycle is the last confirmed server state.");
    setStopError(null);
    try {
      const acknowledgement = await stopGARun(requestedRunId, processId ?? undefined);
      if (activeRunRef.current !== requestedRunId || processRef.current !== processId || revision !== controlRevision.current) return;
      // HTTP and SSE can arrive in either order. Never regress a terminal state.
      if (!["STOPPED", "COMPLETED", "FAILED"].includes(statusRef.current)
          && !(statusRef.current === "STOPPING" && acknowledgement.state === "STOP_REQUESTED")) {
        status(acknowledgement.state);
      }
      setRecoveryNotice(null);
      if (previous === "PAUSED" && acknowledgement.accepted && !["STOPPED", "COMPLETED", "FAILED"].includes(acknowledgement.state)) setLoading(true);
      if (!acknowledgement.accepted) setStopError(`Stop was not accepted; the backend reports ${acknowledgement.state.toLowerCase()}.`);
    } catch (reason) {
      if (activeRunRef.current !== requestedRunId || processRef.current !== processId || revision !== controlRevision.current) return;
      setStopError(reason instanceof Error ? reason.message : "Unable to request a stop.");
      setRecoveryNotice("Stop acknowledgement failed. The displayed lifecycle remains the last confirmed server state.");
      if (reason instanceof GAControlError && reason.code.startsWith("GA_CONTROL_ACK_") && processId) {
        setRecovery({run_id:requestedRunId,process_instance_id:processId});
      }
    } finally {
      if (activeRunRef.current === requestedRunId && processRef.current === processId && revision === controlRevision.current) {
        stopPending.current = false;
        setStopSubmitting(false);
        controlRevision.current++;
        // Restart selected-run verification after the POST settles. Never reuse
        // a checkpoint answer read before the stop attempt or another run.
        if ((previous === "PAUSED" || recovery) && processId) {
          setRecovery({run_id:requestedRunId,process_instance_id:processId});
        }
      }
    }
  }


  // =========================================================
  // DISCOVER THE CURRENT PROCESS; RECOVER MONITORING WITHOUT STARTING A GA.
  // =========================================================

  useEffect(() => {
    let cancelled = false;
    runningRef.current = true;
    // Saved results are independent of run discovery. A slow result must never
    // hide an active/paused run or delay its authoritative metrics.
    void getLatestGAResult().then(latest => {
      if (!cancelled && latest) setGaData(current => current ?? latest);
    }).catch(() => { /* Existing run recovery remains independent. */ });
    async function discover() {
      try {
        const backend = await getGABackendStatus();
        if (cancelled) return;
        processRef.current = backend.process_instance_id;
        setPausedRuns(backend.paused_runs ?? []);
        let remembered: RunReference | null = null;
        try { remembered = readRunReference(sessionStorage); } catch { /* Discovery works without browser storage. */ }
        if (backend.active_run) {
          const snapshot = backend.active_run;
          applySnapshot(snapshot);
          try { sessionStorage.setItem(RUN_REFERENCE_KEY, JSON.stringify({run_id:snapshot.run_id,process_instance_id:snapshot.process_instance_id})); } catch { /* Optional storage. */ }
          setRecoveryNotice(`${remembered && remembered.process_instance_id !== backend.process_instance_id ? "The previous backend changed; its old run was not restored. " : ""}Monitoring recovered from the current backend using read-only status polling. Earlier events may be missing.`);
          setRecovery({run_id:snapshot.run_id,process_instance_id:snapshot.process_instance_id});
          return;
        }
        if (remembered) {
          const paused = backend.paused_runs?.find(run => run.run_id === remembered.run_id);
          if (paused) {
            applySnapshot(paused);
            setControlError(null);
            rememberRun(paused.run_id, paused.process_instance_id);
            setRecoveryNotice("Durable paused checkpoint recovered. Checking compatibility before enabling Resume Generation.");
            setLoading(false);
            setRecovery({run_id:paused.run_id,process_instance_id:paused.process_instance_id});
            return;
          }
          if (remembered.process_instance_id !== backend.process_instance_id) {
            try {
              // Durable terminal records also survive a restart. Ask the new
              // process for this exact UUID before declaring ownership lost.
              const retained = await getGARunState(remembered.run_id, backend.process_instance_id);
              if (cancelled) return;
              applySnapshot(retained);
              rememberRun(retained.run_id, retained.process_instance_id);
              setRecovery({run_id:retained.run_id,process_instance_id:retained.process_instance_id});
              return;
            } catch (reason) {
              if (cancelled) return;
              if (!(reason instanceof GAControlError) || reason.code !== "GA_UNKNOWN_RUN") throw reason;
              activeRunRef.current = remembered.run_id;
              setActiveRunId(remembered.run_id);
              status("INTERRUPTED");
              setRecoveryNotice("The backend process changed. The previous run is interrupted or unknown; its population was not restored. Existing saved results remain available.");
            }
          } else {
            setRecovery(remembered);
            setRecoveryNotice("Checking the remembered run in the same backend process. Earlier events may be missing.");
            return;
          }
        } else if (backend.paused_runs?.length) {
          const paused = backend.paused_runs[0];
          applySnapshot(paused);
          setControlError(null);
          rememberRun(paused.run_id, paused.process_instance_id);
          setRecoveryNotice("A durable paused checkpoint was discovered. Checking compatibility before enabling Resume Generation.");
          setLoading(false);
          setRecovery({run_id:paused.run_id,process_instance_id:paused.process_instance_id});
          return;
        } else status("IDLE");
        runningRef.current = false;
        setLoading(false);
      } catch (reason) {
        if (cancelled) return;
        status(reason instanceof GAControlError && !reason.code.startsWith("GA_RECOVERY_") ? "REJECTED" : "DISCONNECTED");
        setError(reason instanceof Error ? reason.message : "Unable to discover the backend run. No cancellation occurred.");
        setRecoveryNotice(reason instanceof Error ? reason.message : "Unable to discover the backend run. Check port 8000 and refresh to retry.");
        runningRef.current = false;
        setLoading(false);
      }
    }
    void discover();
    return () => { cancelled = true; };
  }, [applySnapshot, status]);

  useEffect(() => {
    if (!recovery) return;
    let cancelled = false;
    let timer: number | undefined;
    async function poll() {
      const revision = controlRevision.current;
      try {
        const snapshot = await getGARunState(recovery!.run_id, recovery!.process_instance_id);
        if (cancelled) return;
        if (revision !== controlRevision.current) {
          timer = window.setTimeout(() => void poll(), 1000);
          return;
        }
        applySnapshot(snapshot);
        setError(null);
        if (snapshot.state !== "PAUSED") {
          setRecoveryNotice(snapshot.state === "RUNNING"
            ? "Monitoring recovered from the current backend using read-only status polling. Earlier events may be missing."
            : null);
          setServerAcceptingResume(false);
          setLoading(snapshot.execution_active);
        }
        if (snapshot.state === "PAUSED" && !snapshot.execution_active) {
          // Hydrate first; checkpoint validation can legitimately take longer.
          setLoading(false);
          setServerAcceptingResume(false);
          if (stopPending.current) {
            timer = window.setTimeout(() => void poll(), 1000);
            return;
          }
          setRecoveryNotice("Durable paused checkpoint recovered. Checking compatibility before enabling Resume Generation.");
          let checkpoint;
          try {
            checkpoint = await getGACheckpointStatus(snapshot.run_id, snapshot.process_instance_id);
          } catch (reason) {
            if (cancelled) return;
            if (revision !== controlRevision.current) {
              timer = window.setTimeout(() => void poll(), 1000);
              return;
            }
            if (reason instanceof GAControlError && ["GA_PROCESS_CHANGED", "GA_UNKNOWN_RUN"].includes(reason.code)) throw reason;
            setServerAcceptingResume(false);
            setControlError(reason instanceof Error ? reason.message : "Checkpoint verification failed. Refresh to retry; no worker was started.");
            setRecoveryNotice("Paused metrics and history recovered. Checkpoint verification failed; Resume Generation remains disabled. Refresh to retry.");
            setRecovery(null); runningRef.current = false;
            return;
          }
          if (cancelled) return;
          if (revision !== controlRevision.current) {
            timer = window.setTimeout(() => void poll(), 1000);
            return;
          }
          if (checkpoint.state !== "PAUSED") {
            status(checkpoint.state);
            setServerAcceptingResume(false);
            setRecoveryNotice(`Checkpoint verification observed ${checkpoint.state.toLowerCase()}. Refreshing the authoritative run status.`);
            timer = window.setTimeout(() => void poll(), 0);
            return;
          }
          setServerAcceptingResume(checkpoint.resumable);
          setControlError(current => checkpoint.error
            ? current?.includes(checkpoint.error) ? current : checkpoint.error
            : null);
          setPausedRuns(current => [...current.filter(run => run.run_id !== snapshot.run_id),
            {...snapshot, checkpoint_status: checkpoint}]);
          setRecovery(null); setLoading(false); runningRef.current = false;
          setRecoveryNotice(checkpoint.resumable
            ? "Durable paused checkpoint recovered and validated. The full generation history is preserved; resume continues from the next generation."
            : "Paused metrics and history recovered. The checkpoint cannot resume with the current backend/inputs; no worker was started.");
          return;
        }
        if (snapshot.state as string === "INTERRUPTED") {
          status("INTERRUPTED"); setRecovery(null); setLoading(false); runningRef.current = false;
          setServerAcceptingStop(false); setServerAcceptingResume(false);
          setRecoveryNotice("The worker was interrupted without a committed paused checkpoint. This run cannot resume.");
          return;
        }
        if (!snapshot.execution_active && ["STOPPED", "COMPLETED", "FAILED"].includes(snapshot.state)) {
          if (snapshot.state === "FAILED") setError(snapshot.terminal_error ?? "GA execution failed.");
          else if (snapshot.result_reference) {
            try {
              const result = await getGARunResult(snapshot.run_id);
              if (cancelled) return;
              setGaData({...result, result_source:"generated", optimization_performed:true});
            } catch (reason) {
              if (cancelled) return;
              setError(`The run is ${snapshot.state.toLowerCase()}, but its preserved result could not be loaded. ${reason instanceof Error ? reason.message : "Try retrieving the result again."}`);
            }
          }
          try { sessionStorage.removeItem(RUN_REFERENCE_KEY); } catch { /* Optional storage. */ }
          setRecovery(null);
          runningRef.current = false;
          setLoading(false);
          return;
        }
        timer = window.setTimeout(() => void poll(), 1000);
      } catch (reason) {
        if (cancelled) return;
        if (revision !== controlRevision.current) {
          timer = window.setTimeout(() => void poll(), 1000);
          return;
        }
        const lostOwner = reason instanceof GAControlError && ["GA_UNKNOWN_RUN", "GA_PROCESS_CHANGED"].includes(reason.code);
        status(lostOwner ? "INTERRUPTED" : "DISCONNECTED");
        setServerAcceptingStop(false);
        setError(reason instanceof Error ? reason.message : "Monitoring could not reconnect. No cancellation occurred.");
        setRecoveryNotice(lostOwner ? "The remembered run is no longer owned by this backend. Its population was not restored." : "Status monitoring disconnected. The server may still own this run; refresh to retry discovery.");
        setRecovery(null);
        runningRef.current = false;
        setLoading(false);
      }
    }
    runningRef.current = true;
    void poll();
    return () => { cancelled = true; if (timer !== undefined) window.clearTimeout(timer); };
  }, [recovery, applySnapshot, status]);

  // The cursor transport survives the original SSE closing at PAUSED.
  // It only reads diagnostics; reconnecting never starts or resumes a worker.
  useEffect(() => {
    if (!logReference) return;
    let cancelled = false;
    let timer: number | undefined;
    async function pollLogs() {
      const revision = controlRevision.current;
      try {
        const page = await getGARunLogs(logReference!.run_id, logReference!.process_instance_id, logHistory.current.cursor);
        if (cancelled) return;
        if (needsLogReplay(logHistory.current, page)) {
          // An evicted buffer may already have a cursor larger than our old
          // one. Fetch from zero in its new epoch rather than skipping lines.
          logHistory.current = {...emptyLogHistory(), truncated: true};
          setLogs([]);
          timer = window.setTimeout(() => void pollLogs(), 0);
          return;
        }
        logHistory.current = mergeRunLogs(logHistory.current, page);
        if (logHistory.current.entries.length || page.cursor_reset) {
          setLogs(logHistory.current.entries.map(entry => entry.message));
        }
        setLogNotice(logHistory.current.truncated
          ? "Earlier console logs are unavailable or were truncated. Available entries remain ordered; checkpoint metrics and history are separate."
          : page.entries.some(entry => entry.line_truncated) ? "An oversized diagnostic line was truncated." : null);
        setLogConnection(page.state === "PAUSED" ? "Connected — paused; checking for lifecycle changes."
          : page.has_more ? "Recovering recent console output…" : "Connected to run logs.");
        // A paused observer also detects resume/stop initiated in another tab.
        // Reconcile through the normal status/checkpoint path, never a local guess.
        if (["PAUSED", "DISCONNECTED"].includes(statusRef.current) && page.state !== statusRef.current
            && revision === controlRevision.current && !actionPending.current && !stopPending.current) {
          // Use a fresh subscription even if a failed status read still has
          // its old reference queued in React's current update batch.
          setRecovery({...logReference!});
        }
        const delay = logPollDelay(page);
        if (delay !== null) timer = window.setTimeout(() => void pollLogs(), delay);
        else setLogConnection("Console output recovered; monitoring finished.");
      } catch (reason) {
        if (cancelled) return;
        setLogConnection("Console connection unavailable.");
        setLogNotice(`Live console could not reconnect. ${reason instanceof Error ? reason.message : "Check the backend and refresh."}`);
        const lostOwner = reason instanceof GAControlError && ["GA_PROCESS_CHANGED", "GA_UNKNOWN_RUN", "GA_CONTROL_ROUTE_MISSING"].includes(reason.code);
        if (!lostOwner && !["STOPPED", "COMPLETED", "FAILED", "INTERRUPTED"].includes(statusRef.current)) {
          timer = window.setTimeout(() => void pollLogs(), 5000);
        }
      }
    }
    timer = window.setTimeout(() => {
      setLogConnection("Reconnecting to run logs…");
      void pollLogs();
    }, 0);
    return () => { cancelled = true; if (timer !== undefined) window.clearTimeout(timer); };
  }, [logReference, executionStatus]);


  // =========================================================
  // TIMER
  // =========================================================

  useEffect(() => {

    if (!loading || executionStatus === "PAUSED") {
      return;
    }


    const timer =
      window.setInterval(
        () => {

          setElapsedSeconds(
            (current) =>
              current + 1
          );

        },
        1000
      );


    return () => {

      window.clearInterval(
        timer
      );

    };

  }, [
    loading, executionStatus,
  ]);


  // =========================================================
  // LOG
  // =========================================================

  function addLog(
    message: string, event?: GAMonitoringEvent
  ) {
    // New servers supply canonical cursor logs. Keep legacy SSE compatibility
    // without racing two copies of the same diagnostic into the console.
    if (event?.type === "log" && Number.isInteger(event.data.log_sequence)) return;

    setLogs(
      (currentLogs) => {

        const updated = [
          ...currentLogs,
          message,
        ];


        return updated.slice(
          -500
        );

      }
    );

  }


  // =========================================================
  // RUN GA
  // =========================================================

  async function runGA(
    newPopulationSize = 10,
    newGenerations = 2,
    newFreshChromosomes = 2,
    baselineMode:
      BaselineMode = "fresh"
  ) {

    if (runningRef.current || stopPending.current || actionPending.current) {
      return;
    }


    const previousResult = gaData;
    let recoveryStarted = false;
    runningRef.current =
      true;


    setPopulationSize(
      newPopulationSize
    );


    setGenerations(
      newGenerations
    );


    setFreshChromosomes(
      newFreshChromosomes
    );


    try {

      setLoading(true);
      status("CONNECTING");
      setRecovery(null);
      setRecoveryNotice(null);
      setServerAcceptingStop(true);
      setActiveRunId(null);
      setLogReference(null);
      activeRunRef.current = null;
      stopPending.current = false;
      setStopError(null);
      setStopSubmitting(false);
      controlRevision.current++;
      actionPending.current = false; setActionSubmitting(false);
      setServerAcceptingPause(false); setServerAcceptingResume(false); setControlError(null);
      setProgressHistory([]);

      setError(null);

      setElapsedSeconds(0);

      setLogs([]);

      const backend = await getGABackendStatus();
      processRef.current = backend.process_instance_id;
      if (backend.active_run) {
        applySnapshot(backend.active_run);
        rememberRun(backend.active_run.run_id, backend.process_instance_id);
        setRecovery({run_id:backend.active_run.run_id,process_instance_id:backend.process_instance_id});
        setRecoveryNotice("An existing run was discovered. Monitoring reconnected; no second run was started. Earlier events may be missing.");
        recoveryStarted = true;
        return;
      }
      setGaData(null);


      const result =
        await runGeneticAlgorithmStream(

          newPopulationSize,

          newGenerations,

          newFreshChromosomes,

          addLog,

          baselineMode,
          receiveEvent,
          backend.process_instance_id

        );


      /*
       * Normal generated result.
       */

      if (statusRef.current === "PAUSED" && activeRunRef.current && processRef.current) {
        setGaData(previousResult);
        setRecovery({run_id:activeRunRef.current,process_instance_id:processRef.current});
        recoveryStarted = true;
        return;
      }
      try { sessionStorage.removeItem(RUN_REFERENCE_KEY); } catch { /* Optional storage. */ }
      status(result?.status === "STOPPED" || statusRef.current === "STOPPED" ? "STOPPED" : "COMPLETED");
      if (!result) {
        setGaData(previousResult);
        return;
      }
      if (result.elapsed_ms !== undefined) setElapsedSeconds(Math.floor(result.elapsed_ms / 1000));
      setGaData({

        ...result,

        result_source:
          "generated",

        optimization_performed:
          true,

      });


    } catch (err) {
      status(err instanceof GAStreamError ? err.status : err instanceof GAControlError ? "REJECTED" : "DISCONNECTED");
      setGaData(previousResult);
      if (err instanceof GAStreamError && err.status === "DISCONNECTED" && activeRunRef.current && processRef.current) {
        setRecovery({run_id:activeRunRef.current,process_instance_id:processRef.current});
        setRecoveryNotice("The SSE connection ended. Reconnecting through read-only status polling; earlier events may be missing.");
        recoveryStarted = true;
      }

      if (
        err instanceof Error
      ) {

        setError(
          err.message
        );


        addLog(
          `ERROR: ${err.message}`
        );


      } else {

        const message =
          "An unexpected error occurred.";


        setError(
          message
        );


        addLog(
          `ERROR: ${message}`
        );

      }


    } finally {

      if (!recoveryStarted) {
        setLoading(false);
        runningRef.current = false;
      }

    }

  }


  // =========================================================
  // LOAD EXISTING CHROMOSOME RESULT
  //
  // NO GA IS RUN HERE.
  // =========================================================

  function loadChromosomeData(
    data: GARunData
  ) {
    if (runningRef.current) return;
    setProgressHistory([]);
    status("IDLE");
    setActiveRunId(null);
    setLogReference(null);
    setStopError(null);

    setGaData(
      data
    );


    setLoading(
      false
    );


    setError(
      null
    );


    setLogs(
      []
    );


    setElapsedSeconds(
      0
    );

  }


  // =========================================================
  // CLEAR RESULT
  // =========================================================

  function clearGAData() {
    if (runningRef.current) return;
    setProgressHistory([]);
    status("IDLE");
    setActiveRunId(null);
    setLogReference(null);
    setStopError(null);

    setGaData(
      null
    );


    setError(
      null
    );


    setLogs(
      []
    );


    setElapsedSeconds(
      0
    );

  }


  return (

    <GAContext.Provider
      value={{
        gaData,
        pauseGA, resumeGA, canPause, canResume, controlError, pausedRuns, selectPausedRun,
        activeRunId,
        recoveryNotice,
        executionStatus,
        progressHistory,
        stopGA,
        canStop,
        stopError,
        loading,
        error,
        elapsedSeconds,
        logs,
        logNotice, logConnection,

        populationSize,
        generations,
        freshChromosomes,

        runGA,

        loadChromosomeData,

        clearGAData,
      }}
    >

      {children}

    </GAContext.Provider>

  );
}


export function useGA() {

  const context =
    useContext(
      GAContext
    );


  if (!context) {

    throw new Error(
      "useGA must be used inside GAProvider."
    );

  }


  return context;
}
