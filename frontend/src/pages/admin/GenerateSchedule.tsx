import {
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  useGA,
} from "../../context/GAContext";

import GALiveConsole
  from "../../components/ga/GALiveConsole";


export default function GenerateSchedule() {

  const navigate =
    useNavigate();


  const {
    gaData,
    loading,
    error,
    elapsedSeconds,
    logs,

    populationSize: runningPopulationSize,
    generations: runningGenerations,
    freshChromosomes: runningFreshChromosomes,

    runGA,
  } = useGA();


  const [
    populationSize,
    setPopulationSize,
  ] = useState(10);


  const [
    generations,
    setGenerations,
  ] = useState(2);


  const [
    freshChromosomes,
    setFreshChromosomes,
  ] = useState(2);


  async function handleGenerate() {

    await runGA(
      populationSize,
      generations,
      freshChromosomes
    );

  }


  return (

    <div className="space-y-6">

      {/* ================================================= */}
      {/* PAGE HEADER */}
      {/* ================================================= */}

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
          Configure and run the Genetic Algorithm
          to generate a faculty schedule.
        </p>

      </div>


      {/* ================================================= */}
      {/* SETTINGS */}
      {/* ================================================= */}

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
            Adjust the parameters before
            generating a schedule.
          </p>

        </div>


        <div
          className="
            mt-6
            grid
            gap-5
            md:grid-cols-3
          "
        >

          {/* POPULATION SIZE */}

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
                bg-white
                px-3
                py-2.5
                text-slate-900
                disabled:cursor-not-allowed
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
                bg-white
                px-3
                py-2.5
                text-slate-900
                disabled:cursor-not-allowed
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
                bg-white
                px-3
                py-2.5
                text-slate-900
                disabled:cursor-not-allowed
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


        {/* GENERATE BUTTON */}

        <div className="mt-6">

          <button
            onClick={handleGenerate}
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


      {/* ================================================= */}
      {/* BIG LOADING PANEL */}
      {/* ================================================= */}

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

          {/* TOP TEAL STRIP */}

          <div
            className="
              h-1.5
              w-full
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

              {/* LEFT */}

              <div
                className="
                  flex
                  items-center
                  gap-5
                "
              >

                {/* LARGE SPINNER */}

                <div
                  className="
                    flex
                    h-16
                    w-16
                    shrink-0
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

                  <div
                    className="
                      flex
                      items-center
                      gap-2
                    "
                  >

                    <span
                      className="
                        h-2.5
                        w-2.5
                        animate-pulse
                        rounded-full
                        bg-[#0F766E]
                      "
                    />


                    <span
                      className="
                        text-xs
                        font-bold
                        uppercase
                        tracking-wider
                        text-[#0F766E]
                      "
                    >
                      Running
                    </span>

                  </div>


                  <h2
                    className="
                      mt-2
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
                      max-w-2xl
                      text-sm
                      text-slate-500
                    "
                  >
                    The system is generating populations,
                    evaluating fitness, performing crossover
                    and mutation, and searching for a better
                    faculty schedule.
                  </p>

                </div>

              </div>


              {/* ELAPSED TIME */}

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
                    font-semibold
                    uppercase
                    tracking-wider
                    text-slate-500
                  "
                >
                  Elapsed Time
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


            {/* PARAMETERS */}

            <div
              className="
                mt-6
                grid
                gap-3
                sm:grid-cols-3
              "
            >

              <RunningStat
                label="Population Size"
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


            {/* WAIT MESSAGE */}

            <div
              className="
                mt-5
                rounded-lg
                border
                border-[#EAB308]/30
                bg-[#FEFCE8]
                px-4
                py-3
              "
            >

              <p
                className="
                  text-sm
                  text-slate-700
                "
              >
                <strong>
                  Please wait.
                </strong>
                {" "}
                You may navigate to another Admin page
                while the Genetic Algorithm continues
                running in the background.
              </p>

            </div>

          </div>

        </div>

      )}


      {/* ================================================= */}
      {/* LIVE GA CONSOLE */}
      {/* ================================================= */}

      {(loading ||
        logs.length > 0) && (

        <div>

          <div className="mb-3">

            <h2
              className="
                text-lg
                font-semibold
                text-slate-900
              "
            >
              Genetic Algorithm Live Progress
            </h2>


            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Live output from the Genetic Algorithm.
            </p>

          </div>


          <GALiveConsole
            logs={logs}
            loading={loading}
          />

        </div>

      )}


      {/* ================================================= */}
      {/* ERROR */}
      {/* ================================================= */}

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


      {/* ================================================= */}
      {/* COMPLETED RESULT */}
      {/* ================================================= */}

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
              w-full
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
                    items-center
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
                  The best chromosome from the latest
                  Genetic Algorithm run is ready for review.
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


            {/* RESULT SUMMARY */}

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

          </div>

        </div>

      )}

    </div>

  );

}


/* =========================================================
   FORMAT TIMER
========================================================= */

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
    `${String(minutes).padStart(
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


/* =========================================================
   RUNNING PARAMETER CARD
========================================================= */

type RunningStatProps = {
  label: string;
  value: number | string;
};


function RunningStat({
  label,
  value,
}: RunningStatProps) {

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
          font-medium
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


/* =========================================================
   RESULT CARD
========================================================= */

function ResultCard({
  label,
  value,
}: RunningStatProps) {

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