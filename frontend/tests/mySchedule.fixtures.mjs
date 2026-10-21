import {binding} from './dashboardD1.fixtures.mjs';
export {binding};
export const proposal = {
  schema_version: 1, availability: 'available', faculty_id: binding.faculty_id, faculty_code: binding.faculty_code,
  source: {kind: 'latest_completed_ga_result', label: 'GA-generated proposal', compatibility: 'checked_against_loaded_inputs', freshness: 'not_recorded', saved_at: '2026-10-21T08:00:00Z'},
  assignments: [
    {subject: 'SYN101', title: 'Synthetic Programming', type: 'Lecture', day: 'M', start: '07:30', end: '10:30', section: 'SYN-A', room: 'SYN LEC'},
    {subject: 'SYN101', title: 'Synthetic Programming', type: 'Laboratory', day: 'W', start: '13:00', end: '16:00', section: 'SYN-A', room: 'SYN LAB'},
  ],
};
export const missing = {...proposal, availability: 'missing', source: {...proposal.source, compatibility: 'not_available', saved_at: null}, assignments: []};
export const empty = {...proposal, availability: 'empty', assignments: []};
