import type {
  ScheduleEntry,
} from "../../types/ga";


type WeeklyScheduleProps = {
  entries: ScheduleEntry[];

  viewMode:
    | "faculty"
    | "room";

  emptyMessage?: string;
};


const DAYS = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];


const DEFAULT_START_MINUTES =
  7 * 60 + 30;

const DEFAULT_END_MINUTES =
  21 * 60;


const ROW_HEIGHT = 38;


/* =========================================================
   TIME HELPERS
========================================================= */

function parseTimeToMinutes(
  value: string
): number | null {

  if (!value) {
    return null;
  }


  const cleaned =
    String(value)
      .trim()
      .toUpperCase()
      .replace(/\s+/g, "");


  /*
    Supports:

    7:30
    07:30
    7:30AM
    07:30AM
    13:30
    13:30:00
  */

  const match =
    cleaned.match(
      /^(\d{1,2}):(\d{2})(?::\d{2})?(AM|PM)?$/
    );


  if (!match) {
    return null;
  }


  let hour =
    Number(match[1]);

  const minute =
    Number(match[2]);

  const period =
    match[3];


  if (
    period === "AM"
  ) {

    if (hour === 12) {
      hour = 0;
    }

  }


  if (
    period === "PM"
  ) {

    if (hour !== 12) {
      hour += 12;
    }

  }


  return (
    hour * 60 +
    minute
  );
}


function formatMinutes(
  totalMinutes: number
) {

  let hour =
    Math.floor(
      totalMinutes / 60
    );

  const minute =
    totalMinutes % 60;


  const period =
    hour >= 12
      ? "PM"
      : "AM";


  hour =
    hour % 12;


  if (hour === 0) {
    hour = 12;
  }


  return (
    `${String(hour).padStart(2, "0")}:` +
    `${String(minute).padStart(2, "0")}` +
    `${period}`
  );
}


/* =========================================================
   DAY NORMALIZATION

   IMPORTANT:
   The Python GA uses:
   M, T, W, TH, F, S
========================================================= */

function normalizeDay(
  value: string
) {

  const day =
    String(
      value ?? ""
    )
      .trim()
      .toUpperCase();


  const mapping:
    Record<string, string> = {

    /* PYTHON GA CODES */

    M: "Monday",
    T: "Tuesday",
    W: "Wednesday",
    TH: "Thursday",
    F: "Friday",
    S: "Saturday",

    /* OPTIONAL ALTERNATIVE VALUES */

    MON: "Monday",
    MONDAY: "Monday",

    TUE: "Tuesday",
    TUES: "Tuesday",
    TUESDAY: "Tuesday",

    WED: "Wednesday",
    WEDNESDAY: "Wednesday",

    THU: "Thursday",
    THUR: "Thursday",
    THURS: "Thursday",
    THURSDAY: "Thursday",

    FRI: "Friday",
    FRIDAY: "Friday",

    SAT: "Saturday",
    SATURDAY: "Saturday",

    SUN: "Sunday",
    SUNDAY: "Sunday",
  };


  return (
    mapping[day] ??
    value
  );
}


/* =========================================================
   EVENT COLORS
========================================================= */

const EVENT_COLORS = [

  {
    background: "#DBEAFE",
    border: "#60A5FA",
    text: "#1E3A8A",
  },

  {
    background: "#CCFBF1",
    border: "#2DD4BF",
    text: "#134E4A",
  },

  {
    background: "#FEF3C7",
    border: "#FBBF24",
    text: "#78350F",
  },

  {
    background: "#FCE7F3",
    border: "#F472B6",
    text: "#831843",
  },

  {
    background: "#DCFCE7",
    border: "#4ADE80",
    text: "#14532D",
  },

  {
    background: "#EDE9FE",
    border: "#A78BFA",
    text: "#4C1D95",
  },

  {
    background: "#FFEDD5",
    border: "#FB923C",
    text: "#7C2D12",
  },

];


function getColor(
  subject: string
) {

  let hash = 0;


  for (
    let index = 0;
    index < subject.length;
    index++
  ) {

    hash =
      subject.charCodeAt(index) +
      (
        (hash << 5) -
        hash
      );

  }


  return (
    EVENT_COLORS[
      Math.abs(hash) %
      EVENT_COLORS.length
    ]
  );
}


/* =========================================================
   MERGED ENTRY

   Python gives us individual 30-minute TimeBlocks.

   Example:

   ITE183
   Tuesday
   7:30 - 8:00

   ITE183
   Tuesday
   8:00 - 8:30

   ITE183
   Tuesday
   8:30 - 9:00

   We combine these into:

   ITE183
   Tuesday
   7:30 - 9:00
========================================================= */

type MergedScheduleEntry =
  ScheduleEntry & {

    normalizedDay: string;

    startMinutes: number;

    endMinutes: number;

  };


