import { useEffect, useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import interactionPlugin, { Draggable } from "@fullcalendar/interaction";
import type { AvailableSubject, SubjectComponent } from "../../api/subjects";
import type { PreferenceScheduleBlock } from "../../api/preferences";
import {
  CALENDAR_EDITING, DAYS, DAY_NAMES, REFERENCE_DATES, addComponentPreference,
  durationLabel, matchingPattern, minutes, moveBlock, patternLabel, realComponents, removeBlock, timeString,
} from "./preferenceModel";

interface Props {
  subjects: AvailableSubject[];
  blocks: PreferenceScheduleBlock[];
  onChange: (blocks: PreferenceScheduleBlock[]) => void;
}
type Placement = { subject: AvailableSubject; component: SubjectComponent };
type SourceChoice = { patternIndex: string; dayPair: string };
const componentKey = (subject: AvailableSubject, component: SubjectComponent) => `${subject.subject_code}-${component.type}`;
function datePosition(date: Date) {
  const localDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  return { day: Object.keys(REFERENCE_DATES).find(key => REFERENCE_DATES[key] === localDate) ?? "", start: timeString(date.getHours() * 60 + date.getMinutes()) };
}
function displayTime(date: Date | null) {
  if (!date) return "";
  const hour = date.getHours();
  return `${hour % 12 || 12}:${String(date.getMinutes()).padStart(2, "0")} ${hour < 12 ? "AM" : "PM"}`;
}

export default function PreferenceCalendar({ subjects, blocks, onChange }: Props) {
  const [placement, setPlacement] = useState<Placement | null>(null);
  const [patternIndex, setPatternIndex] = useState("");
  const [dayPair, setDayPair] = useState("");
  const [general, setGeneral] = useState(false);
  const [editing, setEditing] = useState<PreferenceScheduleBlock | null>(null);
  const [day, setDay] = useState("M");
  const [start, setStart] = useState("08:00");
  const [end, setEnd] = useState("10:00");
  const [error, setError] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [sourceChoices, setSourceChoices] = useState<Record<string, SourceChoice>>({});
  const sourceContainer = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const pattern = placement && patternIndex !== "" ? placement.component.meeting_patterns[Number(patternIndex)] : null;
  useEffect(() => {
    if (!sourceContainer.current) return;
    const draggable = new Draggable(sourceContainer.current, {
      itemSelector: '[data-component-drag="true"]',
      eventData: element => ({
        title: `${element.dataset.subjectCode} ${element.dataset.componentType}`,
        duration: { minutes: Number(element.dataset.duration) },
        extendedProps: { kind: "subject", subject_code: element.dataset.subjectCode, component: element.dataset.componentType },
        // Create through the controlled preference model, including complete paired meetings.
        create: false,
      }),
    });
    return () => draggable.destroy();
  }, []);
  const close = () => { dialog.current?.close(); setModalOpen(false); setPlacement(null); setEditing(null); setGeneral(false); setError(""); };
  function openPlacement(subject: AvailableSubject, component: SubjectComponent, choice: SourceChoice) {
    setPlacement({ subject, component }); setEditing(null); setGeneral(false);
    setPatternIndex(choice.patternIndex);
    setDayPair(choice.dayPair); setDay("M"); setStart("08:00"); setError("");
    dialog.current?.showModal(); setModalOpen(true);
  }
  function openGeneral(selectedDay = "M", selectedStart = "08:00", selectedEnd = "10:00") {
    setGeneral(true); setPlacement(null); setEditing(null); setDay(selectedDay);
    setStart(selectedStart); setEnd(selectedEnd); setError(""); dialog.current?.showModal(); setModalOpen(true);
  }
  function openEdit(block: PreferenceScheduleBlock) {
    setEditing(block); setPlacement(null); setGeneral(false);
    setDay(block.day); setStart(block.start_time); setError(""); dialog.current?.showModal(); setModalOpen(true);
  }
  function removePreference(block: PreferenceScheduleBlock) {
    const subject = subjects.find(item => item.subject_code === block.subject_code);
    const component = subject?.components.find(item => item.type === block.component);
    if (subject && component) {
      const group = blocks.filter(item => item.kind === "subject" && item.subject_code === block.subject_code && item.component === block.component);
      const placedPattern = matchingPattern(group, component);
      if (placedPattern) setSourceChoices(current => ({ ...current, [componentKey(subject, component)]: {
        patternIndex: String(component.meeting_patterns.indexOf(placedPattern)),
        dayPair: String(placedPattern.day_combinations.findIndex(days => days.every(item => group.some(meeting => meeting.day === item)))),
      } }));
    }
    onChange(removeBlock(blocks, block));
  }
  function submit(event: React.SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      if (editing) onChange(moveBlock(blocks, editing.id, day, start, subjects));
      else if (general) {
        if (!DAYS.includes(day) || !Number.isFinite(minutes(start)) || !Number.isFinite(minutes(end)) || minutes(start) < 450 || minutes(end) > 1320 || minutes(end) <= minutes(start)) throw new Error("Choose a period between 7:30 AM and 10 PM, ending after it starts.");
        onChange([...blocks, { id: crypto.randomUUID(), kind: "general", day, start_time: start, end_time: end }]);
      } else if (placement && pattern) {
        const days = pattern.meetings_per_week === 1 ? [day] : pattern.day_combinations[Number(dayPair)];
        if (!days || (pattern.meetings_per_week > 1 && dayPair === "")) throw new Error("Choose the meeting days.");
        onChange(addComponentPreference(blocks, placement.subject, placement.component, pattern, days, start));
        setSourceChoices(current => ({ ...current, [componentKey(placement.subject, placement.component)]: { patternIndex, dayPair } }));
      } else throw new Error("Choose a meeting pattern before adding the component.");
      close();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to place this preference."); }
  }
  const events = blocks.filter(block => REFERENCE_DATES[block.day] && Number.isFinite(minutes(block.start_time)) && Number.isFinite(minutes(block.end_time))).map(block => ({
    id: block.id,
    title: block.kind === "general" ? "General preferred period" : `${block.subject_code} · ${block.component}`,
    start: `${REFERENCE_DATES[block.day]}T${block.start_time}:00`, end: `${REFERENCE_DATES[block.day]}T${block.end_time}:00`,
    // Reuse WeeklySchedule's pale blue/teal block palette and neutral time-column style.
    backgroundColor: block.kind === "general" ? "#f1f5f9" : block.component === "Laboratory" ? "#CCFBF1" : "#DBEAFE",
    borderColor: block.kind === "general" ? "#cbd5e1" : block.component === "Laboratory" ? "#2DD4BF" : "#60A5FA",
    textColor: block.kind === "general" ? "#334155" : block.component === "Laboratory" ? "#134E4A" : "#1E3A8A",
    classNames: ["preference-schedule-block", block.kind === "general" ? "preference-block-general" : block.component === "Laboratory" ? "preference-block-laboratory" : "preference-block-lecture"],
    durationEditable: false,
    extendedProps: { kind: block.kind, subject_code: block.subject_code, component: block.component },
  }));
  return <div ref={sourceContainer} className="space-y-3">
    <p className="pt-3 text-xs text-slate-500">Drag a subject component onto your preferred day and time. Meetings can be moved, but their required duration cannot be changed.</p>
    <div className="flex flex-wrap gap-3 text-xs text-slate-600" aria-label="Preference calendar legend"><span className="preference-legend-item"><i className="preference-legend-general" aria-hidden="true" />General Preference</span><span className="preference-legend-item"><i className="preference-legend-lecture" aria-hidden="true" />Lecture</span><span className="preference-legend-item"><i className="preference-legend-laboratory" aria-hidden="true" />Laboratory</span></div>
    <section className="preference-component-tray" aria-labelledby="draggable-subject-preferences-title">
      <h3 id="draggable-subject-preferences-title" className="mb-2 text-sm font-semibold text-slate-800">Draggable Subject Preferences</h3>
    {subjects.length === 0 ? <p className="preference-tray-empty">Select a preferred subject above to schedule its components.</p> :
      <div className="preference-component-tray-cards">
        {subjects.flatMap(subject => realComponents(subject).map(component => {
          const key = componentKey(subject, component);
          const group = blocks.filter(block => block.kind === "subject" && block.subject_code === subject.subject_code && block.component === component.type);
          const placed = group.length > 0;
          const placedPattern = matchingPattern(group, component);
          const choice = placedPattern ? {
            patternIndex: String(component.meeting_patterns.indexOf(placedPattern)),
            dayPair: String(placedPattern.day_combinations.findIndex(days => days.every(day => group.some(block => block.day === day)))),
          } : sourceChoices[key] ?? { patternIndex: component.meeting_patterns.length === 1 ? "0" : "", dayPair: "" };
          const selectedPattern = choice.patternIndex !== "" ? component.meeting_patterns[Number(choice.patternIndex)] : undefined;
          const pair = selectedPattern && choice.dayPair !== "" ? selectedPattern.day_combinations[Number(choice.dayPair)] : undefined;
          const ready = component.metadata_status === "supported" && !!selectedPattern && (selectedPattern.meetings_per_week === 1 || !!pair);
          const meetingDays = selectedPattern && selectedPattern.meetings_per_week > 1 ? pair ?? [] : [""];
          return <div key={key} className="preference-component-card" data-subject-code={subject.subject_code} data-component-type={component.type} data-paired={selectedPattern && selectedPattern.meetings_per_week > 1 && !!pair ? "true" : "false"}>
            <div className="preference-component-patterns">
            {component.meeting_patterns.length > 1 && <label className="preference-label"><span className="sr-only">Meeting pattern for {subject.subject_code} {component.type}</span><select aria-label={`Meeting pattern for ${subject.subject_code} ${component.type}`} className="preference-input" disabled={placed} value={choice.patternIndex} onChange={event => setSourceChoices(current => ({ ...current, [key]: { patternIndex: event.target.value, dayPair: "" } }))}>
              <option value="">Choose a meeting pattern</option>{component.meeting_patterns.map((option, index) => <option key={index} value={index}>{patternLabel(option)}</option>)}
            </select></label>}
            {selectedPattern && selectedPattern.meetings_per_week > 1 && <label className="preference-label"><span className="sr-only">Meeting days for {subject.subject_code} {component.type}</span><select aria-label={`Meeting days for ${subject.subject_code} ${component.type}`} className="preference-input" disabled={placed} value={choice.dayPair} onChange={event => setSourceChoices(current => ({ ...current, [key]: { ...choice, dayPair: event.target.value } }))}>
              <option value="">Choose meeting days</option>{selectedPattern.day_combinations.map((days, index) => <option key={index} value={index}>{days.map(item => DAY_NAMES[item]).join(" & ")}</option>)}
            </select></label>}
            </div>
            <div className="preference-component-meetings">
            {meetingDays.map((meetingDay, index) => <div key={index} className="preference-component-drag" role="group" aria-label={`Drag ${subject.subject_code} ${component.type}${meetingDay ? ` meeting ${index + 1} on ${DAY_NAMES[meetingDay]}` : ""} to calendar`} aria-disabled={!ready || placed}
              data-component-drag={ready && !placed ? "true" : "false"} data-subject-code={subject.subject_code} data-component-type={component.type} data-pattern-index={choice.patternIndex} data-day-pair={choice.dayPair} data-meeting-day={meetingDay} data-duration={selectedPattern?.duration_minutes}>
              <div className="flex items-center justify-between gap-2"><strong className="text-sm">{subject.subject_code}</strong><span aria-hidden="true" className="text-slate-400">⠿</span></div>
              <p className="preference-component-title" title={subject.subject_title}>{subject.subject_title}</p>
              <p className="mt-1 text-xs font-medium">{component.type.toUpperCase()}{meetingDay ? ` · ${DAY_NAMES[meetingDay]}` : ""}</p>
              <p className="my-1 text-xs font-medium">{durationLabel(selectedPattern?.duration_minutes ?? component.weekly_hours * 60)}{!selectedPattern ? " per week" : ""}{component.type === "Laboratory" && component.continuous ? " · Continuous" : ""}</p>
              <p className="text-xs text-slate-500">{placed ? placedPattern ? "✓ Placed" : "Placed · Review older preference" : ready ? "Drag to preferred time" : "Choose a meeting pattern first"}</p>
            </div>)}
            </div>
            {selectedPattern && selectedPattern.meetings_per_week > 1 && <p className="mt-1 text-xs text-slate-500">Drag either card to place both meetings. Move their start times separately.</p>}
            <button type="button" className="preference-button preference-add-fallback" aria-label={`Add ${subject.subject_code} ${component.type} preference`} disabled={placed || component.metadata_status !== "supported"} onClick={() => openPlacement(subject, component, choice)}>
              {placed ? "Added" : component.metadata_status !== "supported" ? "Meeting pattern unavailable" : "Add"}
            </button>
          </div>;
        }))}
      </div>}
    </section>
    <section className="preference-weekly-schedule" aria-labelledby="preferred-weekly-schedule-title">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 id="preferred-weekly-schedule-title" className="preference-timetable-heading text-sm font-semibold text-slate-800">Preferred Weekly Schedule</h3>
        <button type="button" className="preference-button preference-general-action" onClick={() => openGeneral()}>+ Add General Preferred Period</button>
      </div>
    <div className="preference-calendar overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
    <div className="preference-timetable">
      <FullCalendar plugins={[timeGridPlugin, interactionPlugin]} initialView="timeGridWeek" initialDate="2026-09-28"
        validRange={{ start: "2026-09-28", end: "2026-10-04" }} hiddenDays={[0]} headerToolbar={false} dayHeaderFormat={{ weekday: "long" }}
        dayHeaderClassNames={["bg-[#115E59]", "text-white", "text-sm", "font-semibold", "text-center"]}
        height="auto" allDaySlot={false} slotMinTime="07:30:00" slotMaxTime="22:00:00" slotDuration="00:30:00" snapDuration="00:30:00"
        slotLabelInterval="00:30:00" slotLabelFormat={{ hour: "numeric", minute: "2-digit", omitZeroMinute: false, meridiem: "short" }}
        slotLabelClassNames={["bg-slate-50", "text-xs", "text-slate-600", "text-center"]}
        slotLabelContent={info => { const start = info.date.getHours() * 60 + info.date.getMinutes(); return `${timeString(start)}–${timeString(start + 30)}`; }}
        eventContent={info => {
          const { kind, subject_code: code, component } = info.event.extendedProps;
          const subject = subjects.find(item => item.subject_code === code);
          const timeRange = `${displayTime(info.event.start)} – ${displayTime(info.event.end)}`;
          const duration = info.event.start && info.event.end ? (info.event.end.getTime() - info.event.start.getTime()) / 60000 : 0;
          // Match generated schedule blocks: centered code, title, component, then time.
          return <div className={`preference-block-content flex h-full flex-col items-center justify-center overflow-hidden px-2 py-2 text-center${duration <= 60 ? " preference-block-short" : ""}`}>
            {kind === "subject" ? <><p className="text-xs font-bold">{code}</p><p className="mt-1 line-clamp-2 text-[11px] font-semibold">{subject?.subject_title ?? "Subject details unavailable"}</p><p className="mt-1 text-[10px] font-medium">{component}</p></> : <p className="text-xs font-semibold">General preferred period</p>}
            <p className="preference-block-time mt-1 text-[10px]">{timeRange}</p>
          </div>;
        }}
        editable {...CALENDAR_EDITING} selectable selectMirror events={events} droppable
        dropAccept={element => element.dataset.componentDrag === "true" && !element.closest("fieldset:disabled")}
        drop={info => {
          try {
            const element = info.draggedEl;
            if (element.dataset.componentDrag !== "true" || element.closest("fieldset:disabled")) return;
            const subject = subjects.find(item => item.subject_code === element.dataset.subjectCode);
            const component = subject?.components.find(item => item.type === element.dataset.componentType);
            const selectedPattern = component?.meeting_patterns[Number(element.dataset.patternIndex)];
            if (!subject || !component || !selectedPattern) throw new Error("Choose a supported meeting pattern before dragging.");
            const target = datePosition(info.date);
            if (element.dataset.meetingDay && element.dataset.meetingDay !== target.day) throw new Error(`Drop this meeting on ${DAY_NAMES[element.dataset.meetingDay]}.`);
            const days = selectedPattern.meetings_per_week === 1 ? [target.day] : selectedPattern.day_combinations[Number(element.dataset.dayPair)];
            if (!days) throw new Error("Choose the supported meeting days before dragging.");
            onChange(addComponentPreference(blocks, subject, component, selectedPattern, days, target.start)); setError("");
          } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to place this component."); }
        }}
        eventClick={info => { const block = blocks.find(item => item.id === info.event.id); if (block) openEdit(block); }}
        eventDrop={info => {
          try {
            const date = info.event.start;
            if (!date) throw new Error("Choose a teaching day.");
            const target = datePosition(date);
            onChange(moveBlock(blocks, info.event.id, target.day, target.start, subjects)); setError("");
          } catch (reason) { info.revert(); setError(reason instanceof Error ? reason.message : "Unable to move this meeting."); }
        }}
        select={info => {
          const selectedDay = DAYS[info.start.getDay() - 1];
          if (selectedDay && info.start.getDay() === info.end.getDay()) openGeneral(selectedDay, timeString(info.start.getHours() * 60 + info.start.getMinutes()), timeString(info.end.getHours() * 60 + info.end.getMinutes()));
          info.view.calendar.unselect();
        }} />
      <div className="preference-timetable-end"><span>10:00 PM</span></div>
    </div>
    </div>
    </section>
    {error && !modalOpen && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {blocks.length > 0 && <details className="preference-meeting-controls"><summary className="cursor-pointer text-xs text-slate-500">Meeting details and keyboard controls ({blocks.length})</summary>
      <ul className="mt-3 space-y-2">{blocks.map(block => <li key={block.id} className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2 text-sm">
        <span>{block.kind === "general" ? "General preferred period" : `${block.subject_code} ${block.component ?? "meeting"}`} · {DAY_NAMES[block.day] ?? block.day} · {block.start_time}–{block.end_time}</span>
        <span className="flex gap-2"><button type="button" className="preference-button" onClick={() => openEdit(block)} aria-label={`Move ${block.kind === "general" ? "general period" : `${block.subject_code} ${block.component}`} on ${DAY_NAMES[block.day]}`}>Move</button>
          <button type="button" className="preference-button" onClick={() => removePreference(block)} aria-label={`Remove ${block.kind === "general" ? "general period" : `${block.subject_code} ${block.component} preference`}`}>Remove</button></span>
      </li>)}</ul>
    </details>}
    <dialog ref={dialog} className="preference-dialog" aria-labelledby="placement-title" onCancel={close}>
      <form onSubmit={submit} className="space-y-4">
        <h3 id="placement-title" className="text-lg font-semibold">{editing ? "Move preference" : general ? "General preferred period" : `${placement?.subject.subject_code ?? ""} ${placement?.component.type ?? ""} preference`}</h3>
        {placement && <>
          <label className="preference-label">Meeting pattern<select required className="preference-input" value={patternIndex} onChange={event => { setPatternIndex(event.target.value); setDayPair(""); }}>
            <option value="">Choose a meeting pattern</option>{placement.component.meeting_patterns.map((option, index) => <option key={index} value={index}>{patternLabel(option)}</option>)}
          </select></label>
          {pattern && pattern.meetings_per_week > 1 && <><label className="preference-label">Meeting days<select required className="preference-input" value={dayPair} onChange={event => setDayPair(event.target.value)}>
            <option value="">Choose meeting days</option>{pattern.day_combinations.map((days, index) => <option key={index} value={index}>{days.map(item => DAY_NAMES[item]).join(" & ")}</option>)}
          </select></label><p className="text-sm text-slate-600">Both meetings start at the time below. You can move their start times separately afterward, keeping the selected day pair. Removing either removes this component preference.</p></>}
        </>}
        {(!pattern || pattern.meetings_per_week === 1) && <label className="preference-label">Day<select className="preference-input" value={day} onChange={event => setDay(event.target.value)}>
          {(pattern ? pattern.day_combinations.map(days => days[0]) : DAYS).map(item => <option key={item} value={item}>{DAY_NAMES[item]}</option>)}
        </select></label>}
        <label className="preference-label">Start time<input required className="preference-input" type="time" min="07:30" max="21:59" step="60" value={start} onChange={event => setStart(event.target.value)} /></label>
        {general ? <label className="preference-label">End time<input required className="preference-input" type="time" min="07:31" max="22:00" step="60" value={end} onChange={event => setEnd(event.target.value)} /></label>
          : <p className="text-sm text-slate-600">Fixed duration: {durationLabel(editing ? minutes(editing.end_time) - minutes(editing.start_time) : pattern?.duration_minutes ?? 0)}{(editing || pattern) && Number.isFinite(minutes(start)) ? ` · Ends at ${timeString(minutes(start) + (editing ? minutes(editing.end_time) - minutes(editing.start_time) : pattern!.duration_minutes))}` : ""}</p>}
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className="preference-button" onClick={close}>Cancel</button><button type="submit" className="preference-button preference-primary">{editing ? "Move preference" : "Add preference"}</button></div>
      </form>
    </dialog>
  </div>;
}
