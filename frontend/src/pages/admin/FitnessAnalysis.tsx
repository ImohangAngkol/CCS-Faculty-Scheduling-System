import {
  useNavigate,
} from "react-router-dom";

import {
  useGA,
} from "../../context/GAContext";

import {
  formatFacultyName,
} from "../../components/schedule/WeeklySchedule";

import type {
  FacultyAnalysisItem,
  FacultyDailyLoad,
} from "../../types/ga";


export default function FitnessAnalysis() {

  const navigate =
    useNavigate();


  const {
    gaData,
  } = useGA();


  // ==========================================================
  // EMPTY
  // ==========================================================

  if (!gaData) {

    return (

      <div className="space-y-6">

        <div>

          <h1 className="text-2xl font-bold text-slate-900">
            Genetic Algorithm Analysis
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Analyze the performance of the
            generated faculty schedule.
          </p>

        </div>


        <div
          className="
            rounded-xl
            border
            bg-white
            p-10
            text-center
            shadow-sm
          "
        >

          <div
            className="
              mx-auto
              flex
              h-12
              w-12
              items-center
              justify-center
              rounded-full
              bg-[#CCFBF1]
              text-xl
            "
          >
            📊
          </div>


          <h2
            className="
              mt-4
              text-lg
              font-semibold
              text-slate-900
            "
          >
            No GA analysis available
          </h2>


          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            Generate a schedule first to
            view its analysis.
          </p>


          <button
            onClick={
              () =>
                navigate(
                  "/admin/generate"
                )
            }
            className="ccs-btn-primary mt-5"
          >
            Generate Schedule
          </button>

        </div>

      </div>

    );

  }


  const facultyAnalysis =
    gaData.faculty_analysis;


  const faculty =
    facultyAnalysis?.faculty ?? [];


  const dailyLoad =
    facultyAnalysis?.daily_load ?? [];


  // ==========================================================
  // GENERATION DATA
  // ==========================================================

  const generationData =
    gaData.history.map(
      (item) => {

        const generationBest =
          item.generation === 0

            ? (
                item.best_fitness ??
                item.generation_best_fitness ??
                item.best_ever_fitness ??
                0
              )

            : (
                item.generation_best_fitness ??
                item.best_fitness ??
                item.best_ever_fitness ??
                0
              );


        const bestEver =
          item.generation === 0

            ? generationBest

            : (
                item.best_ever_fitness ??
                generationBest
              );


        return {
          generation:
            item.generation,

          generationBest,

          bestEver,
        };

      }
    );


  const initialFitness =
    generationData.length > 0

      ? generationData[0]
          .bestEver

      : gaData.best_fitness;


  const fitnessImprovement =
    Math.max(
      0,

      initialFitness -
      gaData.best_fitness
    );


  const improvementPercent =
    initialFitness > 0

      ? (
          fitnessImprovement /
          initialFitness
        ) * 100

      : 0;


  const averageLoad =
    facultyAnalysis
      ?.summary
      ?.average_teaching_load ??
    0;


  return (

    <div className="space-y-6">

      {/* ==================================================== */}
      {/* HEADER */}
      {/* ==================================================== */}

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

          <h1
            className="
              text-2xl
              font-bold
              text-slate-900
            "
          >
            Genetic Algorithm Analysis
          </h1>


          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Faculty preference satisfaction,
            workload distribution, and optimization
            performance of the best chromosome.
          </p>

        </div>


        <button
          onClick={
            () =>
              navigate(
                "/admin/schedules"
              )
          }
          className="ccs-btn-primary"
        >
          View Generated Schedule
        </button>

      </div>


      {/* ==================================================== */}
      {/* TOP CARDS */}
      {/* ==================================================== */}

      <div
        className="
          grid
          gap-4
          md:grid-cols-2
          xl:grid-cols-4
        "
      >

        <AnalysisCard
          label="Best Fitness"
          value={
            gaData.best_fitness
          }
          description="Lower is better"
        />


        <AnalysisCard
          label="Initial Fitness"
          value={
            initialFitness
          }
          description="Initial best chromosome"
        />


        <AnalysisCard
          label="Improvement"
          value={
            fitnessImprovement
          }
          description={
            `${improvementPercent.toFixed(
              2
            )}% reduction`
          }
        />


        <AnalysisCard
          label="Average Teaching Load"
          value={
            Number(
              averageLoad
            ).toFixed(1)
          }
          description="Credit units"
        />

      </div>


      {/* ==================================================== */}
      {/* OPTIMIZATION PROGRESS */}
      {/* ==================================================== */}

      <section className="analysis-section">

        <SectionHeader
          title="Optimization Progress"
          description={
            "Tracks how the best fitness changes across generations. Lower values indicate improvement."
          }
        />


        <div className="mt-6">

          <FitnessTrendChart
            data={
              generationData
            }
          />

        </div>

      </section>


      {/* ==================================================== */}
      {/* PREFERENCE SATISFACTION */}
      {/* ==================================================== */}

      <section className="analysis-section">

        <SectionHeader
          title="Faculty Preference Satisfaction"
          description={
            "These percentages are calculated by the existing Python faculty-analysis logic for the selected best chromosome."
          }
        />


        <div
          className="
            mt-6
            space-y-6
          "
        >

          {faculty.map(
            (item) => (

              <FacultyPreferenceRow
                key={
                  String(
                    item.Faculty_Code
                  )
                }
                item={item}
              />

            )
          )}

        </div>

      </section>


      {/* ==================================================== */}
      {/* PREPARATIONS */}
      {/* ==================================================== */}

      <section className="analysis-section">

        <SectionHeader
          title="Number of Preparations per Faculty"
          description={
            "A preparation represents one unique subject assigned to a faculty member."
          }
        />


        <div
          className="
            mt-6
            grid
            gap-3
            sm:grid-cols-2
            lg:grid-cols-3
            xl:grid-cols-4
          "
        >

          {faculty.map(
            (item) => (

              <div
                key={
                  String(
                    item.Faculty_Code
                  )
                }
                className="
                  rounded-xl
                  border
                  border-slate-200
                  bg-slate-50
                  p-4
                "
              >

                <p
                  className="
                    text-sm
                    font-semibold
                    text-slate-700
                  "
                >
                  {formatFacultyName(
                    String(
                      item.Faculty_Code
                    )
                  )}
                </p>


                <p
                  className="
                    mt-2
                    text-3xl
                    font-bold
                    text-[#115E59]
                  "
                >
                  {item.Preparations}
                </p>


                <p
                  className="
                    mt-1
                    text-xs
                    text-slate-400
                  "
                >
                  unique subjects
                </p>

              </div>

            )
          )}

        </div>

      </section>


      {/* ==================================================== */}
      {/* TEACHING LOAD */}
      {/* ==================================================== */}

      <section className="analysis-section">

        <SectionHeader
          title="Teaching Load Distribution"
          description={
            "Shows assigned credit units and each faculty member's deviation from the overall average."
          }
        />


        <div
          className="
            mt-6
            space-y-4
          "
        >

          {faculty.map(
            (item) => {

              const maxLoad =
                Math.max(
                  1,

                  ...faculty.map(
                    (facultyItem) =>
                      Number(
                        facultyItem.Teaching_Load ??
                        0
                      )
                  )
                );


              const width =
                (
                  Number(
                    item.Teaching_Load ??
                    0
                  ) /
                  maxLoad
                ) * 100;


              return (

                <div
                  key={
                    String(
                      item.Faculty_Code
                    )
                  }
                >

                  <div
                    className="
                      mb-2
                      flex
                      items-end
                      justify-between
                      gap-4
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
                        {formatFacultyName(
                          String(
                            item.Faculty_Code
                          )
                        )}
                      </p>


                      <p
                        className="
                          text-xs
                          text-slate-400
                        "
                      >
                        Deviation from average:
                        {" "}
                        {formatSigned(
                          item.Load_Deviation
                        )}
                      </p>

                    </div>


                    <p
                      className="
                        text-sm
                        font-bold
                        text-[#115E59]
                      "
                    >
                      {
                        Number(
                          item.Teaching_Load ??
                          0
                        ).toFixed(1)
                      }
                      {" units"}
                    </p>

                  </div>


                  <div
                    className="
                      h-5
                      overflow-hidden
                      rounded-md
                      bg-slate-100
                    "
                  >

                    <div
                      className="
                        h-full
                        rounded-md
                        bg-[#0F766E]
                      "
                      style={{
                        width:
                          `${width}%`,
                      }}
                    />

                  </div>

                </div>

              );

            }
          )}

        </div>

      </section>


      {/* ==================================================== */}
      {/* DAILY LOAD */}
      {/* ==================================================== */}

      <section className="analysis-section">

        <SectionHeader
          title="Daily Teaching Load"
          description={
            "Scheduled teaching hours per day for each faculty member."
          }
        />


        <div
          className="
            mt-6
            overflow-x-auto
          "
        >

          <table
            className="
              w-full
              min-w-[850px]
              text-left
              text-sm
            "
          >

            <thead
              className="
                bg-[#115E59]
                text-white
              "
            >

              <tr>

                <th className="px-4 py-3">
                  Faculty
                </th>

                <th className="px-4 py-3">
                  Monday
                </th>

                <th className="px-4 py-3">
                  Tuesday
                </th>

                <th className="px-4 py-3">
                  Wednesday
                </th>

                <th className="px-4 py-3">
                  Thursday
                </th>

                <th className="px-4 py-3">
                  Friday
                </th>

                <th className="px-4 py-3">
                  Saturday
                </th>

                <th className="px-4 py-3">
                  Total
                </th>

              </tr>

            </thead>


            <tbody>

              {dailyLoad.map(
                (item) => (

                  <DailyLoadRow
                    key={
                      String(
                        item.Faculty_Code
                      )
                    }
                    item={item}
                  />

                )
              )}

            </tbody>

          </table>

        </div>

      </section>


      {/* ==================================================== */}
      {/* FACULTY SUMMARY */}
      {/* ==================================================== */}

      <section
        className="
          overflow-hidden
          rounded-xl
          border
          bg-white
          shadow-sm
        "
      >

        <div className="p-6">

          <SectionHeader
            title="Faculty Performance Summary"
            description={
              "Combined preference satisfaction, preparations, load, and fitness penalty for the selected chromosome."
            }
          />

        </div>


        <div className="overflow-x-auto">

          <table
            className="
              w-full
              min-w-[1200px]
              text-left
              text-sm
            "
          >

            <thead
              className="
                bg-[#115E59]
                text-white
              "
            >

              <tr>

                <th className="px-4 py-3">
                  Faculty
                </th>

                <th className="px-4 py-3">
                  Priority
                </th>

                <th className="px-4 py-3">
                  Subject %
                </th>

                <th className="px-4 py-3">
                  Day %
                </th>

                <th className="px-4 py-3">
                  Time %
                </th>

                <th className="px-4 py-3">
                  Prep
                </th>

                <th className="px-4 py-3">
                  Load
                </th>

                <th className="px-4 py-3">
                  Load Δ
                </th>

                <th className="px-4 py-3">
                  Subject Penalty
                </th>

                <th className="px-4 py-3">
                  Day Penalty
                </th>

                <th className="px-4 py-3">
                  Time Penalty
                </th>

                <th className="px-4 py-3">
                  Prep Penalty
                </th>

                <th className="px-4 py-3">
                  Total Penalty
                </th>

              </tr>

            </thead>


            <tbody>

              {faculty.map(
                (item) => (

                  <tr
                    key={
                      String(
                        item.Faculty_Code
                      )
                    }
                    className="
                      border-b
                      last:border-0
                      hover:bg-[#F0FDFA]
                    "
                  >

                    <td
                      className="
                        px-4
                        py-3
                        font-semibold
                        text-[#115E59]
                      "
                    >
                      {formatFacultyName(
                        String(
                          item.Faculty_Code
                        )
                      )}
                    </td>


                    <td className="px-4 py-3">
                      {formatNullable(
                        item.Faculty_Priority
                      )}
                    </td>


                    <td className="px-4 py-3">
                      {formatPercent(
                        item.Subject_Satisfaction
                      )}
                    </td>


                    <td className="px-4 py-3">
                      {formatPercent(
                        item.Day_Satisfaction
                      )}
                    </td>


                    <td className="px-4 py-3">
                      {formatPercent(
                        item.Time_Satisfaction
                      )}
                    </td>


                    <td className="px-4 py-3">
                      {item.Preparations}
                    </td>


                    <td className="px-4 py-3">
                      {
                        Number(
                          item.Teaching_Load ??
                          0
                        ).toFixed(1)
                      }
                    </td>


                    <td className="px-4 py-3">
                      {formatSigned(
                        item.Load_Deviation
                      )}
                    </td>


                    <td className="px-4 py-3">
                      {item.Subject_Penalty}
                    </td>


                    <td className="px-4 py-3">
                      {item.Day_Penalty}
                    </td>


                    <td className="px-4 py-3">
                      {item.Time_Penalty}
                    </td>


                    <td className="px-4 py-3">
                      {item.Preparation_Penalty}
                    </td>


                    <td
                      className="
                        px-4
                        py-3
                        font-bold
                        text-[#9D174D]
                      "
                    >
                      {item.Total_Penalty}
                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </section>


      {/* ==================================================== */}
      {/* GENERATION HISTORY */}
      {/* ==================================================== */}

      <section
        className="
          overflow-hidden
          rounded-xl
          border
          bg-white
          shadow-sm
        "
      >

        <div className="p-6">

          <SectionHeader
            title="Generation History"
            description={
              "Best chromosome fitness recorded during every generation."
            }
          />

        </div>


        <div className="overflow-x-auto">

          <table
            className="
              w-full
              text-left
              text-sm
            "
          >

            <thead
              className="
                bg-[#115E59]
                text-white
              "
            >

              <tr>

                <th className="px-4 py-3">
                  Generation
                </th>

                <th className="px-4 py-3">
                  Generation Best
                </th>

                <th className="px-4 py-3">
                  Best Ever
                </th>

              </tr>

            </thead>


            <tbody>

              {generationData.map(
                (item) => (

                  <tr
                    key={
                      item.generation
                    }
                    className="
                      border-b
                      last:border-0
                      hover:bg-[#F0FDFA]
                    "
                  >

                    <td className="px-4 py-3">
                      {item.generation}
                    </td>


                    <td className="px-4 py-3">
                      {item.generationBest}
                    </td>


                    <td
                      className="
                        px-4
                        py-3
                        font-semibold
                        text-[#115E59]
                      "
                    >
                      {item.bestEver}
                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      </section>

    </div>

  );

}


/* ==========================================================
   PREFERENCE ROW
========================================================== */

function FacultyPreferenceRow({
  item,
}: {
  item: FacultyAnalysisItem;
}) {

  return (

    <div
      className="
        rounded-xl
        border
        border-slate-200
        bg-slate-50
        p-4
      "
    >

      <div
        className="
          mb-4
          flex
          items-center
          justify-between
        "
      >

        <div>

          <p
            className="
              font-semibold
              text-slate-900
            "
          >
            {formatFacultyName(
              String(
                item.Faculty_Code
              )
            )}
          </p>


          <p
            className="
              text-xs
              text-slate-400
            "
          >
            Priority{" "}
            {formatNullable(
              item.Faculty_Priority
            )}
          </p>

        </div>


        <div
          className="
            rounded-full
            bg-white
            px-3
            py-1
            text-xs
            font-semibold
            text-[#9D174D]
          "
        >
          Penalty {item.Total_Penalty}
        </div>

      </div>


      <PreferenceBar
        label="Subject Preference"
        value={
          item.Subject_Satisfaction
        }
      />


      <PreferenceBar
        label="Day Preference"
        value={
          item.Day_Satisfaction
        }
      />


      <PreferenceBar
        label="Time Preference"
        value={
          item.Time_Satisfaction
        }
      />

    </div>

  );

}


/* ==========================================================
   PREFERENCE BAR
========================================================== */

function PreferenceBar({
  label,
  value,
}: {
  label: string;
  value: number | null;
}) {

  const safeValue =
    value ?? 0;


  return (

    <div className="mb-3 last:mb-0">

      <div
        className="
          mb-1
          flex
          justify-between
          text-xs
        "
      >

        <span className="text-slate-600">
          {label}
        </span>


        <span
          className="
            font-semibold
            text-[#115E59]
          "
        >
          {formatPercent(
            value
          )}
        </span>

      </div>


      <div
        className="
          h-2.5
          overflow-hidden
          rounded-full
          bg-slate-200
        "
      >

        <div
          className="
            h-full
            rounded-full
            bg-[#0F766E]
          "
          style={{
            width:
              `${Math.min(
                100,
                Math.max(
                  0,
                  safeValue
                )
              )}%`,
          }}
        />

      </div>

    </div>

  );

}


/* ==========================================================
   DAILY LOAD ROW
========================================================== */

function DailyLoadRow({
  item,
}: {
  item: FacultyDailyLoad;
}) {

  const total =
    Number(item.Mon ?? 0) +
    Number(item.Tue ?? 0) +
    Number(item.Wed ?? 0) +
    Number(item.Thu ?? 0) +
    Number(item.Fri ?? 0) +
    Number(item.Sat ?? 0);


  return (

    <tr
      className="
        border-b
        last:border-0
        hover:bg-[#F0FDFA]
      "
    >

      <td
        className="
          px-4
          py-3
          font-semibold
          text-[#115E59]
        "
      >
        {formatFacultyName(
          String(
            item.Faculty_Code
          )
        )}
      </td>


      <DailyCell
        value={item.Mon}
      />

      <DailyCell
        value={item.Tue}
      />

      <DailyCell
        value={item.Wed}
      />

      <DailyCell
        value={item.Thu}
      />

      <DailyCell
        value={item.Fri}
      />

      <DailyCell
        value={item.Sat}
      />


      <td
        className="
          px-4
          py-3
          font-bold
          text-slate-900
        "
      >
        {total.toFixed(1)} hrs
      </td>

    </tr>

  );

}


function DailyCell({
  value,
}: {
  value: number;
}) {

  return (

    <td className="px-4 py-3">
      {Number(
        value ?? 0
      ).toFixed(1)}
      {" hrs"}
    </td>

  );

}


/* ==========================================================
   CARDS / HEADERS
========================================================== */

type AnalysisCardProps = {
  label: string;
  value: number | string;
  description: string;
};


function AnalysisCard({
  label,
  value,
  description,
}: AnalysisCardProps) {

  return (

    <div
      className="
        rounded-xl
        border
        bg-white
        p-5
        shadow-sm
      "
    >

      <div
        className="
          mb-3
          h-1
          w-10
          rounded-full
          bg-[#EAB308]
        "
      />


      <p
        className="
          text-sm
          font-medium
          text-slate-500
        "
      >
        {label}
      </p>


      <p
        className="
          mt-2
          text-3xl
          font-bold
          text-[#115E59]
        "
      >
        {value}
      </p>


      <p
        className="
          mt-1
          text-xs
          text-slate-400
        "
      >
        {description}
      </p>

    </div>

  );

}


function SectionHeader({
  title,
  description,
}: {
  title: string;
  description: string;
}) {

  return (

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
        {title}
      </h2>


      <p
        className="
          mt-1
          text-sm
          text-slate-500
        "
      >
        {description}
      </p>

    </div>

  );

}


/* ==========================================================
   FITNESS TREND CHART
========================================================== */

type ChartData = {
  generation: number;
  generationBest: number;
  bestEver: number;
};


function FitnessTrendChart({
  data,
}: {
  data: ChartData[];
}) {

  if (
    data.length === 0
  ) {

    return (

      <div
        className="
          flex
          h-60
          items-center
          justify-center
          rounded-lg
          bg-slate-50
          text-sm
          text-slate-500
        "
      >
        No generation history available.
      </div>

    );

  }


  const width = 1000;
  const height = 300;

  const left = 70;
  const right = 30;
  const top = 30;
  const bottom = 50;


  const values =
    data.flatMap(
      (item) => [
        item.generationBest,
        item.bestEver,
      ]
    );


  const maximum =
    Math.max(
      ...values
    );


  const minimum =
    Math.min(
      ...values
    );


  const range =
    Math.max(
      1,
      maximum -
      minimum
    );


  function getX(
    index: number
  ) {

    if (
      data.length === 1
    ) {
      return width / 2;
    }


    return (
      left +
      (
        index /
        (
          data.length -
          1
        )
      ) *
      (
        width -
        left -
        right
      )
    );

  }


  function getY(
    value: number
  ) {

    return (
      top +
      (
        (
          maximum -
          value
        ) /
        range
      ) *
      (
        height -
        top -
        bottom
      )
    );

  }


  const generationPoints =
    data
      .map(
        (
          item,
          index
        ) =>
          `${getX(
            index
          )},${getY(
            item.generationBest
          )}`
      )
      .join(" ");


  const bestEverPoints =
    data
      .map(
        (
          item,
          index
        ) =>
          `${getX(
            index
          )},${getY(
            item.bestEver
          )}`
      )
      .join(" ");


  return (

    <div
      className="
        overflow-x-auto
        rounded-lg
        border
        bg-slate-50
        p-3
      "
    >

      <svg
        viewBox={
          `0 0 ${width} ${height}`
        }
        className="
          h-auto
          min-w-[700px]
          w-full
        "
      >

        <line
          x1={left}
          y1={top}
          x2={left}
          y2={
            height -
            bottom
          }
          stroke="#CBD5E1"
        />


        <line
          x1={left}
          y1={
            height -
            bottom
          }
          x2={
            width -
            right
          }
          y2={
            height -
            bottom
          }
          stroke="#CBD5E1"
        />


        <polyline
          points={
            generationPoints
          }
          fill="none"
          stroke="#94A3B8"
          strokeWidth="3"
        />


        <polyline
          points={
            bestEverPoints
          }
          fill="none"
          stroke="#0F766E"
          strokeWidth="4"
        />


        {data.map(
          (
            item,
            index
          ) => (

            <g
              key={
                item.generation
              }
            >

              <circle
                cx={
                  getX(index)
                }
                cy={
                  getY(
                    item.bestEver
                  )
                }
                r="5"
                fill="#0F766E"
              />


              <text
                x={
                  getX(index)
                }
                y={
                  height - 20
                }
                textAnchor="middle"
                fontSize="12"
                fill="#64748B"
              >
                {item.generation}
              </text>

            </g>

          )
        )}


        <text
          x={10}
          y={
            top + 5
          }
          fontSize="12"
          fill="#64748B"
        >
          {maximum}
        </text>


        <text
          x={10}
          y={
            height -
            bottom
          }
          fontSize="12"
          fill="#64748B"
        >
          {minimum}
        </text>

      </svg>

    </div>

  );

}


/* ==========================================================
   FORMATTERS
========================================================== */

function formatPercent(
  value:
    number | null
) {

  if (
    value === null ||
    value === undefined
  ) {
    return "N/A";
  }


  return (
    `${Number(
      value
    ).toFixed(0)}%`
  );

}


function formatNullable(
  value:
    number | null
) {

  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }


  return value;

}


function formatSigned(
  value:
    number | null
) {

  if (
    value === null ||
    value === undefined
  ) {
    return "—";
  }


  const numericValue =
    Number(value);


  if (
    numericValue > 0
  ) {

    return (
      `+${numericValue.toFixed(
        1
      )}`
    );

  }


  return numericValue.toFixed(
    1
  );

}