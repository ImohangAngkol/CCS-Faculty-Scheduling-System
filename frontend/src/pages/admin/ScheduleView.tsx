import {
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import {
  useGA,
} from "../../context/GAContext";


export default function ScheduleView() {

  const navigate =
    useNavigate();

  const {
    gaData,
    loading,
  } = useGA();


  const [
    search,
    setSearch,
  ] = useState("");


  const [
    facultyFilter,
    setFacultyFilter,
  ] = useState("All");


  const [
    dayFilter,
    setDayFilter,
  ] = useState("All");


  const [
    sectionFilter,
    setSectionFilter,
  ] = useState("All");


  const schedule =
    gaData?.schedule ?? [];


  const facultyOptions =
    useMemo(
      () =>
        [
          ...new Set(
            schedule
              .map(
                (entry) =>
                  entry.faculty
              )
              .filter(Boolean)
          ),
        ].sort(),
      [schedule]
    );


  const dayOptions =
    useMemo(
      () =>
        [
          ...new Set(
            schedule
              .map(
                (entry) =>
                  entry.day
              )
              .filter(Boolean)
          ),
        ],
      [schedule]
    );


  const sectionOptions =
    useMemo(
      () =>
        [
          ...new Set(
            schedule
              .map(
                (entry) =>
                  entry.section
              )
              .filter(Boolean)
          ),
        ].sort(),
      [schedule]
    );


  const filteredSchedule =
    useMemo(() => {

      const query =
        search
          .trim()
          .toLowerCase();


      return schedule.filter(
        (entry) => {

          const matchesSearch =
            query === "" ||
            entry.subject
              ?.toLowerCase()
              .includes(query) ||
            entry.title
              ?.toLowerCase()
              .includes(query) ||
            entry.faculty
              ?.toLowerCase()
              .includes(query) ||
            entry.room
              ?.toLowerCase()
              .includes(query) ||
            entry.section
              ?.toLowerCase()
              .includes(query);


          const matchesFaculty =
            facultyFilter === "All" ||
            entry.faculty ===
              facultyFilter;


          const matchesDay =
            dayFilter === "All" ||
            entry.day ===
              dayFilter;


          const matchesSection =
            sectionFilter === "All" ||
            entry.section ===
              sectionFilter;


          return (
            matchesSearch &&
            matchesFaculty &&
            matchesDay &&
            matchesSection
          );

        }
      );

    }, [
      schedule,
      search,
      facultyFilter,
      dayFilter,
      sectionFilter,
    ]);


  const totalFaculty =
    new Set(
      schedule
        .map(
          (entry) =>
            entry.faculty
        )
        .filter(Boolean)
    ).size;


  const totalSections =
    new Set(
      schedule
        .map(
          (entry) =>
            entry.section
        )
        .filter(Boolean)
    ).size;


  const totalRooms =
    new Set(
      schedule
        .map(
          (entry) =>
            entry.room
        )
        .filter(Boolean)
    ).size;


  function clearFilters() {
    setSearch("");
    setFacultyFilter("All");
    setDayFilter("All");
    setSectionFilter("All");
  }


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
            Generated Schedule
          </h1>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Review the schedule produced
            by the Genetic Algorithm.
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
            📅
          </div>


          <h2
            className="
              mt-4
              text-lg
              font-semibold
              text-slate-900
            "
          >
            No schedule generated yet
          </h2>


          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            Generate a schedule first
            before viewing the results.
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


  return (
    <div className="space-y-6">

      {/* HEADER */}

      <div
        className="
          flex
          flex-col
          gap-4
          lg:flex-row
          lg:items-center
          lg:justify-between
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
            Generated Schedule
          </h1>

          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Best chromosome produced by
            the latest Genetic Algorithm run.
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
            onClick={() =>
              navigate(
                "/admin/analysis"
              )
            }
            className="ccs-btn-secondary"
          >
            View GA Analysis
          </button>


          <button
            onClick={() =>
              navigate(
                "/admin/generate"
              )
            }
            disabled={loading}
            className="ccs-btn-primary"
          >
            Generate New Schedule
          </button>

        </div>

      </div>


      {/* SUMMARY */}

      <div
        className="
          grid
          gap-4
          sm:grid-cols-2
          xl:grid-cols-4
        "
      >

        <SummaryCard
          label="Schedule Entries"
          value={schedule.length}
        />

        <SummaryCard
          label="Faculty"
          value={totalFaculty}
        />

        <SummaryCard
          label="Sections"
          value={totalSections}
        />

        <SummaryCard
          label="Rooms"
          value={totalRooms}
        />

      </div>


      {/* FILTERS */}

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
            grid
            gap-4
            md:grid-cols-2
            xl:grid-cols-4
          "
        >

          <div>
            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Search
            </label>

            <input
              type="text"
              value={search}
              placeholder="Subject, faculty, room..."
              onChange={
                (event) =>
                  setSearch(
                    event.target.value
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
                py-2
                text-sm
              "
            />
          </div>


          <div>
            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Faculty
            </label>

            <select
              value={facultyFilter}
              onChange={
                (event) =>
                  setFacultyFilter(
                    event.target.value
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
                py-2
                text-sm
              "
            >

              <option value="All">
                All Faculty
              </option>

              {facultyOptions.map(
                (faculty) => (
                  <option
                    key={faculty}
                    value={faculty}
                  >
                    {faculty}
                  </option>
                )
              )}

            </select>
          </div>


          <div>
            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Day
            </label>

            <select
              value={dayFilter}
              onChange={
                (event) =>
                  setDayFilter(
                    event.target.value
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
                py-2
                text-sm
              "
            >

              <option value="All">
                All Days
              </option>

              {dayOptions.map(
                (day) => (
                  <option
                    key={day}
                    value={day}
                  >
                    {day}
                  </option>
                )
              )}

            </select>
          </div>


          <div>
            <label
              className="
                text-sm
                font-medium
                text-slate-700
              "
            >
              Section
            </label>

            <select
              value={sectionFilter}
              onChange={
                (event) =>
                  setSectionFilter(
                    event.target.value
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
                py-2
                text-sm
              "
            >

              <option value="All">
                All Sections
              </option>

              {sectionOptions.map(
                (section) => (
                  <option
                    key={section}
                    value={section}
                  >
                    {section}
                  </option>
                )
              )}

            </select>
          </div>

        </div>


        <div
          className="
            mt-4
            flex
            items-center
            justify-between
          "
        >

          <p
            className="
              text-sm
              text-slate-500
            "
          >
            Showing{" "}
            <strong>
              {filteredSchedule.length}
            </strong>{" "}
            of{" "}
            <strong>
              {schedule.length}
            </strong>{" "}
            entries
          </p>


          <button
            onClick={clearFilters}
            className="ccs-btn-text"
          >
            Clear Filters
          </button>

        </div>

      </div>


      {/* TABLE */}

      <div
        className="
          overflow-hidden
          rounded-xl
          border
          bg-white
          shadow-sm
        "
      >

        <div className="overflow-x-auto">

          <table
            className="
              w-full
              min-w-[1000px]
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
                  Subject
                </th>

                <th className="px-4 py-3">
                  Title
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

              {filteredSchedule.length > 0 ? (

                filteredSchedule.map(
                  (
                    entry,
                    index
                  ) => (

                    <tr
                      key={
                        `${entry.subject}-` +
                        `${entry.section}-` +
                        `${entry.day}-` +
                        `${entry.start}-` +
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
                          text-[#115E59]
                        "
                      >
                        {entry.subject}
                      </td>

                      <td className="px-4 py-3">
                        {entry.title}
                      </td>

                      <td className="px-4 py-3">
                        {entry.section}
                      </td>

                      <td className="px-4 py-3">
                        <span
                          className="
                            rounded-full
                            bg-[#CCFBF1]
                            px-2.5
                            py-1
                            text-xs
                            font-medium
                            text-[#115E59]
                          "
                        >
                          {entry.type}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        {entry.faculty}
                      </td>

                      <td className="px-4 py-3">
                        {entry.day}
                      </td>

                      <td
                        className="
                          whitespace-nowrap
                          px-4
                          py-3
                        "
                      >
                        {entry.start}
                        {" - "}
                        {entry.end}
                      </td>

                      <td className="px-4 py-3">
                        {entry.room}
                      </td>

                    </tr>

                  )
                )

              ) : (

                <tr>
                  <td
                    colSpan={8}
                    className="
                      px-4
                      py-10
                      text-center
                      text-slate-500
                    "
                  >
                    No schedule entries match
                    the selected filters.
                  </td>
                </tr>

              )}

            </tbody>

          </table>

        </div>

      </div>

    </div>
  );
}


type SummaryCardProps = {
  label: string;
  value: number | string;
};


function SummaryCard({
  label,
  value,
}: SummaryCardProps) {

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

    </div>
  );
}