function mergeScheduleEntries(
  entries: ScheduleEntry[]
): MergedScheduleEntry[] {

  const normalized:
    MergedScheduleEntry[] = [];


  /* -----------------------------------------------------
     NORMALIZE FIRST
  ----------------------------------------------------- */

  for (
    const entry of entries
  ) {

    const normalizedDay =
      normalizeDay(
        entry.day
      );


    const startMinutes =
      parseTimeToMinutes(
        entry.start
      );


    const endMinutes =
      parseTimeToMinutes(
        entry.end
      );


    if (
      !DAYS.includes(
        normalizedDay
      ) ||
      startMinutes === null ||
      endMinutes === null ||
      endMinutes <=
        startMinutes
    ) {

      continue;

    }


    normalized.push({

      ...entry,

      normalizedDay,

      startMinutes,

      endMinutes,

    });

  }


  /* -----------------------------------------------------
     SORT
  ----------------------------------------------------- */

  normalized.sort(
    (
      first,
      second
    ) => {

      const firstDay =
        DAYS.indexOf(
          first.normalizedDay
        );


      const secondDay =
        DAYS.indexOf(
          second.normalizedDay
        );


      if (
        firstDay !==
        secondDay
      ) {

        return (
          firstDay -
          secondDay
        );

      }


      if (
        first.subject !==
        second.subject
      ) {

        return (
          first.subject.localeCompare(
            second.subject
          )
        );

      }


      return (
        first.startMinutes -
        second.startMinutes
      );

    }
  );


  /* -----------------------------------------------------
     MERGE CONSECUTIVE BLOCKS
  ----------------------------------------------------- */

  const merged:
    MergedScheduleEntry[] = [];


  for (
    const entry of normalized
  ) {

    const previous =
      merged[
        merged.length - 1
      ];


    const sameClass =
      previous &&

      previous.normalizedDay ===
        entry.normalizedDay &&

      previous.subject ===
        entry.subject &&

      previous.title ===
        entry.title &&

      previous.type ===
        entry.type &&

      previous.section ===
        entry.section &&

      previous.faculty ===
        entry.faculty &&

      previous.room ===
        entry.room;


    const consecutive =
      previous &&
      previous.endMinutes ===
        entry.startMinutes;


    if (
      sameClass &&
      consecutive
    ) {

      previous.endMinutes =
        entry.endMinutes;

      previous.end =
        entry.end;

    } else {

      merged.push({
        ...entry,
      });

    }

  }


  return merged;
}


/* =========================================================
   MAIN COMPONENT
========================================================= */

