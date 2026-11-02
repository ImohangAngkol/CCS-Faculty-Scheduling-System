import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {CATEGORIES, filterSubjects, isEligible, rankSubject, isDirty} from '../src/components/faculty/preferenceModel.ts';
import {subjects, preference} from './preferenceFixtures.mjs';
const source = path => readFile(new URL('../src/'+path,import.meta.url),'utf8');

test('both portals use a sticky navigation column and a single document content scrollbar',async()=>{
  for(const path of ['layouts/AdminLayout.tsx','layouts/FacultyLayout.tsx']) {
    const text=await source(path);for(const value of ['dashboard-shell','dashboard-content','dashboard-main','Skip to page content','tabIndex={-1}'])assert.ok(text.includes(value));
  }
  const css=await source('components/common/dashboardLayout.css');
  assert.match(css,/min-height: 100dvh/);
  assert.match(css,/\.dashboard-sidebar \{ position: sticky; top: 0/);
  assert.doesNotMatch(css,/\.dashboard-main \{[^}]*overflow-y: auto/);
  assert.match(css,/\.dashboard-main \{ position: relative/);
  assert.match(css,/\.dashboard-sidebar \{[^}]*width: 16rem;[^}]*overflow-y: auto/);
});
test('mobile disclosure preserves NavLink activity, label, expanded state, Escape and focus return',async()=>{
  const text=await source('components/common/Sidebar.tsx');
  for(const value of ['aria-controls={panelId}','aria-expanded={mobileOpen}','Open navigation','Close navigation','event.key === "Escape"','toggle.current?.focus()','<NavLink','isActive','MSU-IIT','College of Computer Studies'])assert.ok(text.includes(value));
  const css=await source('components/common/dashboardLayout.css');assert.match(css,/dashboard-sidebar-panel:not\(\[data-open=true\]\) \{ display: none/);
});
test('switch is a controlled native checkbox with unchanged boolean callback and explicit accessible name',async()=>{
  const text=await source('components/faculty/PreferenceControls.tsx');
  assert.match(text,/type="checkbox" role="switch" aria-label=\{label\} checked=\{checked\}/);
  assert.match(text,/onChange\(event.target.checked\)/);
  assert.match(text,/checked \? "ON" : "OFF"/);
});
test('segmented choices remain native grouped radio inputs, not independent switches',async()=>{
  const text=await source('components/faculty/PreferenceControls.tsx');
  assert.match(text,/<fieldset[^>]*><legend[^>]*>\{label\}/);
  assert.match(text,/type="radio" name=\{name\} value=\{option.value\} checked=\{value === option.value\}/);
  assert.match(text,/onChange\(option.value\)/);
});
test('editor preserves existing API enum values and enable flags; browsing does not edit the draft',async()=>{
  const text=await source('components/faculty/FacultyPreferenceEditor.tsx');
  for(const value of ['value: "Scattered", label: "Spread Out"','value: "Different Day", label: "Different Days"','use_gap_preference: value !== "No Preference"','use_lecture_lab_preference: value !== "No Preference"','use_subject_preference: checked','setShowAll(checked)','setDraft(saved)','updateFacultyPreference(facultyCode, draft)'])assert.ok(text.includes(value));
  assert.match(text,/disabled=\{!eligible \|\| preferred\}/);
  assert.match(text,/if \(isEligible\(subject\) && !preferred\)/);
  assert.match(text,/className="preference-eligibility">Eligible/);
});
test('expanded subject browsing never grants eligibility, including reserved offerings',()=>{
  const expanded=filterSubjects(subjects,'ALL','',true);
  const normal=filterSubjects(subjects,'ALL','');
  assert.equal(expanded.length,4);assert.equal(normal.length,3);
  assert.equal(isEligible(expanded.find(subject=>subject.subject_code==='ITE184')),false);
  assert.deepEqual(filterSubjects(subjects,'ITD','data',true).map(subject=>subject.subject_code),['ITD105']);
  assert.deepEqual([...CATEGORIES],['ALL','CCC','ITD','ITN','ITE','ISY','OTHER']);
});
test('rank and dirty-state models retain explicit save/discard semantics',()=>{
  const saved=structuredClone(preference),draft={...saved,use_subject_preference:false,gap_preference:'Compact',use_gap_preference:true};
  assert.equal(isDirty(draft,saved),true);assert.equal(isDirty(saved,saved),false);
  assert.deepEqual(rankSubject(['CCC100','ITD105'],'ITD105',1),['ITD105','CCC100']);
  assert.equal(saved.gap_preference,'No Preference');assert.equal(saved.use_subject_preference,true);
});
test('focus styling, reduced-motion overrides and narrow wrapping are present',async()=>{
  const css=await source('components/faculty/preferences.css');
  for(const value of [':focus-visible + .preference-switch-track',':focus-visible + .preference-segment-label','prefers-reduced-motion: reduce','forced-colors: active','.preference-segments { display: flex; flex-wrap: wrap','border-radius: 999px'])assert.ok(css.includes(value));
  assert.doesNotMatch(css,/\.flex\.min-h-screen:has\(.preference-page\)/);
});
function luminance(hex){const channels=hex.match(/\w\w/g).map(value=>parseInt(value,16)/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4);return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;}
function contrast(a,b){const values=[luminance(a),luminance(b)].sort((a,b)=>b-a);return(values[0]+.05)/(values[1]+.05);}
test('selected text, unselected teal text and OFF track border have sufficient calculated contrast',()=>{
  assert.ok(contrast('ffffff','115e59')>=4.5);
  assert.ok(contrast('115e59','ffffff')>=4.5);
  assert.ok(contrast('64748b','e2e8f0')>=3);
});
