import { useEffect, useMemo, useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin, { Draggable } from "@fullcalendar/interaction";
import type { DateSelectArg, EventApi, EventClickArg } from "@fullcalendar/core";
import type { AvailableSubject } from "../../api/subjects";

export type PreferenceComponent = "Lecture" | "Laboratory";
export type PreferenceEventKind = "general" | "subject";

export interface PreferenceCalendarSummary {
  preferredDays: string[];
  preferredStartTime: string | null;
  preferredEndTime: string | null;
}

export interface PreferenceScheduleBlock {
  id: string;
  kind: PreferenceEventKind;
  day: string;
  start_time: string;
  end_time: string;
  subject_code?: string | null;
  subject_title?: string | null;
  component?: PreferenceComponent | null;
}

interface StoredPreferenceEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  kind: PreferenceEventKind;
  subjectCode?: string;
  subjectTitle?: string;
  component?: PreferenceComponent;
}

interface Props {
  facultyCode: number;
  preferredSubjects: string[];
  availableSubjects: AvailableSubject[];
  legacyPreferredDays: string[];
  legacyStartTime: string | null;
  legacyEndTime: string | null;
  scheduleBlocks: PreferenceScheduleBlock[];
  onScheduleBlocksChange: (blocks: PreferenceScheduleBlock[]) => void;
  onCalendarSummaryChange: (summary: PreferenceCalendarSummary) => void;
  onSetSubjectRank: (subjectCode: string, rank: number) => void;
}

const REFERENCE_DATES: Record<string, string> = {
  Monday: "2026-09-28",
  Tuesday: "2026-09-29",
  Wednesday: "2026-09-30",
  Thursday: "2026-10-01",
  Friday: "2026-10-02",
  Saturday: "2026-10-03",
};

