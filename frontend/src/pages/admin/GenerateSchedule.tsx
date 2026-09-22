import {
  useEffect,
  useState,
  type ChangeEvent,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  useGA,
} from "../../context/GAContext";

import GALiveConsole
  from "../../components/ga/GALiveConsole";

import {
  getSavedBestDownloadUrl,
  getSavedBestStatus,
  uploadBaselineChromosome,
} from "../../services/gaService";

import type {
  BaselineMode,
} from "../../types/ga";


type SavedBestStatus = {
  exists: boolean;

  fitness:
    number | null;

  created_at:
    string | null;
};


export default function GenerateSchedule() {

  const navigate =
    useNavigate();


  const {
    gaData,
    loading,
    error,
    elapsedSeconds,
    logs,

    populationSize:
      runningPopulationSize,

    generations:
      runningGenerations,

    freshChromosomes:
      runningFreshChromosomes,

    runGA,
  } = useGA();


  // ==========================================================
  // GA SETTINGS
  // ==========================================================

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


  // ==========================================================
  // BASELINE
  // ==========================================================

const [
  baselineMode,
  setBaselineMode,
] =
  useState<BaselineMode>(
    () => {

      const preferred =
        window.sessionStorage.getItem(
          "gaPreferredBaseline"
        );


      window.sessionStorage.removeItem(
        "gaPreferredBaseline"
      );


      if (
        preferred === "saved" ||
        preferred === "uploaded"
      ) {

        return preferred;

      }


      return "fresh";

    }
  );


  const [
    uploadedBaseline,
    setUploadedBaseline,
  ] =
    useState<unknown | null>(
      null
    );


  const [
    uploadedFileName,
    setUploadedFileName,
  ] =
    useState("");


  const [
    savedBest,
    setSavedBest,
  ] =
    useState<SavedBestStatus>({
      exists: false,
      fitness: null,
      created_at: null,
    });


  const [
    checkingSavedBest,
    setCheckingSavedBest,
  ] =
    useState(true);


  // ==========================================================
  // CHECK WHETHER A SAVED BEST EXISTS
  // ==========================================================

  useEffect(() => {

    async function checkSavedBest() {

      try {

        setCheckingSavedBest(
          true
        );


        const response =
          await getSavedBestStatus();


        setSavedBest(
          response.data
        );


      } catch {

        setSavedBest({
          exists: false,
          fitness: null,
          created_at: null,
        });


      } finally {

        setCheckingSavedBest(
          false
        );

      }

    }


    checkSavedBest();

  }, [
    gaData,
  ]);


  // ==========================================================
  // READ UPLOADED JSON
  // ==========================================================

  async function handleBaselineFile(
    event:
      ChangeEvent<HTMLInputElement>
  ) {

    const file =
      event
        .target
        .files?.[0];


    if (!file) {
      return;
    }


    try {

      const text =
        await file.text();


      const parsed =
        JSON.parse(
          text
        );


      setUploadedBaseline(
        parsed
      );


      setUploadedFileName(
        file.name
      );


    } catch {

      setUploadedBaseline(
        null
      );


      setUploadedFileName(
        ""
      );


      window.alert(
        "The selected file is not a valid JSON chromosome."
      );

    }

  }


  // ==========================================================
  // RUN
  // ==========================================================

  async function handleGenerate() {

    try {

      // -------------------------------------------------------
      // SAVED BASELINE VALIDATION
      // -------------------------------------------------------

      if (
        baselineMode ===
        "saved"
        &&
        !savedBest.exists
      ) {

        window.alert(
          "No saved best chromosome exists yet. " +
          "Run the Genetic Algorithm using Fresh Population first."
        );

        return;

      }


      // -------------------------------------------------------
      // UPLOAD BASELINE FIRST
      // -------------------------------------------------------

      if (
        baselineMode ===
        "uploaded"
      ) {

        if (
          !uploadedBaseline
        ) {

          window.alert(
            "Please select a chromosome JSON file first."
          );

          return;

        }


        await uploadBaselineChromosome(
          uploadedBaseline
        );

      }


      // -------------------------------------------------------
      // START GA
      // -------------------------------------------------------

      await runGA(

        populationSize,

        generations,

        freshChromosomes,

        baselineMode

      );


    } catch (runError) {

      window.alert(
        runError instanceof Error

          ? runError.message

          : (
              "Unable to start the Genetic Algorithm."
            )
      );

    }

  }


  return (

    <div className="space-y-6">

      {/* ==================================================== */}
      {/* PAGE HEADER */}
      {/* ==================================================== */}

      <div>

        <h1
          className="
            text-2xl
            font-bold
            text-slate-900
          "
        >
          Generate Schedule
        </h1>


        <p
          className="
            mt-1
            text-sm
            text-slate-500
          "
        >
          Configure the Genetic Algorithm and choose
          how the starting population should be created.
        </p>

      </div>


      {/* ==================================================== */}
      {/* SETTINGS CARD */}
      {/* ==================================================== */}

      <div
        className="
          rounded-xl
          border
          border-slate-200
          bg-white
          p-6
          shadow-sm
        "
      >

        <div
          className="
            border-l-4
            border-[#0F766E]
            pl-4
          "
        >

          <h2
            className="
              text-lg
              font-semibold
              text-slate-900
            "
          >
            Genetic Algorithm Settings
          </h2>


          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Choose a starting chromosome and
            configure the optimization parameters.
          </p>

        </div>


        {/* ================================================== */}
        {/* BASELINE MODE */}
        {/* ================================================== */}

        <div
          className="
            mt-6
            rounded-xl
            border
            border-teal-100
            bg-[#F0FDFA]
            p-5
          "
        >

          <h3
            className="
              font-semibold
              text-slate-900
            "
          >
            Starting Population
          </h3>


          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Choose whether the Genetic Algorithm starts
            completely fresh or uses an existing good
            chromosome as part of the initial population.
          </p>


          <div
            className="
              mt-4
              grid
              gap-4
              lg:grid-cols-3
            "
          >

            {/* ================================================= */}
            {/* FRESH */}
            {/* ================================================= */}

            <label
              className={`
                cursor-pointer
                rounded-xl
                border
                bg-white
                p-4
                transition

                ${
                  baselineMode ===
                  "fresh"

                    ? (
                        "border-[#0F766E] " +
                        "ring-2 ring-[#0F766E]/10"
                      )

                    : (
                        "border-slate-200 " +
                        "hover:border-teal-300"
                      )
                }
              `}
            >

              <div
                className="
                  flex
                  items-center
                  gap-2
                "
              >

                <input
                  type="radio"
                  name="baselineMode"
                  checked={
                    baselineMode ===
                    "fresh"
                  }
                  disabled={loading}
                  onChange={
                    () =>
                      setBaselineMode(
                        "fresh"
                      )
                  }
                />


                <span
                  className="
                    font-semibold
                    text-slate-900
                  "
                >
                  Fresh Population
                </span>

              </div>


              <p
                className="
                  mt-3
                  text-xs
                  leading-5
                  text-slate-500
                "
              >
                Generate every chromosome from scratch.
                Use this when creating the first schedule
                or when you want a completely new search.
              </p>

            </label>


            {/* ================================================= */}
            {/* SAVED BEST */}
            {/* ================================================= */}

            <label
              className={`
                rounded-xl
                border
                bg-white
                p-4
                transition

                ${
                  savedBest.exists
                    ? "cursor-pointer"
                    : "cursor-not-allowed opacity-60"
                }

                ${
                  baselineMode ===
                  "saved"

                    ? (
                        "border-[#0F766E] " +
                        "ring-2 ring-[#0F766E]/10"
                      )

                    : (
                        "border-slate-200"
                      )
                }
              `}
            >

              <div
                className="
                  flex
                  items-center
                  gap-2
                "
              >

                <input
                  type="radio"
                  name="baselineMode"
                  checked={
                    baselineMode ===
                    "saved"
                  }
                  disabled={
                    loading ||
                    !savedBest.exists
                  }
                  onChange={
                    () =>
                      setBaselineMode(
                        "saved"
                      )
                  }
                />


                <span
                  className="
                    font-semibold
                    text-slate-900
                  "
                >
                  Saved Best
                </span>

              </div>


              {checkingSavedBest ? (

                <p
                  className="
                    mt-3
                    text-xs
                    text-slate-500
                  "
                >
                  Checking saved chromosome...
                </p>

              ) : savedBest.exists ? (

                <>

                  <p
                    className="
                      mt-3
                      text-xs
                      leading-5
                      text-slate-500
                    "
                  >
                    Seed the population with the best
                    chromosome previously discovered.
                  </p>


                  <p
                    className="
                      mt-2
                      text-sm
                      font-bold
                      text-[#115E59]
                    "
                  >
                    Saved Fitness:{" "}
                    {savedBest.fitness}
                  </p>

                </>

              ) : (

                <p
                  className="
                    mt-3
                    text-xs
                    leading-5
                    text-slate-500
                  "
                >
                  No saved chromosome yet.
                  Generate a fresh schedule first.
                </p>

              )}

            </label>


            {/* ================================================= */}
            {/* UPLOAD */}
            {/* ================================================= */}

            <label
              className={`
                cursor-pointer
                rounded-xl
                border
                bg-white
                p-4
                transition

                ${
                  baselineMode ===
                  "uploaded"

                    ? (
                        "border-[#0F766E] " +
                        "ring-2 ring-[#0F766E]/10"
                      )

                    : (
                        "border-slate-200 " +
                        "hover:border-teal-300"
                      )
                }
              `}
            >

              <div
                className="
                  flex
                  items-center
                  gap-2
                "
              >

                <input
                  type="radio"
                  name="baselineMode"
                  checked={
                    baselineMode ===
                    "uploaded"
                  }
                  disabled={loading}
                  onChange={
                    () =>
                      setBaselineMode(
                        "uploaded"
                      )
                  }
                />


                <span
                  className="
                    font-semibold
                    text-slate-900
                  "
                >
                  Upload Baseline
                </span>

              </div>


              <p
                className="
                  mt-3
                  text-xs
                  leading-5
                  text-slate-500
                "
              >
                Use a previously exported good chromosome
                JSON file as the starting baseline.
              </p>

            </label>

          </div>


          {/* ================================================= */}
          {/* UPLOAD FILE */}
          {/* ================================================= */}

          {baselineMode ===
            "uploaded" && (

            <div
              className="
                mt-5
                rounded-lg
                border
                border-dashed
                border-teal-300
                bg-white
                p-4
              "
            >

              <label
                className="
                  block
                  text-sm
                  font-semibold
                  text-slate-700
                "
              >
                Baseline Chromosome JSON
              </label>


              <input
                type="file"
                accept=".json,application/json"
                disabled={loading}
                onChange={
                  handleBaselineFile
                }
                className="
                  mt-3
                  block
                  w-full
                  text-sm
                  text-slate-500
                "
              />


              {uploadedFileName && (

                <div
                  className="
                    mt-3
                    rounded-lg
                    bg-[#CCFBF1]
                    px-3
                    py-2
                  "
                >

                  <p
                    className="
                      text-sm
                      font-semibold
                      text-[#115E59]
                    "
                  >
                    ✓ {uploadedFileName}
                  </p>

                </div>

              )}

            </div>

          )}


          {/* ================================================= */}
          {/* DOWNLOAD CURRENT BEST */}
          {/* ================================================= */}

          {savedBest.exists && (

            <div
              className="
                mt-5
                border-t
                border-teal-100
                pt-4
              "
            >

              <a
                href={
                  getSavedBestDownloadUrl()
                }
                className="ccs-btn-secondary"
              >
                Download Saved Best Chromosome
              </a>

            </div>

          )}

        </div>


        {/* ================================================== */}
        {/* GA PARAMETERS */}
        {/* ================================================== */}

        <div
          className="
            mt-6
            grid
            gap-5
            md:grid-cols-3
          "
        >

          {/* POPULATION */}

          <div>

            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Population Size
            </label>


            <input
              type="number"
              min={2}
              max={500}
              value={populationSize}
              disabled={loading}
              onChange={
                (event) =>
                  setPopulationSize(
                    Number(
                      event.target.value
                    )
                  )
              }
              className="
                ccs-input
                mt-2
                w-full
                rounded-lg
                border
                border-slate-300
                px-3
                py-2.5
                disabled:bg-slate-100
              "
            />


            <p
              className="
                mt-1
                text-xs
                text-slate-400
              "
            >
              Allowed range: 2–500
            </p>

          </div>


          {/* GENERATIONS */}

          <div>

            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Generations
            </label>


            <input
              type="number"
              min={1}
              max={10000}
              value={generations}
              disabled={loading}
              onChange={
                (event) =>
                  setGenerations(
                    Number(
                      event.target.value
                    )
                  )
              }
              className="
                ccs-input
                mt-2
                w-full
                rounded-lg
                border
                border-slate-300
                px-3
                py-2.5
                disabled:bg-slate-100
              "
            />


            <p
              className="
                mt-1
                text-xs
                text-slate-400
              "
            >
              Allowed range: 1–10,000
            </p>

          </div>


          {/* FRESH CHROMOSOMES */}

          <div>

            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Fresh Chromosomes
            </label>


            <input
              type="number"
              min={0}
              max={500}
              value={freshChromosomes}
              disabled={loading}
              onChange={
                (event) =>
                  setFreshChromosomes(
                    Number(
                      event.target.value
                    )
                  )
              }
              className="
                ccs-input
                mt-2
                w-full
                rounded-lg
                border
                border-slate-300
                px-3
                py-2.5
                disabled:bg-slate-100
              "
            />


            <p
              className="
                mt-1
                text-xs
                text-slate-400
              "
            >
              Allowed range: 0–500
            </p>

          </div>

        </div>


        {/* ================================================== */}
        {/* BUTTON */}
        {/* ================================================== */}

        <div className="mt-6">

          <button
            onClick={
              handleGenerate
            }
            disabled={loading}
            className="ccs-btn-primary"
          >

            {loading && (

              <span
                className="
                  h-4
                  w-4
                  animate-spin
                  rounded-full
                  border-2
                  border-white
                  border-t-transparent
                "
              />

            )}


            {loading
              ? "Generating Schedule..."
              : "Generate Schedule"
            }

          </button>

        </div>

      </div>


      {/* ==================================================== */}
      {/* RUNNING */}
      {/* ==================================================== */}

      {loading && (

        <div
          className="
            overflow-hidden
            rounded-xl
            border
            border-teal-200
            bg-white
            shadow-sm
          "
        >

          <div
            className="
              h-1.5
              bg-[#0F766E]
            "
          />


          <div className="p-6">

            <div
              className="
                flex
                flex-col
                gap-5
                md:flex-row
                md:items-center
                md:justify-between
              "
            >

              <div
                className="
                  flex
                  items-center
                  gap-5
                "
              >

                <div
                  className="
                    flex
                    h-16
                    w-16
                    items-center
                    justify-center
                    rounded-full
                    bg-[#F0FDFA]
                  "
                >

                  <div
                    className="
                      h-10
                      w-10
                      animate-spin
                      rounded-full
                      border-4
                      border-teal-100
                      border-t-[#0F766E]
                    "
                  />

                </div>


                <div>

                  <p
                    className="
                      text-xs
                      font-bold
                      uppercase
                      tracking-wider
                      text-[#0F766E]
                    "
                  >
                    Running
                  </p>


                  <h2
                    className="
                      mt-1
                      text-xl
                      font-bold
                      text-slate-900
                    "
                  >
                    Genetic Algorithm is running
                  </h2>


                  <p
                    className="
                      mt-1
                      text-sm
                      text-slate-500
                    "
                  >
                    Starting Mode:{" "}
                    <strong>
                      {
                        baselineMode === "fresh"
                          ? "Fresh Population"
                          : baselineMode === "saved"
                          ? "Saved Best Chromosome"
                          : "Uploaded Baseline"
                      }
                    </strong>
                  </p>

                </div>

              </div>


              <div
                className="
                  rounded-xl
                  bg-[#F0FDFA]
                  px-6
                  py-4
                  text-center
                "
              >

                <p
                  className="
                    text-xs
                    uppercase
                    text-slate-500
                  "
                >
                  Elapsed
                </p>


                <p
                  className="
                    mt-1
                    text-3xl
                    font-bold
                    text-[#115E59]
                  "
                >
                  {formatElapsedTime(
                    elapsedSeconds
                  )}
                </p>

              </div>

            </div>


            <div
              className="
                mt-6
                grid
                gap-3
                sm:grid-cols-3
              "
            >

              <RunningStat
                label="Population"
                value={
                  runningPopulationSize
                }
              />


              <RunningStat
                label="Generations"
                value={
                  runningGenerations
                }
              />


              <RunningStat
                label="Fresh Chromosomes"
                value={
                  runningFreshChromosomes
                }
              />

            </div>

          </div>

        </div>

      )}


      {/* ==================================================== */}
      {/* LIVE CONSOLE */}
      {/* ==================================================== */}

      {(loading ||
        logs.length > 0) && (

        <div>

          <h2
            className="
              mb-1
              text-lg
              font-semibold
              text-slate-900
            "
          >
            Genetic Algorithm Live Progress
          </h2>


          <p
            className="
              mb-3
              text-sm
              text-slate-500
            "
          >
            Live output from the optimization process.
          </p>


          <GALiveConsole
            logs={logs}
            loading={loading}
          />

        </div>

      )}


      {/* ==================================================== */}
      {/* ERROR */}
      {/* ==================================================== */}

      {error && (

        <div
          className="
            rounded-xl
            border
            border-red-200
            bg-red-50
            p-5
          "
        >

          <p
            className="
              font-semibold
              text-red-700
            "
          >
            Schedule generation failed
          </p>


          <p
            className="
              mt-1
              text-sm
              text-red-600
            "
          >
            {error}
          </p>

        </div>

      )}


      {/* ==================================================== */}
      {/* COMPLETED */}
      {/* ==================================================== */}

      {gaData &&
        !loading && (

        <div
          className="
            overflow-hidden
            rounded-xl
            border
            border-teal-200
            bg-white
            shadow-sm
          "
        >

          <div
            className="
              h-1.5
              bg-[#0F766E]
            "
          />


          <div className="p-6">

            <div
              className="
                flex
                flex-col
                gap-4
                md:flex-row
                md:items-center
                md:justify-between
              "
            >

              <div>

                <div
                  className="
                    inline-flex
                    rounded-full
                    bg-[#CCFBF1]
                    px-3
                    py-1
                    text-xs
                    font-bold
                    text-[#115E59]
                  "
                >
                  ✓ Generation Complete
                </div>


                <h2
                  className="
                    mt-3
                    text-xl
                    font-bold
                    text-slate-900
                  "
                >
                  Schedule generated successfully
                </h2>


                <p
                  className="
                    mt-1
                    text-sm
                    text-slate-500
                  "
                >
                  The best chromosome is ready for review.
                </p>

              </div>


              <div
                className="
                  flex
                  flex-wrap
                  gap-3
                "
              >

                <button
                  onClick={
                    () =>
                      navigate(
                        "/admin/schedules"
                      )
                  }
                  className="ccs-btn-secondary"
                >
                  View Schedule
                </button>


                <button
                  onClick={
                    () =>
                      navigate(
                        "/admin/analysis"
                      )
                  }
                  className="ccs-btn-primary"
                >
                  View GA Analysis
                </button>

              </div>

            </div>


            {/* ================================================= */}
            {/* RESULT SUMMARY */}
            {/* ================================================= */}

            <div
              className="
                mt-6
                grid
                gap-4
                md:grid-cols-3
              "
            >

              <ResultCard
                label="Best Fitness"
                value={
                  gaData.best_fitness
                }
              />


              <ResultCard
                label="Generations Completed"
                value={
                  gaData
                    .generations_completed
                }
              />


              <ResultCard
                label="Schedule Entries"
                value={
                  gaData.schedule.length
                }
              />

            </div>


            {/* ================================================= */}
            {/* BASELINE COMPARISON */}
            {/* ================================================= */}

            {gaData
              .starting_baseline_fitness !=
              null && (

              <div
                className="
                  mt-6
                  rounded-xl
                  border
                  border-teal-100
                  bg-[#F0FDFA]
                  p-5
                "
              >

                <h3
                  className="
                    font-semibold
                    text-slate-900
                  "
                >
                  Baseline Improvement
                </h3>


                <p
                  className="
                    mt-1
                    text-sm
                    text-slate-500
                  "
                >
                  Comparison between the chromosome
                  used to seed this run and the final
                  best chromosome.
                </p>


                <div
                  className="
                    mt-4
                    grid
                    gap-4
                    sm:grid-cols-3
                  "
                >

                  <BaselineResult
                    label="Starting Fitness"
                    value={
                      gaData
                        .starting_baseline_fitness
                    }
                  />


                  <BaselineResult
                    label="Final Fitness"
                    value={
                      gaData.best_fitness
                    }
                  />


                  <BaselineResult
                    label="Improvement"
                    value={
                      gaData
                        .starting_baseline_fitness
                      -
                      gaData.best_fitness
                    }
                  />

                </div>

              </div>

            )}


            {/* ================================================= */}
            {/* NEW BEST */}
            {/* ================================================= */}

            {gaData
              .saved_best_updated && (

              <div
                className="
                  mt-5
                  rounded-lg
                  border
                  border-[#EAB308]/40
                  bg-[#FEFCE8]
                  p-4
                "
              >

                <p
                  className="
                    font-semibold
                    text-slate-800
                  "
                >
                  ★ New Best Chromosome Saved
                </p>


                <p
                  className="
                    mt-1
                    text-sm
                    text-slate-600
                  "
                >
                  This chromosome is now available as
                  the Saved Best baseline for future
                  Genetic Algorithm runs.
                </p>

              </div>

            )}

          </div>

        </div>

      )}

    </div>

  );

}


/* ==========================================================
   HELPERS
========================================================== */

function formatElapsedTime(
  seconds: number
) {

  const minutes =
    Math.floor(
      seconds / 60
    );


  const remainingSeconds =
    seconds % 60;


  return (
    `${String(
      minutes
    ).padStart(
      2,
      "0"
    )}:` +
    `${String(
      remainingSeconds
    ).padStart(
      2,
      "0"
    )}`
  );

}


type CardProps = {
  label: string;
  value: number | string;
};


function RunningStat({
  label,
  value,
}: CardProps) {

  return (

    <div
      className="
        rounded-lg
        border
        border-teal-100
        bg-[#F0FDFA]
        px-4
        py-3
      "
    >

      <p
        className="
          text-xs
          text-slate-500
        "
      >
        {label}
      </p>


      <p
        className="
          mt-1
          text-lg
          font-bold
          text-[#115E59]
        "
      >
        {value}
      </p>

    </div>

  );

}


function ResultCard({
  label,
  value,
}: CardProps) {

  return (

    <div
      className="
        rounded-lg
        border
        border-teal-100
        bg-[#F0FDFA]
        p-4
      "
    >

      <div
        className="
          mb-3
          h-1
          w-8
          rounded-full
          bg-[#EAB308]
        "
      />


      <p
        className="
          text-sm
          text-slate-500
        "
      >
        {label}
      </p>


      <p
        className="
          mt-1
          text-2xl
          font-bold
          text-[#115E59]
        "
      >
        {value}
      </p>

    </div>

  );

}


function BaselineResult({
  label,
  value,
}: CardProps) {

  return (

    <div
      className="
        rounded-lg
        bg-white
        p-4
      "
    >

      <p
        className="
          text-xs
          text-slate-500
        "
      >
        {label}
      </p>


      <p
        className="
          mt-1
          text-xl
          font-bold
          text-[#115E59]
        "
      >
        {value}
      </p>

    </div>

  );

}