import { test } from "node:test";
import assert from "node:assert/strict";
import { faculty, subjects, subject, component, pattern, preference } from "./preferenceFixtures.mjs";
import { CALENDAR_EDITING, IMPORTANCE_OPTIONS, normalFaculty, isEligible, filterSubjects, realComponents, createComponentBlocks, addComponentPreference, moveBlock, durationLabel, patternLabel, rankSubject, importanceVisible, isDirty, withBlocks, editablePreference, validationIssues, removeBlock } from "../src/components/faculty/preferenceModel.ts";

test("normal faculty selector excludes external instructors", () => {
  assert.deepEqual(normalFaculty([...faculty, { faculty_id: "external", instructor_type: "preassigned_external" }]), faculty);
});
test("eligibility and preassignment, not domain or prefix, authorize selection", () => {
  assert.equal(isEligible(subjects[3]), false);
  assert.equal(isEligible({ ...subjects[0], offerings: [{ can_be_assigned: false }] }), false);
  assert.equal(isEligible({ ...subjects[0], eligibility: null }), false);
  assert.deepEqual(filterSubjects(subjects, "ALL", "").map(s => s.subject_code), ["CCC100", "ITD105", "ITN102"]);
});
test("categories and code/title search are independent browsing filters", () => {
  assert.deepEqual(filterSubjects(subjects, "ITD", "data"), [subjects[1]]);
  assert.deepEqual(filterSubjects(subjects, "ALL", "ccc100"), [subjects[0]]);
  assert.deepEqual(filterSubjects(subjects, "ITN", "data"), []);
  assert.equal(filterSubjects(subjects, "ALL", "", true).length, 4);
});
test("no fake labs or lectures, and zero hour metadata is not rendered", () => {
  assert.deepEqual(realComponents(subjects[1]).map(c => c.type), ["Lecture"]);
  assert.deepEqual(realComponents(subjects[2]).map(c => c.type), ["Laboratory"]);
  assert.deepEqual(realComponents(subject("ZERO", "None", [component("Lecture", 0, [])])), []);
});
test("duration labels reflect real metadata and supported alternatives", () => {
  assert.equal(durationLabel(120), "2 hours"); assert.equal(durationLabel(180), "3 hours");
  assert.equal(patternLabel(pattern(2, 90)), "Two 1.5-hour meetings");
});
test("calendar supports moving and prohibits both forms of resizing", () => {
  assert.equal(CALENDAR_EDITING.eventStartEditable, true);
  assert.equal(CALENDAR_EDITING.eventDurationEditable, false);
  assert.equal(CALENDAR_EDITING.eventResizableFromStart, false);
});
test("moving a lab always uses authoritative 180 minute duration", () => {
  const lab = subjects[0].components[1];
  const blocks = createComponentBlocks(subjects[0], lab, lab.meeting_patterns[0], ["M"], "08:00");
  const moved = moveBlock(blocks, blocks[0].id, "T", "13:00", subjects);
  assert.equal(moved[0].end_time, "16:00");
  assert.throws(() => moveBlock(blocks, blocks[0].id, "T", "20:00", subjects));
  assert.throws(() => moveBlock([{ ...blocks[0], end_time: "14:00" }], blocks[0].id, "T", "08:00", subjects));
});
test("moving lectures preserves 60,120,180 or 90 minute backend requirements", () => {
  for (const duration of [60, 120, 180]) {
    const part = component("Lecture", duration / 60, [pattern(1, duration)]);
    const s = subject("CCC999", "Metadata example", [part]);
    const blocks = createComponentBlocks(s, part, part.meeting_patterns[0], ["M"], "08:00");
    const moved = moveBlock(blocks, blocks[0].id, "W", "13:00", [s]);
    assert.equal(moved[0].end_time, `${13 + duration / 60}:00`);
  }
});
test("ineligible components and guessed patterns cannot be placed", () => {
  const part = subjects[3].components[0];
  assert.throws(() => createComponentBlocks(subjects[3], part, part.meeting_patterns[0], ["M"], "08:00"));
  assert.throws(() => createComponentBlocks(subjects[0], subjects[0].components[0], pattern(1, 360), ["M"], "08:00"));
});
test("two lecture meetings are a complete removable group and move independently", () => {
  const part = subjects[1].components[0];
  const blocks = createComponentBlocks(subjects[1], part, part.meeting_patterns[1], ["M", "TH"], "08:00");
  const moved = moveBlock(blocks, blocks[0].id, "M", "13:00", subjects);
  assert.equal(moved[0].end_time, "14:30"); assert.equal(moved[1].start_time, "08:00");
  assert.throws(() => moveBlock(blocks, blocks[0].id, "T", "08:00", subjects));
  assert.deepEqual(removeBlock(blocks, blocks[0]), []);
  assert.equal(validationIssues({ ...preference, preferred_subjects: ["ITD105"], preferred_schedule_blocks: blocks }, subjects).length, 0);
  assert.ok(validationIssues({ ...preference, preferred_subjects: ["ITD105"], preferred_schedule_blocks: blocks.slice(0, 1) }, subjects).length > 0);
});
test("external placement uses the exact dropped start and rejects a placed component", () => {
  const part = subjects[0].components[0];
  const blocks = addComponentPreference([], subjects[0], part, part.meeting_patterns[0], ["M"], "10:30");
  assert.equal(blocks[0].start_time, "10:30"); assert.equal(blocks[0].end_time, "12:30");
  assert.throws(() => addComponentPreference(blocks, subjects[0], part, part.meeting_patterns[0], ["T"], "13:00"), /already placed/);
  const cleared = removeBlock(blocks, blocks[0]);
  assert.equal(addComponentPreference(cleared, subjects[0], part, part.meeting_patterns[0], ["W"], "13:00")[0].end_time, "15:00");
});
test("paired external placement stays complete and cannot be duplicated with another pattern", () => {
  const part = subjects[1].components[0];
  const blocks = addComponentPreference([], subjects[1], part, part.meeting_patterns[1], ["M", "TH"], "10:30");
  assert.equal(blocks.length, 2); assert.ok(blocks.every(block => block.end_time === "12:00"));
  assert.throws(() => addComponentPreference(blocks, subjects[1], part, part.meeting_patterns[0], ["T"], "13:00"), /already placed/);
  assert.equal(validationIssues({ ...preference, preferred_subjects: ["ITD105"], preferred_schedule_blocks: blocks }, subjects).length, 0);
});
test("drag and rank dropdown share one unique ordered list", () => {
  const first = rankSubject(["CCC100", "ITD105", "ITN102"], "ITN102", 1);
  assert.deepEqual(first, ["ITN102", "CCC100", "ITD105"]);
  assert.deepEqual(rankSubject(first, "ITN102", 3), ["CCC100", "ITD105", "ITN102"]);
  assert.equal(new Set(first).size, first.length);
});
test("importance is hidden when disabled and zero is retained and described", () => {
  assert.equal(importanceVisible(false, "Compact"), false);
  assert.equal(importanceVisible(true, "No Preference"), false);
  assert.equal(importanceVisible(true, "Scattered"), true);
  assert.equal(IMPORTANCE_OPTIONS.find(option => option.value === 0).label, "No weight / informational only");
});
test("dirty state detects changes and becomes clean on discard or save", () => {
  const draft = { ...preference, preferred_subjects: ["CCC100"] };
  assert.equal(isDirty(preference, preference), false);
  assert.equal(isDirty(draft, preference), true);
  assert.equal(isDirty(draft, structuredClone(draft)), false);
});
test("general periods retain duration and do not invent subject placements", () => {
  const blocks = [{ id: "general", kind: "general", day: "T", start_time: "13:00", end_time: "16:00" }];
  const moved = moveBlock(blocks, "general", "W", "14:00", subjects);
  assert.equal(moved[0].end_time, "17:00");
  const draft = withBlocks(preference, moved);
  assert.deepEqual(draft.preferred_days, ["W"]); assert.equal(draft.preferred_start_time, "14:00");
});
test("legacy preferred periods can be edited without an automatic dirty state", () => {
  const saved = { ...preference, preferred_days: ["T"], preferred_start_time: "13:00", preferred_end_time: "16:00" };
  const draft = editablePreference(saved);
  assert.equal(draft.preferred_schedule_blocks.length, 1);
  assert.equal(isDirty(draft, editablePreference(saved)), false);
  assert.equal(saved.preferred_schedule_blocks.length, 0);
});
test("editing or removing meetings preserves deliberately disabled day/time scoring", () => {
  const blocks = [{ id: "general", kind: "general", day: "M", start_time: "08:00", end_time: "10:00" }];
  const draft = { ...preference, preferred_schedule_blocks: blocks };
  const updated = withBlocks(draft, [{ ...blocks[0], day: "T" }]);
  assert.equal(updated.use_day_preference, false); assert.equal(updated.use_time_preference, false);
});
test("older invalid preferences are explained rather than silently discarded", () => {
  const draft = editablePreference({ ...preference, preferred_subjects: ["ITE184"], preferred_schedule_blocks: [{ id: "old", kind: "subject", day: "M", start_time: "08:00", end_time: "09:00", subject_code: "ITE184", component: "Lecture" }] });
  assert.equal(draft.preferred_subjects[0], "ITE184"); assert.equal(validationIssues(draft, subjects).length, 2);
});
