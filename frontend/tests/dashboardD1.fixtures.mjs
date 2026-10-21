// Public synthetic test identities. No institutional records or credentials.
export const facultyId = '10000000-0000-4000-8000-000000000001';
export const binding = {faculty_id: facultyId, faculty_code: 0, display_code: 'Synthetic Faculty 0', name: 'Synthetic Lecturer'};
export const account = {id: '10000000-0000-4000-8000-000000000002', username: 'faculty@example.invalid', role: 'faculty', is_active: true, faculty_id: facultyId, faculty: binding};
export const faculty = {...binding, instructor_type: 'optimization_faculty', seniority_level: 0,
  specializations: ['Synthetic computing domain'], eligible_subject_codes: ['SYN101'],
  admin_load: 0, research_load: 0, extension_load: 0, current_teaching_load: 0,
  required_teaching_load: 0, absolute_max_teaching_load: 40};
export const lecture = {type: 'Lecture', weekly_hours: 3, metadata_status: 'supported', duration_minutes: 90,
  meetings_per_week: 2, continuous: true, fixed_duration: true,
  meeting_patterns: [{meetings_per_week: 2, duration_minutes: 90, continuous: true, day_combinations: [['M', 'TH'], ['T', 'F']]}]};
export const laboratory = {type: 'Laboratory', weekly_hours: 3, metadata_status: 'supported', duration_minutes: 180,
  meetings_per_week: 1, continuous: true, fixed_duration: true,
  meeting_patterns: [{meetings_per_week: 1, duration_minutes: 180, continuous: true, day_combinations: [['W']]}]};
export const subjects = [{course_id: '10000000-0000-4000-8000-000000000003', subject_code: 'SYN101', subject_title: 'Synthetic Computing',
  category: 'OTHER', lecture_hours: 3, laboratory_hours: 3, domains: ['Synthetic computing domain'], components: [lecture, laboratory],
  preassignment_status: 'none', eligibility: null, offerings: [{can_be_assigned: null, is_preassigned: false}]},
{course_id: '10000000-0000-4000-8000-000000000004', subject_code: 'SYN102', subject_title: 'Synthetic Seminar',
  category: 'OTHER', lecture_hours: 1, laboratory_hours: 0, domains: [],
  components: [{...lecture, weekly_hours: 1, metadata_status: 'unsupported', duration_minutes: null, meetings_per_week: null, continuous: null, fixed_duration: false, meeting_patterns: []}],
  preassignment_status: 'none', eligibility: null, offerings: []}];
