import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  FacultyPreferenceUpdate,
  GapPreference,
  LectureLabPreference,
} from "../../api/preferences";

import {
  getFacultyPreference,
  updateFacultyPreference,
} from "../../api/preferences";

import type {
  AvailableSubject,
} from "../../api/subjects";

import {
  getAvailableSubjects,
} from "../../api/subjects";

import PreferenceCalendar from "./PreferenceCalendar";

import type {
  PreferenceCalendarSummary,
  PreferenceScheduleBlock,
} from "./PreferenceCalendar";


interface Props {
  facultyCode: number;
}


const IMPORTANCE_OPTIONS = [
  { value: 0, label: "Ignore" },
  { value: 1, label: "Very Low" },
  { value: 2, label: "Low" },
  { value: 3, label: "Medium" },
  { value: 4, label: "High" },
  { value: 5, label: "Very High" },
];


function ordinal(rank: number) {
  const mod100 = rank % 100;

  if (mod100 >= 11 && mod100 <= 13) {
    return `${rank}th`;
  }

  switch (rank % 10) {
    case 1:
      return `${rank}st`;
    case 2:
      return `${rank}nd`;
    case 3:
      return `${rank}rd`;
    default:
      return `${rank}th`;
  }
}


export default function FacultyPreferenceEditor({
  facultyCode,
}: Props) {

  const [loading, setLoading] =
    useState(true);

  const [saving, setSaving] =
    useState(false);

  const [message, setMessage] =
    useState("");

  const [subjectFilter, setSubjectFilter] =
    useState("");

  const [showRanking, setShowRanking] =
    useState(false);

  const [
    draggedRankIndex,
    setDraggedRankIndex,
  ] = useState<number | null>(null);

  const [
    availableSubjects,
    setAvailableSubjects,
  ] = useState<AvailableSubject[]>([]);


  const [form, setForm] =
    useState<FacultyPreferenceUpdate>({

      faculty_priority: 1,

      preferred_schedule_blocks: [],

      preferred_subjects: [],
      subject_importance: 3,

      preferred_days: [],
      day_importance: 3,

      preferred_start_time: null,
      preferred_end_time: null,
      time_importance: 3,

      gap_preference: "No Preference",
      gap_importance: 0,

      lecture_lab_preference: "No Preference",
      lecture_lab_importance: 0,

      use_subject_preference: true,
      use_day_preference: true,
      use_time_preference: true,
      use_gap_preference: false,
      use_lecture_lab_preference: false,
    });


  useEffect(() => {
    loadPreferences();
  }, [facultyCode]);


  useEffect(() => {
    loadAvailableSubjects();
  }, []);


  async function loadPreferences() {

    try {

      setLoading(true);
      setMessage("");

      const data =
        await getFacultyPreference(
          facultyCode
        );

      setForm({
        faculty_priority:
          data.faculty_priority,

        preferred_schedule_blocks:
          data.preferred_schedule_blocks ?? [],

        preferred_subjects:
          data.preferred_subjects,

        subject_importance:
          data.subject_importance,

        preferred_days:
          data.preferred_days,

        day_importance:
          data.day_importance,

        preferred_start_time:
          data.preferred_start_time,

        preferred_end_time:
          data.preferred_end_time,

        time_importance:
          data.time_importance,

        gap_preference:
          data.gap_preference,

        gap_importance:
          data.gap_importance,

        lecture_lab_preference:
          data.lecture_lab_preference,

        lecture_lab_importance:
          data.lecture_lab_importance,

        use_subject_preference:
          data.use_subject_preference,

        use_day_preference:
          data.use_day_preference,

        use_time_preference:
          data.use_time_preference,

        use_gap_preference:
          data.use_gap_preference,

        use_lecture_lab_preference:
          data.use_lecture_lab_preference,
      });

    } catch (error) {

      console.error(
        "Failed to load preferences:",
        error
      );

      setMessage(
        "Failed to load faculty preferences."
      );

    } finally {

      setLoading(false);
    }
  }


  async function loadAvailableSubjects() {

    try {

      const subjects =
        await getAvailableSubjects();

      setAvailableSubjects(subjects);

    } catch (error) {

      console.error(
        "Failed to load available subjects:",
        error
      );
    }
  }


  const filteredSubjects =
    useMemo(() => {

      const query =
        subjectFilter
          .trim()
          .toLowerCase();

      if (!query) {
        return availableSubjects;
      }

      return availableSubjects.filter(
        (subject) => {

          const code =
            subject.subject_code
              .toLowerCase();

          const title =
            (
              subject.subject_title
              ?? ""
            ).toLowerCase();

          return (
            code.includes(query)
            || title.includes(query)
          );
        }
      );

    }, [
      availableSubjects,
      subjectFilter,
    ]);


  function toggleSubject(
    subjectCode: string
  ) {

    const normalized =
      subjectCode
        .trim()
        .toUpperCase();

    setForm((previous) => {

      const exists =
        previous.preferred_subjects
          .includes(normalized);

      return {
        ...previous,

        preferred_subjects:
          exists
            ? previous.preferred_subjects
                .filter(
                  (item) =>
                    item !== normalized
                )
            : [
                ...previous.preferred_subjects,
                normalized,
              ],
      };
    });

    setMessage("");
  }


  function removeSubject(
    subjectCode: string
  ) {

    setForm((previous) => ({
      ...previous,

      preferred_subjects:
        previous.preferred_subjects
          .filter(
            (item) =>
              item !== subjectCode
          ),
    }));
  }


  function moveSubjectToRank(
    subjectCode: string,
    targetRank: number
  ) {

    setForm((previous) => {

      const currentIndex =
        previous.preferred_subjects
          .findIndex(
            (item) =>
              item === subjectCode
          );

      if (currentIndex < 0) {
        return previous;
      }

      const targetIndex =
        Math.max(
          0,
          Math.min(
            previous.preferred_subjects
              .length - 1,
            targetRank - 1
          )
        );

      if (
        currentIndex === targetIndex
      ) {
        return previous;
      }

      const updated = [
        ...previous.preferred_subjects,
      ];

      const [moved] =
        updated.splice(
          currentIndex,
          1
        );

      updated.splice(
        targetIndex,
        0,
        moved
      );

      return {
        ...previous,
        preferred_subjects: updated,
      };
    });
  }


  function reorderSubjectByDrag(
    targetIndex: number
  ) {

    if (
      draggedRankIndex === null
      || draggedRankIndex === targetIndex
    ) {
      return;
    }

    setForm((previous) => {

      const updated = [
        ...previous.preferred_subjects,
      ];

      const [moved] =
        updated.splice(
          draggedRankIndex,
          1
        );

      updated.splice(
        targetIndex,
        0,
        moved
      );

      return {
        ...previous,
        preferred_subjects: updated,
      };
    });

    setDraggedRankIndex(
      targetIndex
    );
  }


  const handleCalendarSummaryChange =
    useCallback(
      (
        summary:
          PreferenceCalendarSummary
      ) => {

        setForm((previous) => {

          const sameDays =
            JSON.stringify(
              previous.preferred_days
            )
            ===
            JSON.stringify(
              summary.preferredDays
            );

          if (
            sameDays
            && previous
              .preferred_start_time
              ===
              summary
                .preferredStartTime
            && previous
              .preferred_end_time
              ===
              summary
                .preferredEndTime
          ) {
            return previous;
          }

          return {
            ...previous,

            preferred_days:
              summary.preferredDays,

            preferred_start_time:
              summary
                .preferredStartTime,

            preferred_end_time:
              summary
                .preferredEndTime,

            use_day_preference:
              summary.preferredDays
                .length > 0,

            use_time_preference:
              Boolean(
                summary
                  .preferredStartTime
                && summary
                  .preferredEndTime
              ),
          };
        });
      },
      []
    );


  const handleScheduleBlocksChange =
    useCallback(
      (blocks: PreferenceScheduleBlock[]) => {
        setForm((previous) => {
          if (
            JSON.stringify(previous.preferred_schedule_blocks)
            === JSON.stringify(blocks)
          ) {
            return previous;
          }

          return {
            ...previous,
            preferred_schedule_blocks: blocks,
          };
        });
      },
      []
    );


  function setScheduleImportance(
    importance: number
  ) {

    setForm((previous) => ({
      ...previous,
      day_importance: importance,
      time_importance: importance,
    }));
  }


  function handleGapPreferenceChange(
    value: string
  ) {
    let nextValue: GapPreference =
      "No Preference";

    if (value === "Compact") {
      nextValue = "Compact";
    }

    if (value === "Scattered") {
      nextValue = "Scattered";
    }

    setForm((previous) => ({
      ...previous,
      gap_preference: nextValue,
    }));
  }


  function handleLectureLabPreferenceChange(
    value: string
  ) {
    let nextValue: LectureLabPreference =
      "No Preference";

    if (value === "Same Day") {
      nextValue = "Same Day";
    }

    if (value === "Different Day") {
      nextValue = "Different Day";
    }

    setForm((previous) => ({
      ...previous,
      lecture_lab_preference: nextValue,
    }));
  }


  async function savePreferences() {

    try {

      setSaving(true);
      setMessage("");

      await updateFacultyPreference(
        facultyCode,
        form
      );

      setMessage(
        "Preferences saved successfully."
      );

    } catch (error) {

      console.error(
        "Failed to save preferences:",
        error
      );

      setMessage(
        "Failed to save preferences."
      );

    } finally {

      setSaving(false);
    }
  }


  if (loading) {
    return (
      <div className="p-6">
        Loading preferences...
      </div>
    );
  }


  return (

    <div
      className="
        space-y-8
        rounded-xl
        border
        bg-white
        p-6
      "
    >

      <div>

        <h2
          className="
            text-xl
            font-semibold
            text-gray-900
          "
        >
          Faculty Preferences
        </h2>

        <p
          className="
            mt-1
            text-sm
            text-gray-500
          "
        >
          Select preferred subjects first, then
          drag those selected subjects into the
          preferred weekly schedule below.
        </p>

      </div>


      <section
        className="
          rounded-xl
          border
          border-slate-200
          p-5
        "
      >

        <label
          className="
            mb-2
            block
            font-medium
          "
        >
          Faculty Priority
        </label>

        <input
          type="number"
          min={1}
          value={
            form.faculty_priority
          }

          onChange={(event) =>
            setForm((previous) => ({
              ...previous,

              faculty_priority:
                Number(
                  event.target.value
                ),
            }))
          }

          className="
            w-32
            rounded-lg
            border
            px-3
            py-2
          "
        />

        <p
          className="
            mt-1
            text-xs
            text-gray-500
          "
        >
          Priority 1 receives the strongest
          preference weight.
        </p>

      </section>


      <section
        className="
          rounded-xl
          border
          border-slate-200
          p-5
        "
      >

        <div
          className="
            flex
            flex-col
            gap-3
            sm:flex-row
            sm:items-start
            sm:justify-between
          "
        >

          <div>

            <h3
              className="
                font-semibold
                text-slate-900
              "
            >
              Preferred Subjects
            </h3>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Browse the subjects being offered
              and select the ones this faculty
              prefers to teach.
            </p>

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
                text-sm
                text-slate-600
              "
            >
              Enable
            </span>

            <input
              type="checkbox"

              checked={
                form
                  .use_subject_preference
              }

              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,

                  use_subject_preference:
                    event.target.checked,
                }))
              }

              className="h-5 w-5"
            />

          </div>

        </div>


        <div
          className="
            mt-4
            grid
            gap-4
            lg:grid-cols-[1fr_260px]
            lg:items-end
          "
        >

          <div>

            <label
              className="
                mb-2
                block
                text-sm
                font-medium
                text-slate-700
              "
            >
              Filter Subjects
            </label>

            <input
              type="text"

              value={subjectFilter}

              onChange={(event) =>
                setSubjectFilter(
                  event.target.value
                )
              }

              placeholder=
                "Filter by subject code or title..."

              disabled={
                !form
                  .use_subject_preference
              }

              className="
                w-full
                rounded-lg
                border
                border-slate-300
                px-3
                py-2
                disabled:bg-gray-100
              "
            />

          </div>


          <div>

            <label
              className="
                mb-2
                block
                text-sm
                font-medium
                text-slate-700
              "
            >
              Subject Preference Importance
            </label>

            <select
              value={
                form.subject_importance
              }

              disabled={
                !form
                  .use_subject_preference
              }

              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,

                  subject_importance:
                    Number(
                      event.target.value
                    ),
                }))
              }

              className="
                w-full
                rounded-lg
                border
                border-slate-300
                px-3
                py-2
                disabled:bg-gray-100
              "
            >
              {
                IMPORTANCE_OPTIONS.map(
                  (option) => (

                    <option
                      key={option.value}
                      value={option.value}
                    >
                      {option.value}
                      {" - "}
                      {option.label}
                    </option>

                  )
                )
              }
            </select>

          </div>

        </div>


        <div
          className="
            mt-4
            max-h-80
            overflow-y-auto
            rounded-xl
            border
            border-slate-200
            bg-slate-50
            p-2
          "
        >

          {
            filteredSubjects.length === 0
              ? (

                <div
                  className="
                    px-4
                    py-10
                    text-center
                    text-sm
                    text-slate-500
                  "
                >
                  No subjects match the filter.
                </div>

              )
              : filteredSubjects.map(
                  (subject) => {

                    const code =
                      subject.subject_code
                        .toUpperCase();

                    const selected =
                      form.preferred_subjects
                        .includes(code);

                    return (

                      <label
                        key={code}

                        className={[
                          "mb-2",
                          "flex",
                          "items-start",
                          "gap-3",
                          "rounded-lg",
                          "border",
                          "px-3",
                          "py-3",
                          "transition",
                          selected
                            ? (
                                "border-purple-300 "
                                + "bg-purple-50"
                              )
                            : (
                                "border-slate-200 "
                                + "bg-white "
                                + "hover:border-slate-300"
                              ),
                          form
                            .use_subject_preference
                            ? "cursor-pointer"
                            : (
                                "cursor-not-allowed "
                                + "opacity-50"
                              ),
                        ].join(" ")}
                      >

                        <input
                          type="checkbox"

                          disabled={
                            !form
                              .use_subject_preference
                          }

                          checked={selected}

                          onChange={() =>
                            toggleSubject(code)
                          }

                          className="
                            mt-1
                            h-4
                            w-4
                            accent-purple-700
                          "
                        />


                        <div
                          className="
                            min-w-0
                            flex-1
                          "
                        >

                          <div
                            className="
                              text-sm
                              font-semibold
                              text-slate-900
                            "
                          >
                            {code}
                          </div>

                          <div
                            className="
                              mt-0.5
                              text-xs
                              text-slate-500
                            "
                          >
                            {
                              subject.subject_title
                              || "No title available"
                            }
                          </div>

                        </div>


                        {selected && (

                          <div
                            className="
                              rounded-full
                              bg-purple-100
                              px-2
                              py-1
                              text-[11px]
                              font-semibold
                              text-purple-700
                            "
                          >
                            Selected
                          </div>

                        )}

                      </label>
                    );
                  }
                )
          }

        </div>


        <div
          className="
            mt-4
            flex
            flex-col
            gap-3
            md:flex-row
            md:items-center
            md:justify-between
          "
        >

          <div
            className="
              text-sm
              text-slate-600
            "
          >
            <span className="font-semibold">
              {
                form.preferred_subjects
                  .length
              }
            </span>
            {" "}
            subject
            {
              form.preferred_subjects
                .length === 1
                ? ""
                : "s"
            }
            {" "}
            selected
          </div>


          <button
            type="button"

            onClick={() =>
              setShowRanking(
                (current) => !current
              )
            }

            disabled={
              form.preferred_subjects
                .length === 0
            }

            className="
              rounded-lg
              border
              border-purple-200
              bg-purple-50
              px-4
              py-2
              text-sm
              font-semibold
              text-purple-700
              hover:bg-purple-100
              disabled:cursor-not-allowed
              disabled:opacity-40
            "
          >
            {
              showRanking
                ? "Hide Subject Rankings"
                : "Manage Subject Rankings"
            }
          </button>

        </div>


        {
          form.preferred_subjects
            .length > 0
          && (

            <div
              className="
                mt-4
                rounded-xl
                border
                border-purple-100
                bg-purple-50/50
                p-4
              "
            >

              <div
                className="
                  mb-3
                  text-sm
                  font-semibold
                  text-slate-800
                "
              >
                Selected Preferred Subjects
              </div>


              <div
                className="
                  flex
                  flex-wrap
                  gap-2
                "
              >
                {
                  form.preferred_subjects
                    .map(
                      (
                        subject,
                        index
                      ) => (

                        <div
                          key={subject}

                          className="
                            flex
                            items-center
                            gap-2
                            rounded-full
                            border
                            border-purple-200
                            bg-white
                            px-3
                            py-2
                          "
                        >

                          <span
                            className="
                              text-xs
                              font-semibold
                              text-purple-700
                            "
                          >
                            {ordinal(index + 1)}
                          </span>

                          <span
                            className="
                              text-sm
                              font-medium
                              text-slate-900
                            "
                          >
                            {subject}
                          </span>

                          <button
                            type="button"

                            onClick={() =>
                              removeSubject(
                                subject
                              )
                            }

                            className="
                              ml-1
                              text-slate-400
                              hover:text-red-600
                            "
                          >
                            ×
                          </button>

                        </div>

                      )
                    )
                }
              </div>

            </div>

          )
        }


        {showRanking && (

          <div
            className="
              mt-5
              rounded-xl
              border
              border-slate-200
              bg-slate-50
              p-4
            "
          >

            <div
              className="
                mb-3
                text-sm
                font-medium
                text-slate-700
              "
            >
              Drag rows to reorder or use
              the rank dropdown.
            </div>


            <div className="space-y-2">

              {
                form.preferred_subjects
                  .map(
                    (
                      subject,
                      index
                    ) => {

                      const detail =
                        availableSubjects.find(
                          (item) =>
                            item.subject_code
                              .toUpperCase()
                            ===
                            subject
                              .toUpperCase()
                        );

                      return (

                        <div
                          key={subject}
                          draggable

                          onDragStart={() =>
                            setDraggedRankIndex(
                              index
                            )
                          }

                          onDragOver={
                            (event) => {

                              event
                                .preventDefault();

                              reorderSubjectByDrag(
                                index
                              );
                            }
                          }

                          onDragEnd={() =>
                            setDraggedRankIndex(
                              null
                            )
                          }

                          className="
                            flex
                            cursor-grab
                            items-center
                            gap-3
                            rounded-xl
                            border
                            border-slate-200
                            bg-white
                            px-3
                            py-3
                            shadow-sm
                          "
                        >

                          <div
                            className="
                              text-lg
                              text-slate-400
                            "
                          >
                            ☰
                          </div>

                          <div
                            className="
                              flex
                              h-8
                              w-8
                              items-center
                              justify-center
                              rounded-full
                              bg-purple-100
                              text-sm
                              font-semibold
                              text-purple-700
                            "
                          >
                            {index + 1}
                          </div>


                          <div
                            className="
                              min-w-0
                              flex-1
                            "
                          >

                            <div
                              className="
                                font-medium
                                text-slate-900
                              "
                            >
                              {subject}
                            </div>

                            <div
                              className="
                                truncate
                                text-xs
                                text-slate-500
                              "
                            >
                              {
                                detail
                                  ?.subject_title
                                || (
                                  `${ordinal(
                                    index + 1
                                  )} preference`
                                )
                              }
                            </div>

                          </div>


                          <select
                            value={index + 1}

                            onChange={
                              (event) =>
                                moveSubjectToRank(
                                  subject,
                                  Number(
                                    event
                                      .target
                                      .value
                                  )
                                )
                            }

                            onMouseDown={
                              (event) =>
                                event
                                  .stopPropagation()
                            }

                            className="
                              rounded-lg
                              border
                              border-slate-300
                              bg-white
                              px-3
                              py-2
                              text-sm
                              font-medium
                            "
                          >
                            {
                              form
                                .preferred_subjects
                                .map(
                                  (
                                    _,
                                    rankIndex
                                  ) => (

                                    <option
                                      key={
                                        rankIndex
                                        + 1
                                      }
                                      value={
                                        rankIndex
                                        + 1
                                      }
                                    >
                                      {
                                        ordinal(
                                          rankIndex
                                          + 1
                                        )
                                      }
                                    </option>

                                  )
                                )
                            }
                          </select>


                          <button
                            type="button"

                            onClick={() =>
                              removeSubject(
                                subject
                              )
                            }

                            className="
                              rounded-lg
                              border
                              border-red-200
                              px-3
                              py-2
                              text-sm
                              text-red-600
                              hover:bg-red-50
                            "
                          >
                            Remove
                          </button>

                        </div>
                      );
                    }
                  )
              }

            </div>

          </div>

        )}

      </section>


      <section
        className="
          rounded-xl
          border
          border-slate-200
          p-5
        "
      >

        <div
          className="
            mb-4
            grid
            gap-4
            lg:grid-cols-[1fr_280px]
            lg:items-end
          "
        >

          <div>

            <h3
              className="
                font-semibold
                text-slate-900
              "
            >
              Scheduling Preference
            </h3>

            <p
              className="
                mt-1
                text-sm
                text-slate-500
              "
            >
              Only the preferred subjects selected
              above appear as draggable subject cards.
              Drag them into the weekly timetable.
            </p>

          </div>


          <div>

            <label
              className="
                mb-2
                block
                text-sm
                font-medium
                text-slate-700
              "
            >
              Schedule Preference Importance
            </label>

            <select
              value={
                Math.max(
                  form.day_importance,
                  form.time_importance
                )
              }

              onChange={(event) =>
                setScheduleImportance(
                  Number(
                    event.target.value
                  )
                )
              }

              className="
                w-full
                rounded-lg
                border
                border-slate-300
                px-3
                py-2
              "
            >
              {
                IMPORTANCE_OPTIONS.map(
                  (option) => (

                    <option
                      key={option.value}
                      value={option.value}
                    >
                      {option.value}
                      {" - "}
                      {option.label}
                    </option>

                  )
                )
              }
            </select>

          </div>

        </div>


        <PreferenceCalendar
          key={facultyCode}
          facultyCode={facultyCode}

          preferredSubjects={
            form.preferred_subjects
          }

          availableSubjects={
            availableSubjects
          }

          legacyPreferredDays={
            form.preferred_days
          }

          legacyStartTime={
            form.preferred_start_time
          }

          legacyEndTime={
            form.preferred_end_time
          }

          scheduleBlocks={
            form.preferred_schedule_blocks
          }

          onScheduleBlocksChange={
            handleScheduleBlocksChange
          }

          onCalendarSummaryChange={
            handleCalendarSummaryChange
          }

          onSetSubjectRank={
            moveSubjectToRank
          }
        />

      </section>


      <section
        className="
          grid
          gap-5
          lg:grid-cols-2
        "
      >

        <div
          className="
            rounded-xl
            border
            border-slate-200
            p-5
          "
        >

          <div
            className="
              flex
              items-start
              justify-between
              gap-4
            "
          >

            <div>

              <h3
                className="
                  font-semibold
                  text-slate-900
                "
              >
                Schedule Style
              </h3>

              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                Compact, scattered, or no
                preference.
              </p>

            </div>

            <input
              type="checkbox"

              checked={
                form.use_gap_preference
              }

              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,

                  use_gap_preference:
                    event.target.checked,
                }))
              }

              className="h-5 w-5"
            />

          </div>


          <select
            disabled={
              !form.use_gap_preference
            }

            value={
              form.gap_preference
            }

            onChange={(event) =>
              handleGapPreferenceChange(
                event.target.value
              )
            }

            className="
              mt-4
              w-full
              rounded-lg
              border
              border-slate-300
              px-3
              py-2
              disabled:bg-gray-100
            "
          >
            <option
              value="No Preference"
            >
              No Preference
            </option>

            <option value="Compact">
              Compact
            </option>

            <option value="Scattered">
              Scattered
            </option>
          </select>


          <label
            className="
              mb-2
              mt-4
              block
              text-sm
              font-medium
              text-slate-700
            "
          >
            Importance
          </label>

          <select
            value={
              form.gap_importance
            }

            disabled={
              !form.use_gap_preference
            }

            onChange={(event) =>
              setForm((previous) => ({
                ...previous,

                gap_importance:
                  Number(
                    event.target.value
                  ),
              }))
            }

            className="
              w-full
              rounded-lg
              border
              border-slate-300
              px-3
              py-2
              disabled:bg-gray-100
            "
          >
            {
              IMPORTANCE_OPTIONS.map(
                (option) => (

                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.value}
                    {" - "}
                    {option.label}
                  </option>

                )
              )
            }
          </select>

        </div>


        <div
          className="
            rounded-xl
            border
            border-slate-200
            p-5
          "
        >

          <div
            className="
              flex
              items-start
              justify-between
              gap-4
            "
          >

            <div>

              <h3
                className="
                  font-semibold
                  text-slate-900
                "
              >
                Lecture / Laboratory Day
              </h3>

              <p
                className="
                  mt-1
                  text-sm
                  text-slate-500
                "
              >
                Prefer lecture and laboratory on
                the same day or different days.
              </p>

            </div>

            <input
              type="checkbox"

              checked={
                form
                  .use_lecture_lab_preference
              }

              onChange={(event) =>
                setForm((previous) => ({
                  ...previous,

                  use_lecture_lab_preference:
                    event.target.checked,
                }))
              }

              className="h-5 w-5"
            />

          </div>


          <select
            value={
              form
                .lecture_lab_preference
            }

            disabled={
              !form
                .use_lecture_lab_preference
            }

            onChange={(event) =>
              handleLectureLabPreferenceChange(
                event.target.value
              )
            }

            className="
              mt-4
              w-full
              rounded-lg
              border
              border-slate-300
              px-3
              py-2
              disabled:bg-gray-100
            "
          >
            <option
              value="No Preference"
            >
              No Preference
            </option>

            <option value="Same Day">
              Same Day
            </option>

            <option
              value="Different Day"
            >
              Different Day
            </option>
          </select>


          <label
            className="
              mb-2
              mt-4
              block
              text-sm
              font-medium
              text-slate-700
            "
          >
            Importance
          </label>

          <select
            value={
              form
                .lecture_lab_importance
            }

            disabled={
              !form
                .use_lecture_lab_preference
            }

            onChange={(event) =>
              setForm((previous) => ({
                ...previous,

                lecture_lab_importance:
                  Number(
                    event.target.value
                  ),
              }))
            }

            className="
              w-full
              rounded-lg
              border
              border-slate-300
              px-3
              py-2
              disabled:bg-gray-100
            "
          >
            {
              IMPORTANCE_OPTIONS.map(
                (option) => (

                  <option
                    key={option.value}
                    value={option.value}
                  >
                    {option.value}
                    {" - "}
                    {option.label}
                  </option>

                )
              )
            }
          </select>

        </div>

      </section>


      <div
        className="
          flex
          flex-wrap
          items-center
          gap-4
          border-t
          pt-5
        "
      >

        <button
          type="button"

          onClick={
            savePreferences
          }

          disabled={saving}

          className="
            rounded-lg
            bg-orange-500
            px-5
            py-2
            font-medium
            text-white
            hover:bg-orange-600
            disabled:opacity-50
          "
        >
          {
            saving
              ? "Saving..."
              : "Save Preferences"
          }
        </button>


        {message && (

          <span
            className="
              text-sm
              text-gray-600
            "
          >
            {message}
          </span>

        )}

      </div>

    </div>
  );
}
