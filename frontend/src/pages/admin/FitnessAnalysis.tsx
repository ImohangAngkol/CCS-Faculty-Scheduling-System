import {
  useNavigate,
} from "react-router-dom";

import {
  useGA,
} from "../../context/GAContext";


export default function FitnessAnalysis() {

  const navigate =
    useNavigate();

  const {
    gaData,
  } = useGA();


  if (!gaData) {

    return (
      <div className="space-y-6">

        <div>
          <h1
            className="
              text-2xl
              font-bold
              text-slate-900
            "
          >
            GA Analysis
          </h1>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Analyze Genetic Algorithm fitness
            and optimization performance.
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
            Run the Genetic Algorithm first
            to generate analysis data.
          </p>


          <button
            onClick={() =>
              navigate(
                "/admin/generate"
              )
            }
            className="
              ccs-btn-primary
              mt-5
            "
          >
            Generate Schedule
          </button>

        </div>

      </div>
    );
  }


  const chartData =
    (gaData.history ?? []).map(
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
    chartData.length > 0
      ? chartData[0].bestEver
      : gaData.best_fitness;


  const finalFitness =
    gaData.best_fitness;


  const fitnessImprovement =
    Math.max(
      0,
      initialFitness -
        finalFitness
    );


  const improvementPercentage =
    initialFitness > 0
      ? (
          fitnessImprovement /
          initialFitness
        ) * 100
      : 0;


  const fitnessBreakdown = [
    {
      label:
        "Subject Preference",

      value:
        gaData
          .fitness_breakdown
          .subject_preference,
    },

    {
      label:
        "Time Preference",

      value:
        gaData
          .fitness_breakdown
          .time_preference,
    },

    {
      label:
        "Day Preference",

      value:
        gaData
          .fitness_breakdown
          .day_preference,
    },

    {
      label:
        "Number of Preparations",

      value:
        gaData
          .fitness_breakdown
          .number_of_preparations,
    },

    {
      label:
        "Teaching Load Balance",

      value:
        gaData
          .fitness_breakdown
          .teaching_load_balance,
    },

    {
      label:
        "Daily Teaching Load",

      value:
        gaData
          .fitness_breakdown
          .daily_teaching_load,
    },
  ];


  const totalPenalty =
    fitnessBreakdown.reduce(
      (
        total,
        item
      ) =>
        total +
        item.value,
      0
    );


  return (
    <div className="space-y-6">

      {/* HEADER */}

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
            Fitness performance and penalty analysis
            of the latest GA run.
          </p>
        </div>


        <button
          onClick={() =>
            navigate(
              "/admin/schedules"
            )
          }
          className="ccs-btn-primary"
        >
          View Schedule
        </button>

      </div>


      {/* SUMMARY */}

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
          description="Starting best chromosome"
        />

        <AnalysisCard
          label="Fitness Improvement"
          value={
            fitnessImprovement
          }
          description={
            `${improvementPercentage.toFixed(
              2
            )}% reduction`
          }
        />

        <AnalysisCard
          label="Generations"
          value={
            gaData
              .generations_completed
          }
          description="Completed generations"
        />

      </div>


      {/* CHART */}

      <div
        className="
          rounded-xl
          border
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
            Fitness Progress
          </h2>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Lower fitness represents
            a better chromosome.
          </p>

        </div>


        <div className="mt-6">

          <FitnessTrendChart
            data={chartData}
          />

        </div>

      </div>


      {/* BREAKDOWN */}

      <div
        className="
          rounded-xl
          border
          bg-white
          p-6
          shadow-sm
        "
      >

        <h2
          className="
            text-lg
            font-semibold
            text-slate-900
          "
        >
          Fitness Penalty Breakdown
        </h2>

        <p
          className="
            mt-1
            text-sm
            text-slate-500
          "
        >
          Contribution of each soft constraint
          to the final fitness score.
        </p>


        <div
          className="
            mt-6
            space-y-5
          "
        >

          {fitnessBreakdown.map(
            (item) => {

              const percentage =
                totalPenalty > 0
                  ? (
                      item.value /
                      totalPenalty
                    ) * 100
                  : 0;


              return (
                <div
                  key={item.label}
                >

                  <div
                    className="
                      mb-2
                      flex
                      items-center
                      justify-between
                    "
                  >

                    <span
                      className="
                        text-sm
                        font-medium
                        text-slate-700
                      "
                    >
                      {item.label}
                    </span>


                    <div>
                      <span
                        className="
                          text-sm
                          font-semibold
                          text-[#115E59]
                        "
                      >
                        {item.value}
                      </span>

                      <span
                        className="
                          ml-2
                          text-xs
                          text-slate-400
                        "
                      >
                        {percentage.toFixed(
                          1
                        )}
                        %
                      </span>
                    </div>

                  </div>


                  <div
                    className="
                      h-3
                      overflow-hidden
                      rounded-full
                      bg-teal-50
                    "
                  >

                    <div
                      className="
                        h-full
                        rounded-full
                        bg-[#0F766E]
                        transition-all
                      "
                      style={{
                        width:
                          `${percentage}%`,
                      }}
                    />

                  </div>

                </div>
              );

            }
          )}

        </div>


        <div
          className="
            mt-6
            border-t
            pt-4
          "
        >

          <div
            className="
              flex
              items-center
              justify-between
            "
          >

            <span
              className="
                text-sm
                font-medium
                text-slate-600
              "
            >
              Total Penalty
            </span>

            <span
              className="
                text-xl
                font-bold
                text-[#115E59]
              "
            >
              {totalPenalty}
            </span>

          </div>

        </div>

      </div>


      {/* HISTORY */}

      <div
        className="
          rounded-xl
          border
          bg-white
          p-6
          shadow-sm
        "
      >

        <h2
          className="
            text-lg
            font-semibold
            text-slate-900
          "
        >
          Generation History
        </h2>


        <div
          className="
            mt-5
            overflow-x-auto
          "
        >

          <table
            className="
              w-full
              text-left
              text-sm
            "
          >

            <thead
              className="
                border-b
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

                <th className="px-4 py-3">
                  Improvement
                </th>
              </tr>
            </thead>


            <tbody>

              {chartData.map(
                (
                  item,
                  index
                ) => {

                  const previous =
                    index === 0
                      ? item.bestEver
                      : chartData[
                          index - 1
                        ].bestEver;


                  const improvement =
                    Math.max(
                      0,
                      previous -
                        item.bestEver
                    );


                  return (
                    <tr
                      key={item.generation}
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

                      <td className="px-4 py-3">

                        {improvement > 0 ? (
                          <span
                            className="
                              font-semibold
                              text-teal-700
                            "
                          >
                            -{improvement}
                          </span>
                        ) : (
                          <span
                            className="
                              text-slate-400
                            "
                          >
                            —
                          </span>
                        )}

                      </td>

                    </tr>
                  );

                }
              )}

            </tbody>

          </table>

        </div>

      </div>

    </div>
  );
}


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


type ChartItem = {
  generation: number;
  generationBest: number;
  bestEver: number;
};


function FitnessTrendChart({
  data,
}: {
  data: ChartItem[];
}) {

  if (data.length === 0) {
    return (
      <div
        className="
          flex
          h-64
          items-center
          justify-center
          rounded-lg
          bg-[#F0FDFA]
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

  const paddingLeft = 70;
  const paddingRight = 30;
  const paddingTop = 25;
  const paddingBottom = 50;


  const allValues =
    data.flatMap(
      (item) => [
        item.generationBest,
        item.bestEver,
      ]
    );


  const maxFitness =
    Math.max(
      ...allValues
    );


  const minFitness =
    Math.min(
      ...allValues
    );


  const range =
    Math.max(
      1,
      maxFitness -
        minFitness
    );


  function getX(
    index: number
  ) {

    if (data.length === 1) {
      return width / 2;
    }

    return (
      paddingLeft +
      (
        index /
        (data.length - 1)
      ) *
      (
        width -
        paddingLeft -
        paddingRight
      )
    );
  }


  function getY(
    fitness: number
  ) {

    return (
      paddingTop +
      (
        (
          maxFitness -
          fitness
        ) /
        range
      ) *
      (
        height -
        paddingTop -
        paddingBottom
      )
    );
  }


  const generationBestPoints =
    data
      .map(
        (
          item,
          index
        ) =>
          `${getX(index)},${getY(
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
          `${getX(index)},${getY(
            item.bestEver
          )}`
      )
      .join(" ");


  return (
    <div>

      <div
        className="
          mb-4
          flex
          flex-wrap
          gap-5
          text-sm
          text-slate-600
        "
      >

        <div
          className="
            flex
            items-center
            gap-2
          "
        >
          <span
            className="
              h-1
              w-6
              rounded
              bg-[#94A3B8]
            "
          />

          Generation Best
        </div>


        <div
          className="
            flex
            items-center
            gap-2
          "
        >
          <span
            className="
              h-1
              w-6
              rounded
              bg-[#0F766E]
            "
          />

          Best Ever
        </div>

      </div>


      <div
        className="
          overflow-x-auto
          rounded-lg
          border
          bg-[#F0FDFA]
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
            x1={paddingLeft}
            y1={paddingTop}
            x2={paddingLeft}
            y2={
              height -
              paddingBottom
            }
            stroke="#CBD5E1"
          />


          <line
            x1={paddingLeft}
            y1={
              height -
              paddingBottom
            }
            x2={
              width -
              paddingRight
            }
            y2={
              height -
              paddingBottom
            }
            stroke="#CBD5E1"
          />


          <text
            x={10}
            y={
              paddingTop + 5
            }
            fontSize="13"
            fill="#64748B"
          >
            {maxFitness}
          </text>


          <text
            x={10}
            y={
              height -
              paddingBottom
            }
            fontSize="13"
            fill="#64748B"
          >
            {minFitness}
          </text>


          <polyline
            points={
              generationBestPoints
            }
            fill="none"
            stroke="#94A3B8"
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
          />


          <polyline
            points={
              bestEverPoints
            }
            fill="none"
            stroke="#0F766E"
            strokeWidth="4"
            strokeLinejoin="round"
            strokeLinecap="round"
          />


          {data.map(
            (
              item,
              index
            ) => (

              <g
                key={item.generation}
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
            x={
              width / 2
            }
            y={
              height - 2
            }
            textAnchor="middle"
            fontSize="13"
            fill="#64748B"
          >
            Generation
          </text>

        </svg>

      </div>

    </div>
  );
}