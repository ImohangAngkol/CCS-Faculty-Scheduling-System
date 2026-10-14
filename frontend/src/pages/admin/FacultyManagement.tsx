import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import WeeklySchedule from "../../components/schedule/WeeklySchedule";
import { formatFacultyName } from "../../components/schedule/facultyDisplay";

import {
  useGA,
} from "../../context/GAContext";

import type {
  ScheduleEntry,
} from "../../types/ga";


export default function FacultyManagement() {

  const navigate =
    useNavigate();


  const {
    gaData,
    loading,
  } = useGA();


  const schedule =
    gaData?.schedule ?? [];


  /* =====================================================
     FACULTY LIST
  ===================================================== */

  const facultyOptions =
    useMemo(() => {

      return [
        ...new Set(
          schedule
            .map(
              (entry) =>
                String(
                  entry.faculty
                )
            )
            .filter(Boolean)
        ),
      ].sort(
        (
          first,
          second
        ) =>
          first.localeCompare(
            second,
            undefined,
            {
              numeric: true,
            }
          )
      );

    }, [
      schedule,
    ]);


  const [
    selectedFaculty,
    setSelectedFaculty,
  ] = useState("");


  useEffect(() => {

    if (
      facultyOptions.length === 0
    ) {

      setSelectedFaculty("");

      return;
    }


    if (
      !facultyOptions.includes(
        selectedFaculty
      )
    ) {

      setSelectedFaculty(
        facultyOptions[0]
      );

    }

  }, [
    facultyOptions,
    selectedFaculty,
  ]);


  /* =====================================================
     SELECTED FACULTY SCHEDULE
  ===================================================== */

  const facultySchedule =
    useMemo(
      () =>
        schedule.filter(
          (entry) =>
            String(
              entry.faculty
            ) ===
            selectedFaculty
        ),
      [
        schedule,
        selectedFaculty,
      ]
    );


  /* =====================================================
     SUMMARY
  ===================================================== */

  const uniqueSubjects =
    new Set(
      facultySchedule.map(
        (entry) =>
          entry.subject
      )
    ).size;


  const uniqueRooms =
    new Set(
      facultySchedule
        .map(
          (entry) =>
            entry.room
        )
        .filter(Boolean)
    ).size;


  const teachingHours =
    calculateTotalHours(
      facultySchedule
    );


  /* =====================================================
     NO GENERATED SCHEDULE
  ===================================================== */

  if (!gaData) {

    return (

      <div className="space-y-6">

        <PageHeader />


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
            👨‍🏫
          </div>


          <h2
            className="
              mt-4
              text-lg
              font-semibold
              text-slate-900
            "
          >
            No faculty schedule available
          </h2>


          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            Generate a schedule first to view
            each faculty member's weekly class schedule.
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

      <PageHeader />


      {/* ================================================= */}
      {/* FACULTY SELECTOR */}
      {/* ================================================= */}

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
            flex
            flex-col
            gap-4
            lg:flex-row
            lg:items-end
            lg:justify-between
          "
        >

          <div
            className="
              w-full
              max-w-md
            "
          >

            <label
              className="
                text-sm
                font-semibold
                text-slate-700
              "
            >
              Select Faculty
            </label>


            <select
              value={
                selectedFaculty
              }

              onChange={
                (event) =>
                  setSelectedFaculty(
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
                bg-white
                px-3
                py-2.5
                text-sm
                text-slate-900
              "
            >

              {facultyOptions.map(
                (faculty) => (

                  <option
                    key={faculty}
                    value={faculty}
                  >
                    {formatFacultyName(
                      faculty
                    )}
                  </option>

                )
              )}

            </select>

          </div>


          <button
            onClick={
              () =>
                navigate(
                  "/admin/generate"
                )
            }
            disabled={loading}
            className="ccs-btn-secondary"
          >
            Generate New Schedule
          </button>

        </div>

      </div>


      {/* ================================================= */}
      {/* SELECTED FACULTY */}
      {/* ================================================= */}

      <div>

        <p
          className="
            text-sm
            font-medium
            text-[#0F766E]
          "
        >
          Selected Faculty
        </p>


        <h2
          className="
            mt-1
            text-2xl
            font-bold
            text-slate-900
          "
        >
          {formatFacultyName(
            selectedFaculty
          )}
        </h2>

      </div>


      {/* ================================================= */}
      {/* SUMMARY */}
      {/* ================================================= */}

      <div
        className="
          grid
          gap-4
          sm:grid-cols-2
          xl:grid-cols-4
        "
      >

        <SummaryCard
          label="Class Meetings"
          value={
            facultySchedule.length
          }
        />


        <SummaryCard
          label="Preparations"
          value={
            uniqueSubjects
          }
        />


        <SummaryCard
          label="Teaching Hours"
          value={
            `${teachingHours.toFixed(
              1
            )} hrs`
          }
        />


        <SummaryCard
          label="Rooms Used"
          value={
            uniqueRooms
          }
        />

      </div>


      {/* ================================================= */}
      {/* WEEKLY SCHEDULE */}
      {/* ================================================= */}

      <div>

        <div
          className="
            mb-4
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
            Weekly Class Schedule
          </h2>


          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Subject code, subject name, section,
            room, and class type are shown inside
            each scheduled block.
          </p>

        </div>


        <WeeklySchedule
          entries={
            facultySchedule
          }
          viewMode="faculty"
          emptyMessage="This faculty member has no scheduled classes."
        />

      </div>

    </div>

  );

}


/* =========================================================
   PAGE HEADER
========================================================= */

function PageHeader() {

  return (

    <div>

      <h1
        className="
          text-2xl
          font-bold
          text-slate-900
        "
      >
        Faculty Management
      </h1>


      <p
        className="
          mt-1
          text-sm
          text-slate-500
        "
      >
        View the complete weekly teaching schedule
        of each faculty member.
      </p>

    </div>

  );
}


/* =========================================================
   SUMMARY CARD
========================================================= */

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


/* =========================================================
   HOURS
========================================================= */

function calculateTotalHours(
  entries: ScheduleEntry[]
) {

  const minutes =
    entries.reduce(
      (
        total,
        entry
      ) => {

        const start =
          parseMinutes(
            entry.start
          );

        const end =
          parseMinutes(
            entry.end
          );


        if (
          start === null ||
          end === null ||
          end <= start
        ) {

          return total;

        }


        return (
          total +
          (
            end -
            start
          )
        );

      },
      0
    );


  return (
    minutes / 60
  );
}


function parseMinutes(
  value: string
) {

  const cleaned =
    value
      ?.trim()
      .toUpperCase()
      .replace(/\s+/g, "");


  const match =
    cleaned?.match(
      /^(\d{1,2}):(\d{2})(AM|PM)?$/
    );


  if (!match) {
    return null;
  }


  let hour =
    Number(
      match[1]
    );

  const minute =
    Number(
      match[2]
    );

  const period =
    match[3];


  if (
    period === "AM" &&
    hour === 12
  ) {

    hour = 0;

  }


  if (
    period === "PM" &&
    hour !== 12
  ) {

    hour += 12;

  }


  return (
    hour * 60 +
    minute
  );
}
