import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  runGeneticAlgorithmStream,
} from "../services/gaService";

import type {
  GARunData,
} from "../types/ga";


type GAContextType = {

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
    freshChromosomes?: number
  ) => Promise<void>;

};


const GAContext =
  createContext<
    GAContextType | undefined
  >(undefined);


type GAProviderProps = {
  children: ReactNode;
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
    useState(false);


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


  const runningRef =
    useRef(false);


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

  }, [loading]);


  // =========================================================
  // ADD LIVE LOG
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


        // Avoid keeping thousands and thousands
        // of DOM lines in the browser.
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
    newFreshChromosomes = 2
  ) {

    if (
      runningRef.current
    ) {
      return;
    }


    runningRef.current = true;


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

      setError(null);

      setElapsedSeconds(0);

      setLogs([]);

      setGaData(null);


      const result =
        await runGeneticAlgorithmStream(

          newPopulationSize,

          newGenerations,

          newFreshChromosomes,

          addLog

        );


      setGaData(
        result
      );


    } catch (err) {

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

      setLoading(false);

      runningRef.current =
        false;

    }

  }


  return (

    <GAContext.Provider
      value={{
        gaData,
        loading,
        error,
        elapsedSeconds,
        logs,

        populationSize,
        generations,
        freshChromosomes,

        runGA,
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