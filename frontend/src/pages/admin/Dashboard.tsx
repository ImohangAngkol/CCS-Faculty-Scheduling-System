import {
  useGA,
} from "../../context/GAContext";


export default function Dashboard() {

  const {
    gaData,
    loading,
    error,
    elapsedSeconds,

    populationSize,
    generations,
    freshChromosomes,

    runGA,
  } = useGA();


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
            Admin Dashboard
          </h1>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Genetic Algorithm Faculty Scheduling
          </p>
        </div>


        <button
          onClick={() =>
            runGA(
              10,
              2,
              2
            )
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
            ? "Genetic Algorithm Running"
            : "Run Genetic Algorithm"}

        </button>

      </div>


      {/* RUNNING */}

      {loading && (
        <div
          className="
            rounded-xl
            border
            border-teal-200
            bg-white
            p-6
            shadow-sm
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
                h-12
                w-12
                shrink-0
                animate-spin
                rounded-full
                border-4
                border-teal-100
                border-t-[#0F766E]
              "
            />


            <div>
              <h2
                className="
                  text-lg
                  font-semibold
                  text-[#115E59]
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
                Searching for a better faculty schedule.
              </p>


              <div
                className="
                  mt-3
                  flex
                  flex-wrap
                  gap-x-5
                  gap-y-2
                  text-sm
                  text-slate-500
                "
              >

                <span>
                  Population:{" "}
                  <strong>
                    {populationSize}
                  </strong>
                </span>

                <span>
                  Generations:{" "}
                  <strong>
                    {generations}
                  </strong>
                </span>

                <span>
                  Fresh Chromosomes:{" "}
                  <strong>
                    {freshChromosomes}
                  </strong>
                </span>

                <span>
                  Elapsed:{" "}
                  <strong>
                    {elapsedSeconds}s
                  </strong>
                </span>

              </div>

            </div>

          </div>

        </div>
      )}


      {/* ERROR */}

      {error && (
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
              font-medium
              text-red-700
            "
          >
            Genetic Algorithm failed
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


      {/* EMPTY */}

      {!gaData &&
        !loading &&
        !error && (

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
                text-[#115E59]
              "
            >
              ⚙
            </div>


            <h2
              className="
                mt-4
                text-lg
                font-semibold
                text-slate-900
              "
            >
              No Genetic Algorithm run yet
            </h2>


            <p
              className="
                mt-2
                text-sm
                text-slate-500
              "
            >
              Run the Genetic Algorithm to generate
              and analyze a faculty schedule.
            </p>

          </div>

        )}


      {/* RESULTS */}

      {gaData && (
        <>

          <div
            className="
              grid
              gap-4
              md:grid-cols-2
              xl:grid-cols-4
            "
          >

            <DashboardCard
              label="Best Fitness"
              value={gaData.best_fitness}
            />

            <DashboardCard
              label="Generations"
              value={gaData.generations_completed}
            />

            <DashboardCard
              label="Population Size"
              value={gaData.population_size}
            />

            <DashboardCard
              label="Schedule Entries"
              value={gaData.schedule.length}
            />

          </div>


          {/* FITNESS BREAKDOWN */}

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
              Fitness Breakdown
            </h2>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Lower penalty values indicate
              better schedule quality.
            </p>


            <div
              className="
                mt-5
                grid
                gap-4
                md:grid-cols-2
                xl:grid-cols-3
              "
            >

              <PenaltyCard
                label="Subject Preference"
                value={
                  gaData
                    .fitness_breakdown
                    .subject_preference
                }
              />

              <PenaltyCard
                label="Time Preference"
                value={
                  gaData
                    .fitness_breakdown
                    .time_preference
                }
              />

              <PenaltyCard
                label="Day Preference"
                value={
                  gaData
                    .fitness_breakdown
                    .day_preference
                }
              />

              <PenaltyCard
                label="Preparations"
                value={
                  gaData
                    .fitness_breakdown
                    .number_of_preparations
                }
              />

              <PenaltyCard
                label="Teaching Load"
                value={
                  gaData
                    .fitness_breakdown
                    .teaching_load_balance
                }
              />

              <PenaltyCard
                label="Daily Teaching Load"
                value={
                  gaData
                    .fitness_breakdown
                    .daily_teaching_load
                }
              />

            </div>

          </div>


          {/* GENERATION HISTORY */}

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
                mt-4
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
                    bg-[#F0FDFA]
                    text-[#115E59]
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
                  {gaData.history.map(
                    (item) => (
                      <tr
                        key={item.generation}
                        className="
                          border-b
                          last:border-0
                        "
                      >

                        <td className="px-4 py-3">
                          {item.generation}
                        </td>

                        <td className="px-4 py-3">
                          {
                            item.generation === 0
                              ? item.best_fitness
                              : item
                                  .generation_best_fitness
                          }
                        </td>

                        <td
                          className="
                            px-4
                            py-3
                            font-semibold
                            text-[#115E59]
                          "
                        >
                          {
                            item.generation === 0
                              ? item.best_fitness
                              : item
                                  .best_ever_fitness
                          }
                        </td>

                      </tr>
                    )
                  )}
                </tbody>

              </table>

            </div>

          </div>


          {/* SCHEDULE */}

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
              Generated Schedule
            </h2>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Preview of the best chromosome.
            </p>


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
                    bg-[#F0FDFA]
                    text-[#115E59]
                  "
                >
                  <tr>
                    <th className="px-4 py-3">
                      Subject
                    </th>

                    <th className="px-4 py-3">
                      Section
                    </th>

                    <th className="px-4 py-3">
                      Type
                    </th>

                    <th className="px-4 py-3">
                      Faculty
                    </th>

                    <th className="px-4 py-3">
                      Day
                    </th>

                    <th className="px-4 py-3">
                      Time
                    </th>

                    <th className="px-4 py-3">
                      Room
                    </th>
                  </tr>
                </thead>


                <tbody>
                  {gaData.schedule
                    .slice(0, 10)
                    .map(
                      (
                        entry,
                        index
                      ) => (

                        <tr
                          key={
                            `${entry.subject}-` +
                            `${entry.section}-` +
                            `${entry.day}-` +
                            `${index}`
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
                              text-slate-900
                            "
                          >
                            {entry.subject}
                          </td>

                          <td className="px-4 py-3">
                            {entry.section}
                          </td>

                          <td className="px-4 py-3">
                            {entry.type}
                          </td>

                          <td className="px-4 py-3">
                            {entry.faculty}
                          </td>

                          <td className="px-4 py-3">
                            {entry.day}
                          </td>

                          <td className="px-4 py-3">
                            {entry.start}
                            {" - "}
                            {entry.end}
                          </td>

                          <td className="px-4 py-3">
                            {entry.room}
                          </td>

                        </tr>

                      )
                    )}
                </tbody>

              </table>

            </div>

          </div>

        </>
      )}

    </div>
  );
}


type CardProps = {
  label: string;
  value: number | string;
};


function DashboardCard({
  label,
  value,
}: CardProps) {

  return (
    <div
      className="
        rounded-xl
        border
        border-slate-200
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
          bg-[#0F766E]
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

    </div>
  );
}


function PenaltyCard({
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
          text-xl
          font-semibold
          text-[#115E59]
        "
      >
        {value}
      </p>

    </div>
  );
}