export interface OfficerHead {
  name: string;
  phone: string;
  designation: string;
}

const OFFICER_DIRECTORY: Record<string, OfficerHead> = {
  'General Administration': { name: 'Dr. M. Sharmila', phone: '9443777666', designation: 'Appellate Authority / Deputy Commissioner' },
  'Engineering': { name: 'Mr. Arasu Selvaraj', phone: '9443799211', designation: 'City Engineer' },
  'JNNURM': { name: 'Ms. Sasipriya', phone: '9489206018', designation: 'Executive Engineer (JNNURM) (i/c)' },
  'Public Health': { name: 'Dr. Pradeep V. Krishankumar', phone: '9443799202', designation: 'City Health Officer' },
  'Education': { name: 'Mr. K. Pandia Raja Sekaran', phone: '9443799229', designation: 'Corporation Education Officer (i/c)' },
  'Town Planning': { name: 'Mrs. K. Karuppathal', phone: '9787715156', designation: 'Executive Engineer (Planning)' },
  'Accounts': { name: 'Mr. R. Sundarajan', phone: '9442104146', designation: 'Assistant Commissioner (Accounts)' },
  'Personnel Administration': { name: 'Mr. V. Saravanan', phone: '9442501877', designation: 'Assistant Commissioner (Personnel)' },
  'Revenue': { name: 'Mr. Senthilkumar Rathinam', phone: '9443799201', designation: 'Assistant Commissioner (Revenue)' },
  'Council': { name: 'Mr. A. Amalraj', phone: '9442104128', designation: 'Council Secretary' },
  'Legal Wing': { name: 'Mr. A. Amalraj', phone: '9442104128', designation: 'Law Officer' },
  'Election': { name: 'Mrs. R. Kavitha', phone: '9944876710', designation: 'Deputy Tahsildar (Election)' },
};

const FALLBACK_MAP: Record<string, string> = {
  'roads': 'Engineering',
  'water supply': 'Engineering',
  'waste management': 'Public Health',
  'sanitation': 'Public Health',
  'street lighting': 'Engineering',
  'electricity': 'Engineering',
  'public health': 'Public Health',
};

export function getDepartmentHead(dept: string): OfficerHead | null {
  const direct = OFFICER_DIRECTORY[dept];
  if (direct) return direct;
  const key = dept.toLowerCase();
  for (const [category, mappedDept] of Object.entries(FALLBACK_MAP)) {
    if (key.includes(category)) return OFFICER_DIRECTORY[mappedDept] || null;
  }
  return null;
}
