import { useEffect, useState } from "react";

import type {
  FacultyPreferenceUpdate,
  GapPreference,
} from "../../api/preferences";

import {
  getFacultyPreference,
  updateFacultyPreference,
} from "../../api/preferences";
interface Props {
  facultyCode: number;
}


const DAYS = [
  { code: "Monday", label: "Monday" },
  { code: "Tuesday", label: "Tuesday" },
  { code: "Wednesday", label: "Wednesday" },
  { code: "Thursday", label: "Thursday" },
  { code: "Friday", label: "Friday" },
  { code: "Saturday", label: "Saturday" },
];


export default function FacultyPreferenceEditor({
  facultyCode,
}: Props) {

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [message, setMessage] = useState("");

  const [subjectInput, setSubjectInput] = useState("");

const [form, setForm] =
  useState<FacultyPreferenceUpdate>({
    faculty_priority: 1,

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


  async function loadPreferences() {

    try {

      setLoading(true);

      const data =
        await getFacultyPreference(
          facultyCode
        );

    setForm({
    faculty_priority: data.faculty_priority,

    preferred_subjects: data.preferred_subjects,
    subject_importance: data.subject_importance,

    preferred_days: data.preferred_days,
    day_importance: data.day_importance,

    preferred_start_time: data.preferred_start_time,
    preferred_end_time: data.preferred_end_time,
    time_importance: data.time_importance,

    gap_preference: data.gap_preference,
    gap_importance: data.gap_importance,

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


  function toggleDay(day: string) {

    setForm((previous) => {

      const exists =
        previous.preferred_days.includes(
          day
        );

      return {
        ...previous,

        preferred_days: exists
          ? previous.preferred_days.filter(
              (item) => item !== day
            )
          : [
              ...previous.preferred_days,
              day
            ],
      };
    });
  }


  function addSubject() {

    const subject =
      subjectInput
        .trim()
        .toUpperCase();

    if (!subject) {
      return;
    }

    if (
      form.preferred_subjects.includes(
        subject
      )
    ) {

      setSubjectInput("");
      return;
    }

    setForm((previous) => ({
      ...previous,

      preferred_subjects: [
        ...previous.preferred_subjects,
        subject,
      ],
    }));

    setSubjectInput("");
  }


  function removeSubject(
    subject: string
  ) {

    setForm((previous) => ({
      ...previous,

      preferred_subjects:
        previous.preferred_subjects.filter(
          (item) => item !== subject
        ),
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
        bg-white
        rounded-xl
        border
        p-6
        space-y-8
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
            text-sm
            text-gray-500
            mt-1
          "
        >
          These preferences are used
          when generating optimized
          faculty schedules.
        </p>

      </div>


      {/* ==================================
          FACULTY PRIORITY
      ================================== */}

      <div>

        <label
          className="
            block
            font-medium
            mb-2
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
            setForm({
              ...form,

              faculty_priority:
                Number(
                  event.target.value
                ),
            })
          }

          className="
            border
            rounded-lg
            px-3
            py-2
            w-32
          "
        />

        <p
          className="
            text-xs
            text-gray-500
            mt-1
          "
        >
          Priority 1 receives the
          strongest preference weight.
        </p>

      </div>


      {/* ==================================
          SUBJECT PREFERENCE
      ================================== */}

      <div>

        <div
          className="
            flex
            items-center
            justify-between
            mb-3
          "
        >

          <div>

            <h3 className="font-medium">
              Subject Preference
            </h3>

            <p
              className="
                text-sm
                text-gray-500
              "
            >
              Subjects this faculty
              prefers to teach.
            </p>

          </div>


          <input
            type="checkbox"

            checked={
              form.use_subject_preference
            }

            onChange={(event) =>
              setForm({
                ...form,

                use_subject_preference:
                  event.target.checked,
              })
            }

            className="
              w-5
              h-5
            "
          />

        </div>


        <div className="flex gap-2">

          <input
            value={subjectInput}

            onChange={(event) =>
              setSubjectInput(
                event.target.value
              )
            }

            onKeyDown={(event) => {

              if (
                event.key === "Enter"
              ) {

                event.preventDefault();

                addSubject();
              }
            }}

            placeholder="Example: ITE153"

            disabled={
              !form.use_subject_preference
            }

            className="
              border
              rounded-lg
              px-3
              py-2
              flex-1
              disabled:bg-gray-100
            "
          />


          <button
            type="button"

            onClick={addSubject}

            disabled={
              !form.use_subject_preference
            }

            className="
              bg-purple-700
              text-white
              px-4
              rounded-lg
              disabled:opacity-50
            "
          >
            Add
          </button>

        </div>


        <div
          className="
            flex
            flex-wrap
            gap-2
            mt-3
          "
        >

          {form.preferred_subjects.map(
            (subject) => (

              <button
                key={subject}

                type="button"

                onClick={() =>
                  removeSubject(
                    subject
                  )
                }

                className="
                  bg-purple-100
                  text-purple-800
                  px-3
                  py-1
                  rounded-full
                  text-sm
                "
              >
                {subject} ×
              </button>

            )
          )}

        </div>

      </div>


      {/* ==================================
          DAY PREFERENCE
      ================================== */}

      <div>

        <div
          className="
            flex
            justify-between
            mb-3
          "
        >

          <div>

            <h3 className="font-medium">
              Preferred Teaching Days
            </h3>

            <p
              className="
                text-sm
                text-gray-500
              "
            >
              Select the days the
              faculty prefers.
            </p>

          </div>


          <input
            type="checkbox"

            checked={
              form.use_day_preference
            }

            onChange={(event) =>
              setForm({
                ...form,

                use_day_preference:
                  event.target.checked,
              })
            }

            className="w-5 h-5"
          />

        </div>


        <div
          className="
            flex
            flex-wrap
            gap-4
          "
        >

          {DAYS.map((day) => (

            <label
              key={day.code}

              className="
                flex
                items-center
                gap-2
              "
            >

              <input
                type="checkbox"

                disabled={
                  !form.use_day_preference
                }

                checked={
                  form
                    .preferred_days
                    .includes(
                      day.code
                    )
                }

                onChange={() =>
                  toggleDay(
                    day.code
                  )
                }
              />

              {day.label}

            </label>

          ))}

        </div>

      </div>


      {/* ==================================
          TIME PREFERENCE
      ================================== */}

      <div>

        <div
          className="
            flex
            justify-between
            mb-3
          "
        >

          <div>

            <h3 className="font-medium">
              Preferred Teaching Time
            </h3>

            <p
              className="
                text-sm
                text-gray-500
              "
            >
              Preferred daily teaching
              time range.
            </p>

          </div>


          <input
            type="checkbox"

            checked={
              form.use_time_preference
            }

            onChange={(event) =>
              setForm({
                ...form,

                use_time_preference:
                  event.target.checked,
              })
            }

            className="w-5 h-5"
          />

        </div>


        <div
          className="
            flex
            items-center
            gap-4
          "
        >

          <input
            type="time"

            disabled={
              !form.use_time_preference
            }

            value={
              form
                .preferred_start_time
                ?? ""
            }

            onChange={(event) =>
              setForm({
                ...form,

                preferred_start_time:
                  event.target.value
                  || null,
              })
            }

            className="
              border
              rounded-lg
              px-3
              py-2
            "
          />


          <span>to</span>


          <input
            type="time"

            disabled={
              !form.use_time_preference
            }

            value={
              form
                .preferred_end_time
                ?? ""
            }

            onChange={(event) =>
              setForm({
                ...form,

                preferred_end_time:
                  event.target.value
                  || null,
              })
            }

            className="
              border
              rounded-lg
              px-3
              py-2
            "
          />

        </div>

      </div>


      {/* ==================================
          GAP / SCHEDULE STYLE
      ================================== */}

      <div>

        <div
          className="
            flex
            justify-between
            mb-3
          "
        >

          <div>

            <h3 className="font-medium">
              Schedule Style
            </h3>

            <p
              className="
                text-sm
                text-gray-500
              "
            >
              Optional preference for
              compact or spaced classes.
            </p>

          </div>


          <input
            type="checkbox"

            checked={
              form.use_gap_preference
            }

            onChange={(event) =>
              setForm({
                ...form,

                use_gap_preference:
                  event.target.checked,
              })
            }

            className="w-5 h-5"
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
            setForm({
              ...form,

             gap_preference:
                event.target.value as GapPreference,
            })
          }

          className="
            border
            rounded-lg
            px-3
            py-2
          "
        >

          <option>
            No Preference
          </option>

          <option>
            Compact
          </option>

          <option>
            Scattered
          </option>

        </select>

      </div>


      {/* ==================================
          SAVE
      ================================== */}

      <div
        className="
          border-t
          pt-5
          flex
          items-center
          gap-4
        "
      >

        <button
          type="button"

          onClick={
            savePreferences
          }

          disabled={saving}

          className="
            bg-orange-500
            hover:bg-orange-600
            text-white
            font-medium
            px-5
            py-2
            rounded-lg
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