const DATE_TO_DAY: Record<string, string> = {
  "2026-09-28": "Monday",
  "2026-09-29": "Tuesday",
  "2026-09-30": "Wednesday",
  "2026-10-01": "Thursday",
  "2026-10-02": "Friday",
  "2026-10-03": "Saturday",
};

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function formatLocalDateTime(date: Date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

function getDatePart(value: string) {
  return value.slice(0, 10);
}

function getTimePart(value: string) {
  return value.slice(11, 16);
}

function eventDayName(event: StoredPreferenceEvent) {
  return DATE_TO_DAY[getDatePart(event.start)] ?? "";
}


function makeId() {
  return `pref-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function buildLegacyEvents(
  preferredDays: string[],
  startTime: string | null,
  endTime: string | null
): StoredPreferenceEvent[] {
  if (!startTime || !endTime || preferredDays.length === 0) return [];

  return preferredDays
    .filter((day) => Boolean(REFERENCE_DATES[day]))
    .map((day) => ({
      id: makeId(),
      title: "Preferred Teaching Time",
      start: `${REFERENCE_DATES[day]}T${startTime}:00`,
      end: `${REFERENCE_DATES[day]}T${endTime}:00`,
      kind: "general" as const,
    }));
}

function calculateGeneralSummary(events: StoredPreferenceEvent[]): PreferenceCalendarSummary {
  const generalEvents = events.filter((event) => event.kind === "general");

  if (generalEvents.length === 0) {
    return { preferredDays: [], preferredStartTime: null, preferredEndTime: null };
  }

  const preferredDays = Array.from(new Set(generalEvents.map(eventDayName).filter(Boolean)));
  const startTimes = generalEvents.map((event) => getTimePart(event.start)).sort();
  const endTimes = generalEvents.map((event) => getTimePart(event.end)).sort();

  return {
    preferredDays,
    preferredStartTime: startTimes[0] ?? null,
    preferredEndTime: endTimes[endTimes.length - 1] ?? null,
  };
}

function ordinal(rank: number) {
  const mod100 = rank % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${rank}th`;
  if (rank % 10 === 1) return `${rank}st`;
  if (rank % 10 === 2) return `${rank}nd`;
  if (rank % 10 === 3) return `${rank}rd`;
  return `${rank}th`;
}


function formatClock(date: Date) {
  let hours = date.getHours();
  const minutes = date.getMinutes();
  const suffix = hours >= 12 ? "PM" : "AM";

  hours = hours % 12;

  if (hours === 0) {
    hours = 12;
  }

  return (
    `${String(hours).padStart(2, "0")}:`
    + `${String(minutes).padStart(2, "0")}`
    + suffix
  );
}


function formatSlotRange(date: Date) {
  const end = new Date(
    date.getTime() + 30 * 60 * 1000
  );

  return (
    `${formatClock(date)}-`
    + `${formatClock(end)}`
  );
}


function blocksToEvents(blocks: PreferenceScheduleBlock[]): StoredPreferenceEvent[] {
  return blocks
    .filter((block) => Boolean(REFERENCE_DATES[block.day]))
    .map((block) => ({
      id: block.id,
      title:
        block.kind === "subject" && block.subject_code
          ? `${block.subject_code.toUpperCase()} — ${block.component ?? "Lecture"}`
          : "Preferred Teaching Time",
      start: `${REFERENCE_DATES[block.day]}T${block.start_time}:00`,
      end: `${REFERENCE_DATES[block.day]}T${block.end_time}:00`,
      kind: block.kind,
      subjectCode: block.subject_code ?? undefined,
      subjectTitle: block.subject_title ?? undefined,
      component: block.component ?? undefined,
    }));
}

function eventsToBlocks(events: StoredPreferenceEvent[]): PreferenceScheduleBlock[] {
  return events
    .map((event) => ({
      id: event.id,
      kind: event.kind,
      day: eventDayName(event),
      start_time: getTimePart(event.start),
      end_time: getTimePart(event.end),
      subject_code: event.subjectCode ?? null,
      subject_title: event.subjectTitle ?? null,
      component: event.component ?? null,
    }))
    .filter((block) => Boolean(block.day));
}


export default function PreferenceCalendar({
  facultyCode,
  preferredSubjects,
  availableSubjects,
  legacyPreferredDays,
  legacyStartTime,
  legacyEndTime,
  scheduleBlocks,
  onScheduleBlocksChange,
  onCalendarSummaryChange,
  onSetSubjectRank,
}: Props) {
  const trayRef = useRef<HTMLDivElement | null>(null);

  const [events, setEvents] =
    useState<StoredPreferenceEvent[]>(() => {
      if (scheduleBlocks.length > 0) {
        return blocksToEvents(scheduleBlocks);
      }

      return buildLegacyEvents(
        legacyPreferredDays,
        legacyStartTime,
        legacyEndTime
      );
    });
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [editDay, setEditDay] = useState("Monday");
  const [editStart, setEditStart] = useState("09:00");
  const [editEnd, setEditEnd] = useState("10:00");

  const selectedEvent = useMemo(
    () => events.find((event) => event.id === selectedEventId) ?? null,
    [events, selectedEventId]
  );

  const subjectMap = useMemo(() => {
    const result = new Map<string, AvailableSubject>();
    for (const subject of availableSubjects) {
      result.set(subject.subject_code.toUpperCase(), subject);
    }
    return result;
  }, [availableSubjects]);

  useEffect(() => {
    if (scheduleBlocks.length > 0) {
      setEvents(
        blocksToEvents(scheduleBlocks)
      );
      return;
    }

    setEvents(
      buildLegacyEvents(
        legacyPreferredDays,
        legacyStartTime,
        legacyEndTime
      )
    );
    // The calendar is keyed by facultyCode in the parent, so this
    // effect is only a safety net for faculty switching.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facultyCode]);

  useEffect(() => {
    const allowedSubjects = new Set(
      preferredSubjects.map(
        (subject) => subject.toUpperCase()
      )
    );

    setEvents((current) => {
      const filtered = current.filter(
        (event) =>
          event.kind === "general"
          || (
            event.subjectCode
            && allowedSubjects.has(
              event.subjectCode.toUpperCase()
            )
          )
      );

      if (filtered.length === current.length) {
        return current;
      }

      return filtered;
    });
  }, [preferredSubjects]);

  useEffect(() => {
    const nextBlocks =
      eventsToBlocks(events);

    const nextSummary =
      calculateGeneralSummary(events);

    if (
      JSON.stringify(nextBlocks)
      !== JSON.stringify(scheduleBlocks)
    ) {
      onScheduleBlocksChange(
        nextBlocks
      );
    }

    onCalendarSummaryChange(
      nextSummary
    );
  }, [
    events,
    scheduleBlocks,
    onScheduleBlocksChange,
    onCalendarSummaryChange,
  ]);

  const usedSubjectComponents = useMemo(() => {
    const used = new Set<string>();
    for (const event of events) {
      if (event.kind === "subject" && event.subjectCode && event.component) {
        used.add(`${event.subjectCode.toUpperCase()}::${event.component}`);
      }
    }
    return used;
  }, [events]);

  useEffect(() => {
    const element = trayRef.current;
    if (!element) return;

    const draggable = new Draggable(element, {
      itemSelector: ".faculty-pref-draggable",
      eventData(eventElement) {
        const raw = eventElement.getAttribute("data-event");
        if (!raw) return {};
        const parsed = JSON.parse(raw);
        return {
          title: parsed.title,
          duration: "01:00",
          create: true,
          extendedProps: {
            kind: "subject",
            subjectCode: parsed.subjectCode,
            subjectTitle: parsed.subjectTitle,
            component: parsed.component,
          },
        };
      },
    });

    return () => draggable.destroy();
  }, [preferredSubjects, availableSubjects, usedSubjectComponents]);

  function syncEventApi(event: EventApi) {
    if (!event.start || !event.end) return;

    setEvents((current) =>
      current.map((item) =>
        item.id === event.id
          ? {
              ...item,
              title: event.title,
              start: formatLocalDateTime(event.start as Date),
              end: formatLocalDateTime(event.end as Date),
            }
          : item
      )
    );
  }

  function handleExternalReceive(info: { event: EventApi }) {
    const received = info.event;
    if (!received.start || !received.end) {
      received.remove();
      return;
    }

    const subjectCode = String(received.extendedProps.subjectCode ?? "").toUpperCase();
    const component = received.extendedProps.component as PreferenceComponent | undefined;

    if (!subjectCode || !component) {
      received.remove();
      return;
    }

    const uniqueKey = `${subjectCode}::${component}`;
    if (usedSubjectComponents.has(uniqueKey)) {
      received.remove();
      window.alert(`${subjectCode} ${component} already has a preferred time. Move or resize the existing block instead.`);
      return;
    }

    const stored: StoredPreferenceEvent = {
      id: makeId(),
      title: `${subjectCode} — ${component}`,
      start: formatLocalDateTime(received.start),
      end: formatLocalDateTime(received.end),
      kind: "subject",
      subjectCode,
      subjectTitle: received.extendedProps.subjectTitle,
      component,
    };

    received.remove();
    setEvents((current) => [...current, stored]);
  }

  function handleSelect(selection: DateSelectArg) {
    setEvents((current) => [
      ...current,
      {
        id: makeId(),
        title: "Preferred Teaching Time",
        start: formatLocalDateTime(selection.start),
        end: formatLocalDateTime(selection.end),
        kind: "general",
      },
    ]);
  }

  function openEventEditor(info: EventClickArg) {
    const found = events.find((event) => event.id === info.event.id);
    if (!found) return;

    setSelectedEventId(found.id);
    setEditDay(eventDayName(found) || "Monday");
    setEditStart(getTimePart(found.start));
    setEditEnd(getTimePart(found.end));
  }

  function saveEditedEvent() {
    if (!selectedEvent) return;
    if (editEnd <= editStart) {
      window.alert("End time must be later than start time.");
      return;
    }

    const date = REFERENCE_DATES[editDay];
    setEvents((current) =>
      current.map((event) =>
        event.id === selectedEvent.id
          ? { ...event, start: `${date}T${editStart}:00`, end: `${date}T${editEnd}:00` }
          : event
      )
    );
    setSelectedEventId(null);
  }

  function removeSelectedEvent() {
    if (!selectedEvent) return;
    setEvents((current) => current.filter((event) => event.id !== selectedEvent.id));
    setSelectedEventId(null);
  }

  function clearCalendar() {
    if (window.confirm("Clear all preferred teaching times and subject placements?")) {
      setEvents([]);
    }
  }

  function getSubjectRank(subjectCode: string) {
    const index = preferredSubjects.findIndex(
      (item) => item.toUpperCase() === subjectCode.toUpperCase()
    );
    return index >= 0 ? index + 1 : null;
  }

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">Draggable Subject Preferences</h3>
            <p className="mt-1 text-sm text-slate-500">
              Drag one Lecture or Laboratory card into the weekly calendar. Each subject component can have only one preferred time.
            </p>
          </div>
          <div className="rounded-full bg-purple-100 px-3 py-1 text-xs font-semibold text-purple-700">
            Soft preferences only
          </div>
        </div>

        <div ref={trayRef} className="mt-4 flex flex-wrap gap-3">
          {preferredSubjects.length === 0 ? (
            <p className="text-sm text-slate-500">Add preferred subjects first.</p>
          ) : (
            preferredSubjects.flatMap((subjectCode) => {
              const details = subjectMap.get(subjectCode.toUpperCase());
              const title = details?.subject_title ?? "";

              return (["Lecture", "Laboratory"] as PreferenceComponent[]).map((component) => {
                const key = `${subjectCode.toUpperCase()}::${component}`;
                const used = usedSubjectComponents.has(key);
                const eventData = JSON.stringify({
                  subjectCode: subjectCode.toUpperCase(),
                  subjectTitle: title,
                  component,
                  title: `${subjectCode.toUpperCase()} — ${component}`,
                });

                return (
                  <div
                    key={key}
                    data-event={eventData}
                    className={[
                      "faculty-pref-draggable min-w-[190px] rounded-xl border px-4 py-3 shadow-sm transition",
                      used
                        ? "cursor-not-allowed border-slate-200 bg-slate-100 opacity-50"
                        : "cursor-grab border-purple-200 bg-white hover:border-purple-400 hover:shadow",
                    ].join(" ")}
                    style={{ pointerEvents: used ? "none" : "auto" }}
                  >
                    <div className="text-sm font-semibold text-slate-900">{subjectCode.toUpperCase()}</div>
                    <div className="text-xs font-medium text-purple-700">{component}</div>
                    {title && (
                      <div className="mt-1 max-w-[220px] truncate text-xs text-slate-500" title={title}>
                        {title}
                      </div>
                    )}
                    <div className="mt-2 text-[11px] text-slate-400">
                      {used ? "Placed on calendar" : "Drag to preferred time"}
                    </div>
                  </div>
                );
              });
            })
          )}
        </div>

        <p className="mt-3 text-xs text-slate-500">
          UI checkpoint: the current subject endpoint only gives code and title, so both Lecture and Laboratory cards are shown for now. We will connect actual lecture/lab hours in the backend checkpoint.
        </p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">Preferred Weekly Schedule</h3>
            <p className="mt-1 text-sm text-slate-500">
              Drag empty calendar space to create a general preferred period. Move and resize blocks in 30-minute increments.
            </p>
          </div>
          <button
            type="button"
            onClick={clearCalendar}
            className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
          >
            Clear Preferred Times
          </button>
        </div>

        <style>{`
          .faculty-preference-calendar .fc {
            font-size: 12px;
          }

          .faculty-preference-calendar .fc-theme-standard td,
          .faculty-preference-calendar .fc-theme-standard th {
            border-color: #dbe4ec;
          }

          .faculty-preference-calendar .fc-scrollgrid {
            border-radius: 10px;
            overflow: hidden;
          }

          .faculty-preference-calendar .fc-col-header-cell {
            background: #0f6663;
            border-color: #2f7a77 !important;
          }

          .faculty-preference-calendar .fc-col-header-cell-cushion {
            display: block;
            padding: 10px 6px;
            color: #ffffff;
            font-weight: 700;
            text-decoration: none;
          }

          .faculty-preference-calendar .fc-timegrid-axis {
            background: #0f6663;
            border-color: #2f7a77 !important;
          }

          .faculty-preference-calendar
          .fc-col-header
          .fc-timegrid-axis-frame::before {
            content: "Time";
            color: #ffffff;
            font-weight: 700;
          }

          .faculty-preference-calendar
          .fc-col-header
          .fc-timegrid-axis-frame {
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .faculty-preference-calendar .fc-timegrid-slot-label {
            background: #ffffff;
            vertical-align: middle;
          }

          .faculty-preference-calendar .fc-timegrid-slot-label-cushion {
            padding: 0 8px;
            color: #475569;
            font-size: 10px;
            white-space: nowrap;
          }

          .faculty-preference-calendar .fc-timegrid-slot {
            height: 29px;
            background: #ffffff;
          }

          .faculty-preference-calendar .fc-timegrid-col {
            background: #ffffff;
          }

          .faculty-preference-calendar
          .fc-timegrid-col.fc-day-today {
            background: #ffffff !important;
          }

          .faculty-preference-calendar
          .fc-col-header-cell.fc-day-today {
            background: #0f6663 !important;
          }

          .faculty-preference-calendar
          .fc-col-header-cell.fc-day-today
          .fc-col-header-cell-cushion {
            color: #ffffff !important;
          }

          .faculty-preference-calendar .fc-timegrid-now-indicator-line,
          .faculty-preference-calendar .fc-timegrid-now-indicator-arrow {
            display: none;
          }

          .faculty-preference-calendar .fc-event {
            border-radius: 5px;
            box-shadow: none;
          }

          .faculty-preference-calendar .fc-event-main {
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
          }
        `}</style>

        <div
          className="
            faculty-preference-calendar
            overflow-x-auto
            rounded-xl
            border
            border-slate-200
          "
        >
          <div className="min-w-[1050px]">
            <FullCalendar
              plugins={[
                timeGridPlugin,
                interactionPlugin,
              ]}
              initialView="timeGridWeek"
              initialDate="2026-09-28"
              headerToolbar={false}
              firstDay={1}
              hiddenDays={[0]}
              dayHeaderFormat={{
                weekday: "long",
              }}
              allDaySlot={false}
              slotMinTime="07:30:00"
              slotMaxTime="22:00:00"
              slotDuration="00:30:00"
              snapDuration="00:30:00"
              slotLabelInterval="00:30:00"
              slotLabelContent={(arg) =>
                formatSlotRange(arg.date)
              }
              editable
              eventStartEditable
              eventDurationEditable
              droppable
              selectable
              selectMirror
              eventOverlap
              selectOverlap
              nowIndicator={false}
              height="auto"
              events={events}
              select={handleSelect}
              eventReceive={handleExternalReceive}
              eventChange={(info) => syncEventApi(info.event)}
              eventClick={openEventEditor}
              eventDidMount={(info) => {
                const kind = info.event.extendedProps.kind;
                const component = info.event.extendedProps.component;
                if (kind === "general") {
                  info.el.style.backgroundColor = "#f97316";
                  info.el.style.borderColor = "#ea580c";
                } else if (component === "Laboratory") {
                  info.el.style.backgroundColor = "#0f766e";
                  info.el.style.borderColor = "#115e59";
                } else {
                  info.el.style.backgroundColor = "#7e22ce";
                  info.el.style.borderColor = "#6b21a8";
                }
              }}
              eventContent={(arg) => {
                const subjectCode = arg.event.extendedProps.subjectCode as string | undefined;
                const rank = subjectCode ? getSubjectRank(subjectCode) : null;
                const component =
                  arg.event.extendedProps
                    .component as
                    PreferenceComponent | undefined;

                return (
                  <div
                    className="
                      w-full
                      overflow-hidden
                      px-1
                      py-1
                      text-center
                      text-[10px]
                      leading-tight
                      text-white
                    "
                  >
                    <div className="truncate font-bold">
                      {
                        subjectCode
                        ?? arg.event.title
                      }
                    </div>

                    {component && (
                      <div className="mt-0.5 truncate opacity-95">
                        {component}
                      </div>
                    )}

                    {subjectCode && rank && (
                      <div className="mt-0.5 truncate opacity-90">
                        {ordinal(rank)} preference
                      </div>
                    )}

                    <div className="mt-0.5 truncate opacity-90">
                      {arg.timeText}
                    </div>
                  </div>
                );
              }}
            />
          </div>
        </div>
      </div>

      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Edit Preference</h3>
                <p className="mt-1 text-sm text-slate-500">{selectedEvent.title}</p>
              </div>
              <button type="button" onClick={() => setSelectedEventId(null)} className="rounded-lg px-3 py-1 text-slate-500 hover:bg-slate-100">✕</button>
            </div>

            <div className="mt-5 grid gap-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">Day</label>
                <select value={editDay} onChange={(event) => setEditDay(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2">
                  {Object.keys(REFERENCE_DATES).map((day) => <option key={day} value={day}>{day}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Start</label>
                  <input type="time" step={1800} min="07:30" max="21:30" value={editStart} onChange={(event) => setEditStart(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2" />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">End</label>
                  <input type="time" step={1800} min="08:00" max="22:00" value={editEnd} onChange={(event) => setEditEnd(event.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2" />
                </div>
              </div>

              {selectedEvent.kind === "subject" && selectedEvent.subjectCode && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-slate-700">Subject Preference Rank</label>
                  <select
                    value={getSubjectRank(selectedEvent.subjectCode) ?? 1}
                    onChange={(event) => onSetSubjectRank(selectedEvent.subjectCode!, Number(event.target.value))}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2"
                  >
                    {preferredSubjects.map((_, index) => <option key={index + 1} value={index + 1}>{ordinal(index + 1)}</option>)}
                  </select>
                </div>
              )}
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
              <button type="button" onClick={removeSelectedEvent} className="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50">Remove</button>
              <div className="flex gap-2">
                <button type="button" onClick={() => setSelectedEventId(null)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">Cancel</button>
                <button type="button" onClick={saveEditedEvent} className="rounded-lg bg-purple-700 px-4 py-2 text-sm font-medium text-white hover:bg-purple-800">Apply Changes</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
