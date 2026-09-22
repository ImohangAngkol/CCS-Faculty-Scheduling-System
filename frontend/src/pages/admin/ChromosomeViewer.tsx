import {
  useEffect,
  useState,
  type ChangeEvent,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  analyzeSavedBestChromosome,
  analyzeUploadedChromosome,
  getSavedBestDownloadUrl,
  getSavedBestStatus,
  uploadBaselineChromosome,
} from "../../services/gaService";

import {
  useGA,
} from "../../context/GAContext";


type SavedBestStatus = {

  exists:
    boolean;


  fitness:
    number | null;


  created_at:
    string | null;
};


type ActionLoading =
  | "saved-view"
  | "saved-baseline"
  | "uploaded-view"
  | "uploaded-baseline"
  | null;


export default function ChromosomeViewer() {

  const navigate =
    useNavigate();


  const {
    loadChromosomeData,
  } = useGA();


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


  const [
    uploadedPayload,
    setUploadedPayload,
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
    loadingAction,
    setLoadingAction,
  ] =
    useState<ActionLoading>(
      null
    );


  const [
    pageError,
    setPageError,
  ] =
    useState<string | null>(
      null
    );


  // ==========================================================
  // LOAD SAVED STATUS
  // ==========================================================

  useEffect(() => {

    async function loadStatus() {

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


    loadStatus();

  }, []);


  // ==========================================================
  // SELECT JSON FILE
  // ==========================================================

  async function handleFileChange(
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

      setPageError(
        null
      );


      const text =
        await file.text();


      const parsed =
        JSON.parse(
          text
        );


      setUploadedPayload(
        parsed
      );


      setUploadedFileName(
        file.name
      );


    } catch {

      setUploadedPayload(
        null
      );


      setUploadedFileName(
        ""
      );


      setPageError(
        "The selected file is not a valid chromosome JSON file."
      );

    }

  }


  // ==========================================================
  // VIEW SAVED BEST ONLY
  // ==========================================================

  async function handleViewSavedBest() {

    try {

      setPageError(
        null
      );


      setLoadingAction(
        "saved-view"
      );


      const response =
        await analyzeSavedBestChromosome();


      loadChromosomeData(
        response.data
      );


      navigate(
        "/admin/schedules"
      );


    } catch (error) {

      setPageError(
        error instanceof Error
          ? error.message
          : (
              "Unable to analyze saved chromosome."
            )
      );


    } finally {

      setLoadingAction(
        null
      );

    }

  }


  // ==========================================================
  // USE SAVED BEST AS GA BASELINE
  // ==========================================================

  function handleSavedBaseline() {

    /*
     * GenerateSchedule will read this once
     * and automatically select "Saved Best".
     */

    window.sessionStorage.setItem(
      "gaPreferredBaseline",
      "saved"
    );


    navigate(
      "/admin/generate"
    );

  }


  // ==========================================================
  // UPLOAD JSON TO BACKEND
  // ==========================================================

  async function uploadCurrentFile() {

    if (
      !uploadedPayload
    ) {

      throw new Error(
        "Please select a chromosome JSON file first."
      );

    }


    await uploadBaselineChromosome(
      uploadedPayload
    );

  }


  // ==========================================================
  // VIEW UPLOADED ONLY
  // ==========================================================

  async function handleViewUploaded() {

    try {

      setPageError(
        null
      );


      setLoadingAction(
        "uploaded-view"
      );


      await uploadCurrentFile();


      const response =
        await analyzeUploadedChromosome();


      loadChromosomeData(
        response.data
      );


      navigate(
        "/admin/schedules"
      );


    } catch (error) {

      setPageError(
        error instanceof Error
          ? error.message
          : (
              "Unable to analyze uploaded chromosome."
            )
      );


    } finally {

      setLoadingAction(
        null
      );

    }

  }


  // ==========================================================
  // USE UPLOAD AS GA BASELINE
  // ==========================================================

  async function handleUploadedBaseline() {

    try {

      setPageError(
        null
      );


      setLoadingAction(
        "uploaded-baseline"
      );


      await uploadCurrentFile();


      window.sessionStorage.setItem(
        "gaPreferredBaseline",
        "uploaded"
      );


      navigate(
        "/admin/generate"
      );


    } catch (error) {

      setPageError(
        error instanceof Error
          ? error.message
          : (
              "Unable to upload chromosome."
            )
      );


      setLoadingAction(
        null
      );

    }

  }


  return (

    <div className="space-y-6">

      {/* ==================================================== */}
      {/* HEADER */}
      {/* ==================================================== */}

      <div>

        <h1
          className="
            text-2xl
            font-bold
            text-slate-900
          "
        >
          Saved Chromosomes
        </h1>


        <p
          className="
            mt-1
            max-w-3xl
            text-sm
            text-slate-500
          "
        >
          Load and inspect an existing chromosome
          without running the Genetic Algorithm,
          or use it as the baseline for another
          optimization run.
        </p>

      </div>


      {/* ==================================================== */}
      {/* ERROR */}
      {/* ==================================================== */}

      {pageError && (

        <div
          className="
            rounded-xl
            border
            border-red-200
            bg-red-50
            p-4
          "
        >

          <p
            className="
              font-semibold
              text-red-700
            "
          >
            Unable to process chromosome
          </p>


          <p
            className="
              mt-1
              text-sm
              text-red-600
            "
          >
            {pageError}
          </p>

        </div>

      )}


      {/* ==================================================== */}
      {/* SAVED BEST */}
      {/* ==================================================== */}

      <section
        className="
          overflow-hidden
          rounded-xl
          border
          border-slate-200
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
              lg:flex-row
              lg:items-start
              lg:justify-between
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
                SYSTEM SAVED BEST
              </div>


              <h2
                className="
                  mt-3
                  text-xl
                  font-bold
                  text-slate-900
                "
              >
                Best Chromosome
              </h2>


              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                Best chromosome automatically saved
                by previous Genetic Algorithm runs.
              </p>

            </div>


            {savedBest.exists && (

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
                    tracking-wider
                    text-slate-500
                  "
                >
                  Saved Fitness
                </p>


                <p
                  className="
                    mt-1
                    text-3xl
                    font-bold
                    text-[#115E59]
                  "
                >
                  {savedBest.fitness}
                </p>

              </div>

            )}

          </div>


          {checkingSavedBest ? (

            <div
              className="
                mt-6
                rounded-lg
                bg-slate-50
                p-4
                text-sm
                text-slate-500
              "
            >
              Checking for saved chromosome...
            </div>

          ) : savedBest.exists ? (

            <>

              {savedBest.created_at && (

                <p
                  className="
                    mt-5
                    text-sm
                    text-slate-500
                  "
                >
                  Saved:{" "}
                  <strong>
                    {formatDate(
                      savedBest.created_at
                    )}
                  </strong>
                </p>

              )}


              <div
                className="
                  mt-6
                  flex
                  flex-wrap
                  gap-3
                "
              >

                <button
                  onClick={
                    handleViewSavedBest
                  }
                  disabled={
                    loadingAction !==
                    null
                  }
                  className="ccs-btn-primary"
                >

                  {loadingAction ===
                    "saved-view"
                    ? "Loading Results..."
                    : "View Results Only"
                  }

                </button>


                <button
                  onClick={
                    handleSavedBaseline
                  }
                  disabled={
                    loadingAction !==
                    null
                  }
                  className="ccs-btn-secondary"
                >
                  Use as GA Baseline
                </button>


                <a
                  href={
                    getSavedBestDownloadUrl()
                  }
                  className="ccs-btn-secondary"
                >
                  Download JSON
                </a>

              </div>

            </>

          ) : (

            <div
              className="
                mt-6
                rounded-lg
                border
                border-dashed
                border-slate-300
                bg-slate-50
                p-5
              "
            >

              <p
                className="
                  text-sm
                  text-slate-500
                "
              >
                No saved best chromosome exists yet.
                Generate a schedule first.
              </p>


              <button
                onClick={
                  () =>
                    navigate(
                      "/admin/generate"
                    )
                }
                className="
                  ccs-btn-primary
                  mt-4
                "
              >
                Generate Schedule
              </button>

            </div>

          )}

        </div>

      </section>


      {/* ==================================================== */}
      {/* UPLOAD */}
      {/* ==================================================== */}

      <section
        className="
          overflow-hidden
          rounded-xl
          border
          border-slate-200
          bg-white
          shadow-sm
        "
      >

        <div
          className="
            h-1.5
            bg-[#EAB308]
          "
        />


        <div className="p-6">

          <h2
            className="
              text-xl
              font-bold
              text-slate-900
            "
          >
            Upload Chromosome
          </h2>


          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Select an exported chromosome JSON file.
            You can inspect it directly or continue
            evolving it with the Genetic Algorithm.
          </p>


          <div
            className="
              mt-6
              rounded-xl
              border
              border-dashed
              border-teal-300
              bg-[#F0FDFA]
              p-5
            "
          >

            <label
              className="
                text-sm
                font-semibold
                text-slate-700
              "
            >
              Chromosome JSON File
            </label>


            <input
              type="file"
              accept=".json,application/json"
              onChange={
                handleFileChange
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
                  mt-4
                  rounded-lg
                  bg-white
                  px-4
                  py-3
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


          <div
            className="
              mt-6
              flex
              flex-wrap
              gap-3
            "
          >

            <button
              onClick={
                handleViewUploaded
              }
              disabled={
                !uploadedPayload ||
                loadingAction !==
                null
              }
              className="ccs-btn-primary"
            >

              {loadingAction ===
                "uploaded-view"
                ? "Loading Results..."
                : "View Results Only"
              }

            </button>


            <button
              onClick={
                handleUploadedBaseline
              }
              disabled={
                !uploadedPayload ||
                loadingAction !==
                null
              }
              className="ccs-btn-secondary"
            >

              {loadingAction ===
                "uploaded-baseline"
                ? "Preparing Baseline..."
                : "Use as GA Baseline"
              }

            </button>

          </div>

        </div>

      </section>


      {/* ==================================================== */}
      {/* EXPLANATION */}
      {/* ==================================================== */}

      <section
        className="
          rounded-xl
          border
          border-[#EAB308]/40
          bg-[#FEFCE8]
          p-5
        "
      >

        <h3
          className="
            font-semibold
            text-slate-900
          "
        >
          View Results Only vs. GA Baseline
        </h3>


        <div
          className="
            mt-3
            grid
            gap-4
            md:grid-cols-2
          "
        >

          <div>

            <p
              className="
                text-sm
                font-semibold
                text-slate-700
              "
            >
              View Results Only
            </p>


            <p
              className="
                mt-1
                text-sm
                leading-6
                text-slate-600
              "
            >
              Loads the chromosome, recalculates its
              fitness and analysis, and displays its
              schedules. No Genetic Algorithm generation,
              crossover, or mutation is performed.
            </p>

          </div>


          <div>

            <p
              className="
                text-sm
                font-semibold
                text-slate-700
              "
            >
              Use as GA Baseline
            </p>


            <p
              className="
                mt-1
                text-sm
                leading-6
                text-slate-600
              "
            >
              Uses the chromosome as a known-good member
              of the initial population and continues
              optimization to search for a better result.
            </p>

          </div>

        </div>

      </section>

    </div>

  );

}


/* ==========================================================
   DATE
========================================================== */

function formatDate(
  value: string
) {

  const date =
    new Date(
      value
    );


  if (
    Number.isNaN(
      date.getTime()
    )
  ) {

    return value;

  }


  return date.toLocaleString();

}