export default function WeeklySchedule({
  entries,
  viewMode,
  emptyMessage =
    "No classes are scheduled for this selection.",
}: WeeklyScheduleProps) {


  /*
    This is the important part.

    Instead of rendering the raw half-hour entries,
    render merged classes.
  */

  const mergedEntries =
    mergeScheduleEntries(
      entries
    );


  /* =====================================================
     DETERMINE RANGE
  ===================================================== */

  const eventTimes =
    mergedEntries.flatMap(
      (entry) => [

        entry.startMinutes,

        entry.endMinutes,

      ]
    );


  const earliestEvent =
    eventTimes.length > 0

      ? Math.min(
          ...eventTimes
        )

      : DEFAULT_START_MINUTES;


  const latestEvent =
    eventTimes.length > 0

      ? Math.max(
          ...eventTimes
        )

      : DEFAULT_END_MINUTES;


  const startMinutes =
    Math.min(

      DEFAULT_START_MINUTES,

      Math.floor(
        earliestEvent / 30
      ) * 30

    );


  const endMinutes =
    Math.max(

      DEFAULT_END_MINUTES,

      Math.ceil(
        latestEvent / 30
      ) * 30

    );


  const slots:
    number[] = [];


  for (
    let time =
      startMinutes;

    time <
      endMinutes;

    time += 30
  ) {

    slots.push(
      time
    );

  }


  return (

    <div
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
          overflow-x-auto
        "
      >

        <div
          className="
            min-w-[1250px]
          "
        >

          {/* ================================================= */}
          {/* DAYS HEADER */}
          {/* ================================================= */}

          <div
            className="
              grid
              border-b
              bg-[#115E59]
              text-sm
              font-semibold
              text-white
            "

            style={{
              gridTemplateColumns:
                "150px repeat(7, minmax(150px, 1fr))",
            }}
          >

            <div
              className="
                border-r
                border-white/20
                px-3
                py-3
                text-center
              "
            >
              Time
            </div>


            {DAYS.map(
              (day) => (

                <div
                  key={day}

                  className="
                    border-r
                    border-white/20
                    px-3
                    py-3
                    text-center
                    last:border-r-0
                  "
                >
                  {day}
                </div>

              )
            )}

          </div>


          {/* ================================================= */}
          {/* BODY */}
          {/* ================================================= */}

          <div
            className="
              relative
              grid
            "

            style={{

              gridTemplateColumns:
                "150px repeat(7, minmax(150px, 1fr))",

              gridTemplateRows:
                `repeat(${slots.length}, ${ROW_HEIGHT}px)`,

            }}
          >

            {/* ================================================= */}
            {/* TIME COLUMN */}
            {/* ================================================= */}

            {slots.map(
              (
                slot,
                rowIndex
              ) => (

                <div
                  key={
                    `time-${slot}`
                  }

                  className="
                    flex
                    items-center
                    justify-center
                    border-b
                    border-r
                    border-slate-200
                    bg-slate-50
                    px-2
                    text-xs
                    text-slate-600
                  "

                  style={{
                    gridColumn: 1,

                    gridRow:
                      rowIndex + 1,
                  }}
                >

                  {formatMinutes(
                    slot
                  )}

                  {"-"}

                  {formatMinutes(
                    slot + 30
                  )}

                </div>

              )
            )}


            {/* ================================================= */}
            {/* EMPTY GRID */}
            {/* ================================================= */}

            {DAYS.map(
              (
                day,
                dayIndex
              ) =>

                slots.map(
                  (
                    slot,
                    rowIndex
                  ) => (

                    <div
                      key={
                        `${day}-${slot}`
                      }

                      className="
                        border-b
                        border-r
                        border-slate-200
                        bg-white
                      "

                      style={{

                        gridColumn:
                          dayIndex + 2,

                        gridRow:
                          rowIndex + 1,

                      }}
                    />

                  )
                )
            )}


            {/* ================================================= */}
            {/* CLASSES */}
            {/* ================================================= */}

            {mergedEntries.map(
              (
                entry,
                index
              ) => {

                const dayIndex =
                  DAYS.indexOf(
                    entry.normalizedDay
                  );


                if (
                  dayIndex === -1
                ) {
                  return null;
                }


                const startRow =
                  Math.floor(
                    (
                      entry.startMinutes -
                      startMinutes
                    ) / 30
                  ) + 1;


                const endRow =
                  Math.ceil(
                    (
                      entry.endMinutes -
                      startMinutes
                    ) / 30
                  ) + 1;


                const color =
                  getColor(
                    entry.subject
                  );


                return (

                  <div
                    key={
                      `${entry.subject}-` +
                      `${entry.section}-` +
                      `${entry.normalizedDay}-` +
                      `${entry.startMinutes}-` +
                      `${index}`
                    }

                    className="
                      z-20
                      m-0.5
                      flex
                      flex-col
                      items-center
                      justify-center
                      overflow-hidden
                      rounded-md
                      border
                      px-2
                      py-2
                      text-center
                      shadow-sm
                    "

                    style={{

                      gridColumn:
                        dayIndex + 2,

                      gridRow:
                        `${startRow} / ${endRow}`,

                      backgroundColor:
                        color.background,

                      borderColor:
                        color.border,

                      color:
                        color.text,

                    }}
                  >

                    {/* SUBJECT CODE */}

                    <p
                      className="
                        text-xs
                        font-bold
                      "
                    >
                      {entry.subject}
                    </p>


                    {/* SUBJECT NAME */}

                    {entry.title && (

                      <p
                        className="
                          mt-1
                          line-clamp-2
                          text-[11px]
                          font-semibold
                        "
                      >
                        {entry.title}
                      </p>

                    )}


                    {/* SECTION */}

                    <p
                      className="
                        mt-1
                        text-[10px]
                      "
                    >
                      {entry.section}
                    </p>


                    {/* FACULTY VIEW */}

                    {viewMode ===
                      "faculty" && (

                      <p
                        className="
                          mt-0.5
                          text-[10px]
                        "
                      >
                        {entry.room}
                      </p>

                    )}


                    {/* ROOM VIEW */}

                    {viewMode ===
                      "room" && (

                      <p
                        className="
                          mt-0.5
                          text-[10px]
                        "
                      >
                        {formatFacultyName(
                          entry.faculty
                        )}
                      </p>

                    )}


                    {/* TYPE */}

                    {entry.type && (

                      <p
                        className="
                          mt-1
                          text-[9px]
                          font-medium
                          opacity-70
                        "
                      >
                        {entry.type}
                      </p>

                    )}


                    {/* TIME */}

                    <p
                      className="
                        mt-1
                        text-[9px]
                        opacity-70
                      "
                    >
                      {formatMinutes(
                        entry.startMinutes
                      )}

                      {" - "}

                      {formatMinutes(
                        entry.endMinutes
                      )}
                    </p>

                  </div>

                );

              }
            )}

          </div>

        </div>

      </div>


      {/* ================================================= */}
      {/* EMPTY MESSAGE */}
      {/* ================================================= */}

      {mergedEntries.length === 0 && (

        <div
          className="
            border-t
            bg-slate-50
            px-6
            py-6
            text-center
            text-sm
            text-slate-500
          "
        >
          {emptyMessage}
        </div>

      )}

    </div>

  );

}


/* =========================================================
   FACULTY DISPLAY
========================================================= */

export function formatFacultyName(
  faculty: string
) {

  const value =
    String(
      faculty ?? ""
    ).trim();


  if (
    /^\d+$/.test(
      value
    )
  ) {

    return (
      `Faculty ${value}`
    );

  }


  return (
    value ||
    "Unassigned Faculty"
  );
}