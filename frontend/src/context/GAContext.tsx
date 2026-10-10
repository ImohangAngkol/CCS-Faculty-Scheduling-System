import { GAStreamError } from "../services/gaMonitoring";
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
} from "../services/gaService";
import { GAControlError, readRunReference, RUN_REFERENCE_KEY } from "../services/gaRecovery";
import type { RunReference, RunSnapshot } from "../services/gaRecovery";

import type {
  BaselineMode,
  GARunData,
} from "../types/ga";


type GAContextType = {
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
  const [recoveryNotice, setRecoveryNotice] = useState<string | null>(null);
  const [serverAcceptingStop, setServerAcceptingStop] = useState(true);
  const [stopError, setStopError] = useState<string | null>(null);
  const statusRef = useRef<GAExecutionStatus>("RECOVERING");
  const stopPending = useRef(false);
  const stopAcknowledged = useRef(false);
  const status = useCallback((value: GAExecutionStatus) => { statusRef.current = value; setExecutionStatus(value); }, []);

  function rememberRun(runId: string, processInstanceId: string) {
    try { sessionStorage.setItem(RUN_REFERENCE_KEY, JSON.stringify({ run_id: runId, process_instance_id: processInstanceId })); } catch { /* Discovery still works without browser storage. */ }
  }
  const applySnapshot = useCallback((snapshot: RunSnapshot) => {
    activeRunRef.current = snapshot.run_id;
    processRef.current = snapshot.process_instance_id;
    setActiveRunId(snapshot.run_id);
    setServerAcceptingStop(snapshot.accepting_stop);
    const awaitingStop = ["STOP_REQUESTED", "STOPPING"].includes(statusRef.current)
      && (stopPending.current || stopAcknowledged.current);
    const olderStopState = awaitingStop
      && (["CREATED", "INITIALIZING", "RUNNING"].includes(snapshot.state)
        || (statusRef.current === "STOPPING" && snapshot.state === "STOP_REQUESTED"));
    if (!olderStopState) status(snapshot.state);
    setElapsedSeconds(Math.floor(snapshot.elapsed_ms / 1000));
    if (snapshot.configuration.population_size !== undefined) setPopulationSize(snapshot.configuration.population_size);
    if (snapshot.configuration.generations !== undefined) setGenerations(snapshot.configuration.generations);
    if (snapshot.configuration.fresh_chromosomes !== undefined) setFreshChromosomes(snapshot.configuration.fresh_chromosomes);
    const metric = snapshot.latest_progress;
    if (metric) setProgressHistory(current => current.some(item => item.generation === metric.generation) ? current : [...current, metric]);
    if (["STOP_REQUESTED", "STOPPING", "STOPPED"].includes(snapshot.state)) stopAcknowledged.current = true;
  }, [status]);

  function receiveEvent(event: GAMonitoringEvent) {
    if ((event.type === "run_created" || event.type === "run_started") && typeof event.data.process_instance_id === "string") {
      if (processRef.current && processRef.current !== event.data.process_instance_id) throw new GAStreamError("The stream came from a different backend process; run ownership could not be verified.");
      processRef.current = event.data.process_instance_id;
    }
    if (processRef.current) rememberRun(event.run_id, processRef.current);
    if ((event.type === "run_created" || event.type === "run_started" || event.type === "run_state_changed") && typeof event.data.accepting_stop === "boolean") setServerAcceptingStop(event.data.accepting_stop);
    activeRunRef.current = event.run_id;
    setActiveRunId(event.run_id);
    if (event.type === "run_created" || event.type === "run_started") {
      if (!["STOP_REQUESTED", "STOPPING", "STOPPED"].includes(statusRef.current)) {
        status(event.data.status === "STOP_REQUESTED" ? "STOP_REQUESTED" : event.data.status === "CREATED" ? "CREATED" : "INITIALIZING");
      }
    }
    if (event.type === "run_state_changed") {
      status(event.data.status as GAExecutionStatus);
      if (["STOP_REQUESTED", "STOPPING", "STOPPED"].includes(String(event.data.status))) stopAcknowledged.current = true;
      if (typeof event.data.elapsed_ms === "number") setElapsedSeconds(Math.floor(event.data.elapsed_ms / 1000));
    }
    if (event.type === "done" && event.data.status === "STOPPED") status("STOPPED");
    if (event.type === "initial_population_ready" || event.type === "generation_completed") {
      if (["CREATED", "INITIALIZING", "RUNNING"].includes(statusRef.current)) status("RUNNING");
      const metric = event.data;
      setProgressHistory(current => current.some(item => item.generation === metric.generation) ? current : [...current, metric]);
      setElapsedSeconds(Math.floor(metric.elapsed_ms / 1000));
    }
  }

  const runningRef =
    useRef(true);

  const canStop = loading && !!activeRunId && serverAcceptingStop && ["CREATED", "INITIALIZING", "RUNNING"].includes(executionStatus);
  async function stopGA() {
    if (!canStop || !activeRunId || stopPending.current) return;
    stopPending.current = true;
    const requestedRunId = activeRunId;
    const previous = statusRef.current;
    status("STOP_REQUESTED");
    setStopError(null);
    try {
      const acknowledgement = await stopGARun(activeRunId, processRef.current ?? undefined);
      if (activeRunRef.current !== requestedRunId) return;
      if (acknowledgement.accepted && ["STOP_REQUESTED", "STOPPING", "STOPPED"].includes(acknowledgement.state)) stopAcknowledged.current = true;
      // HTTP and SSE can arrive in either order. Never regress a terminal state.
      if (["STOP_REQUESTED", "STOPPING"].includes(statusRef.current)) {
        if (statusRef.current === "STOP_REQUESTED" && acknowledgement.accepted && ["STOP_REQUESTED", "STOPPING"].includes(acknowledgement.state)) {
          status(acknowledgement.state);
        } else if (!acknowledgement.accepted) {
          setStopError(`Stop was not accepted; the run is ${acknowledgement.state.toLowerCase()}. Waiting for its final stream event.`);
        }
      }
    } catch (reason) {
      if (activeRunRef.current !== requestedRunId) return;
      setStopError(reason instanceof Error ? reason.message : "Unable to request a stop.");
      if (statusRef.current === "STOP_REQUESTED" && !stopAcknowledged.current) status(previous);
    } finally {
      if (activeRunRef.current === requestedRunId) stopPending.current = false;
    }
  }


  // =========================================================
  // DISCOVER THE CURRENT PROCESS; RECOVER MONITORING WITHOUT STARTING A GA.
  // =========================================================

  useEffect(() => {
    let cancelled = false;
    runningRef.current = true;
    async function discover() {
      try {
        const [backend, latest] = await Promise.all([getGABackendStatus(), getLatestGAResult().catch(() => null)]);
        if (cancelled) return;
        processRef.current = backend.process_instance_id;
        if (latest) setGaData(latest);
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
          if (remembered.process_instance_id !== backend.process_instance_id) {
            activeRunRef.current = remembered.run_id;
            setActiveRunId(remembered.run_id);
            status("INTERRUPTED");
            setRecoveryNotice("The backend process changed. The previous run is interrupted or unknown; its population was not restored. Existing saved results remain available.");
          } else {
            setRecovery(remembered);
            setRecoveryNotice("Checking the remembered run in the same backend process. Earlier events may be missing.");
            return;
          }
        } else status("IDLE");
        runningRef.current = false;
        setLoading(false);
      } catch (reason) {
        if (cancelled) return;
        status(reason instanceof GAControlError ? "REJECTED" : "DISCONNECTED");
        setError(reason instanceof Error ? reason.message : "Unable to discover the backend run. No cancellation occurred.");
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
      try {
        const snapshot = await getGARunState(recovery!.run_id, recovery!.process_instance_id);
        if (cancelled) return;
        applySnapshot(snapshot);
        setError(null);
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


  // =========================================================
  // TIMER
  // =========================================================

  useEffect(() => {

    if (!loading) {
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
    loading,
  ]);


  // =========================================================
  // LOG
  // =========================================================

  function addLog(
    message: string
  ) {

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

    if (
      runningRef.current
    ) {
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
      activeRunRef.current = null;
      stopPending.current = false;
      setStopError(null);
      stopAcknowledged.current = false;
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
