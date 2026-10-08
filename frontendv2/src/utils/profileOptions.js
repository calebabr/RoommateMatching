// Shared static profile option lists.
//
// These were previously duplicated verbatim in SignupPage, ProfilePage and
// App.jsx.  They are now defined once here so the signup form, the profile
// editor, the profile-completion modal and the Discover filter sheet can never
// drift apart.

export const RELIGION_OPTIONS = [
  'Christian', 'Catholic', 'Muslim', 'Jewish', 'Hindu',
  'Buddhist', 'Agnostic', 'Atheist', 'Spiritual', 'Other', 'Prefer not to say',
];

export const MAJOR_OPTIONS = [
  'Accounting', 'Aerospace Engineering', 'Architecture', 'Biology',
  'Business Administration', 'Chemical Engineering', 'Chemistry',
  'Civil Engineering', 'Communications', 'Computer Science',
  'Criminal Justice', 'Economics', 'Education', 'Electrical Engineering',
  'English', 'Finance', 'Graphic Design', 'History', 'Industrial Engineering',
  'Information Systems', 'Kinesiology', 'Marketing', 'Mathematics',
  'Mechanical Engineering', 'Nursing', 'Philosophy', 'Physics',
  'Political Science', 'Psychology', 'Public Health', 'Sociology',
  'Software Engineering', 'Statistics', 'Theater', 'Undecided', 'Other',
];

export const GRADUATION_SEASONS = ['Spring', 'Summer', 'Fall'];

export const GRADUATION_YEARS = [
  2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035,
];
