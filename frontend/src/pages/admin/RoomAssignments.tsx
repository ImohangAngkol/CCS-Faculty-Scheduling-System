import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  useNavigate,
} from "react-router-dom";

import WeeklySchedule
  from "../../components/schedule/WeeklySchedule";

import {
  useGA,
} from "../../context/GAContext";

import type {
  ScheduleEntry,
} from "../../types/ga";


export default function RoomAssignments() {

  const navigate =
    useNavigate();


  const {
    gaData,
    loading,
  } = useGA();


  const schedule =
    gaData?.schedule ?? [];


  /* =====================================================
     ROOM LIST
  ===================================================== */

  const roomOptions =
    useMemo(() => {

      return [
        ...new Set(
          schedule
            .map(
              (entry) =>
                String(
                  entry.room
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
    selectedRoom,
    setSelectedRoom,
  ] = useState("");


  useEffect(() => {

    if (
      roomOptions.length === 0
    ) {

      setSelectedRoom("");

      return;
    }


    if (
      !roomOptions.includes(
        selectedRoom
      )
    ) {

      setSelectedRoom(
        roomOptions[0]
      );

    }

  }, [
    roomOptions,
    selectedRoom,
  ]);


  /* =====================================================
     ROOM SCHEDULE
  ===================================================== */

  const roomSchedule =
    useMemo(
      () =>
        schedule.filter(
          (entry) =>
            String(
              entry.room
            ) ===
            selectedRoom
        ),
      [
        schedule,
        selectedRoom,
      ]
    );


  const uniqueSubjects =
    new Set(
      roomSchedule.map(
        (entry) =>
          entry.subject
      )
    ).size;


  const uniqueSections =
    new Set(
      roomSchedule
        .map(
          (entry) =>
            entry.section
        )
        .filter(Boolean)
    ).size;


  const uniqueFaculty =
    new Set(
      roomSchedule
        .map(
          (entry) =>
            entry.faculty
        )
        .filter(Boolean)
    ).size;


  const occupiedHours =
    calculateTotalHours(
      roomSchedule
    );


  /* =====================================================
     NO GA SCHEDULE
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
            🏫
          </div>


          <h2
            className="
              mt-4
              text-lg
              font-semibold
              text-slate-900
            "
          >
            No room assignments available
          </h2>


          <p
            className="
              mt-2
              text-sm
              text-slate-500
            "
          >
            Generate a schedule first to view
            the weekly schedule assigned to each room.
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
      {/* ROOM SELECTOR */}
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
              Select Room
            </label>


            <select
              value={
                selectedRoom
              }

              onChange={
                (event) =>
                  setSelectedRoom(
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

              {roomOptions.map(
                (room) => (

                  <option
                    key={room}
                    value={room}
                  >
                    {room}
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
      {/* SELECTED ROOM */}
      {/* ================================================= */}

      <div>

        <p
          className="
            text-sm
            font-medium
            text-[#0F766E]
          "
        >
          Selected Room
        </p>


        <h2
          className="
            mt-1
            text-2xl
            font-bold
            text-slate-900
          "
        >
          {selectedRoom}
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
            roomSchedule.length
          }
        />


        <SummaryCard
          label="Subjects"
          value={
            uniqueSubjects
          }
        />


        <SummaryCard
          label="Sections"
          value={
            uniqueSections
          }
        />


        <SummaryCard
          label="Occupied Hours"
          value={
            `${occupiedHours.toFixed(
              1
            )} hrs`
          }
          secondary={
            `${uniqueFaculty} faculty`
          }
        />

      </div>


      {/* ================================================= */}
      {/* WEEKLY ROOM SCHEDULE */}
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
            Weekly Room Schedule
          </h2>


          <p
            className="
              mt-1
              text-sm
              text-slate-500
            "
          >
            Shows every class assigned to {selectedRoom},
            including subject name, section, faculty,
            and class type.
          </p>

        </div>


        <WeeklySchedule
          entries={
            roomSchedule
          }
          viewMode="room"
          emptyMessage="No classes are assigned to this room."
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
        Room Assignments
      </h1>


      <p
        className="
          mt-1
          text-sm
          text-slate-500
        "
      >
        View the complete weekly class schedule
        assigned to each room.
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
  secondary?: string;
};


function SummaryCard({
  label,
  value,
  secondary,
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


      {secondary && (

        <p
          className="
            mt-1
            text-xs
            text-slate-400
          "
        >
          {secondary}
        </p>

      )}

    </div>

  );

}


/* =========================================================
   HOURS
========================================================= */

function calculateTotalHours(
  entries: ScheduleEntry[]
) {

  let minutes = 0;


  for (
    const entry of entries
  ) {

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
      continue;
    }


    minutes +=
      end - start;

  }


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