export interface DepartmentInfo {
  slug: string;
  nameEn: string;
  nameTa: string;
  icon: string;
}

export const DEPARTMENTS: DepartmentInfo[] = [
  { slug: 'agriculture',                             nameEn: 'Agriculture Department',                                                                                                 nameTa: 'வேளாண்மைத் துறை',                                        icon: 'agriculture' },
  { slug: 'animal_husbandry_dairying_fisheries',      nameEn: 'Animal Husbandry, Dairying and Fisheries Department',                                                                    nameTa: 'கால்நடை பராமரிப்பு, பால்வளம் மற்றும் மீன்வளத் துறை',        icon: 'animal' },
  { slug: 'it_digital_services',                      nameEn: 'Information Technology and Digital Services Department',                                                                nameTa: 'தகவல் தொழில் நுட்பவியல் மற்றும் டிஜிட்டல் சேவைகள் துறை',   icon: 'technology' },
  { slug: 'backward_classes_minorities_welfare',      nameEn: 'Backward Classes, Most Backward Classes and Minorities Welfare Department',                                            nameTa: 'பிற்படுத்தப்பட்டோர் நலம் மற்றும் சிறுபான்மையினர் நலத்துறை', icon: 'welfare' },
  { slug: 'commercial_taxes_registration',            nameEn: 'Commercial Taxes and Registration Department',                                                                         nameTa: 'வணிகவரித் துறை மற்றும் பத்திரப்பதிவு துறை',               icon: 'finance' },
  { slug: 'cooperation_food_consumer_protection',     nameEn: 'Co-operation, Food and Consumer Protection Department',                                                                nameTa: 'கூட்டுறவு, உணவு மற்றும் நுகர்வோர் பாதுகாப்பு துறை',        icon: 'food' },
  { slug: 'energy',                                   nameEn: 'Energy Department',                                                                                                    nameTa: 'எரிசக்தி துறை',                                           icon: 'electricity' },
  { slug: 'environment_forests',                      nameEn: 'Environment and Forests Department',                                                                                   nameTa: 'சுற்றுச்சூழல் மற்றும் வனத்துறை',                            icon: 'environment' },
  { slug: 'finance',                                  nameEn: 'Finance Department',                                                                                                   nameTa: 'நிதித் துறை',                                              icon: 'finance' },
  { slug: 'handlooms_handicrafts_textiles_khadi',     nameEn: 'Handlooms, Handicrafts, Textiles and Khadi Department',                                                                nameTa: 'கைத்தறி, கைத்திறன், துணிநூல் மற்றும் கதர்த்துறை',          icon: 'industry' },
  { slug: 'health_family_welfare',                    nameEn: 'Health and Family Welfare Department',                                                                                 nameTa: 'மக்கள் நலவாழ்வு மற்றும் குடும்பநலத்துறை',                   icon: 'health' },
  { slug: 'higher_education',                         nameEn: 'Higher Education Department',                                                                                          nameTa: 'உயர்கல்வி துறை',                                          icon: 'education' },
  { slug: 'highways_minor_ports',                     nameEn: 'Highways and Minor Ports Department',                                                                                  nameTa: 'நெடுஞ்சாலைகள் மற்றும் சிறு துறைமுகங்கள் துறை',            icon: 'road' },
  { slug: 'home_prohibition_excise',                  nameEn: 'Home, Prohibition and Excise Department',                                                                              nameTa: 'உள், மதுவிலக்கு மற்றும் ஆயத்தீர்வை துறை',                  icon: 'security' },
  { slug: 'housing_urban_development',                nameEn: 'Housing and Urban Development Department',                                                                             nameTa: 'வீட்டு வசதி மற்றும் நகர்ப்புற வளர்ச்சித் துறை',           icon: 'building' },
  { slug: 'human_resources_management',               nameEn: 'Human Resources Management Department',                                                                                 nameTa: 'பணியாளர் மற்றும் நிர்வாகச் சீர்திருத்தத் துறை',            icon: 'admin' },
  { slug: 'industries',                               nameEn: 'Industries Department',                                                                                                nameTa: 'தொழில் துறை',                                             icon: 'industry' },
  { slug: 'labour_employment',                        nameEn: 'Labour and Employment Department',                                                                                      nameTa: 'தொழிலாளர் மற்றும் வேலைவாய்ப்பு துறை',                     icon: 'labour' },
  { slug: 'law',                                      nameEn: 'Law Department',                                                                                                      nameTa: 'சட்டத்துறை',                                              icon: 'law' },
  { slug: 'legislative_assembly',                     nameEn: 'Legislative Assembly Department',                                                                                      nameTa: 'சட்டமன்ற பேரவைச் செயலகம் துறை',                          icon: 'government' },
  { slug: 'msme',                                     nameEn: 'Micro, Small and Medium Enterprises Department',                                                                       nameTa: 'குறு, சிறு மற்றும் நடுத்தரத் தொழில் நிறுவனங்கள் துறை',    icon: 'industry' },
  { slug: 'miscellaneous_officers_secretariat',       nameEn: 'Miscellaneous Officers, Secretariat Department',                                                                       nameTa: 'இதர அலுவலர்கள், செயலகம் துறை',                            icon: 'admin' },
  { slug: 'mudalvarin_mugavari',                      nameEn: 'Mudalvarin Mugavari Department',                                                                                       nameTa: 'முதல்வரின் முகவரி துறை',                                  icon: 'government' },
  { slug: 'municipal_admin_water_supply',             nameEn: 'Municipal Administration and Water Supply Department',                                                                nameTa: 'நகராட்சி நிர்வாகம் மற்றும் குடிநீர் வழங்கல் துறை',        icon: 'water' },
  { slug: 'natural_resources',                        nameEn: 'Natural Resources Department',                                                                                         nameTa: 'கனிம வளத் துறை',                                         icon: 'environment' },
  { slug: 'other_states_government',                  nameEn: 'Other States Government Department',                                                                                   nameTa: 'பிற மாநில அரசுகள் துறை',                                  icon: 'government' },
  { slug: 'planning_development_special_initiatives', nameEn: 'Planning, Development and Special Initiatives Department',                                                             nameTa: 'திட்டமிடல் மற்றும் மேம்பாட்டுத் துறை',                     icon: 'admin' },
  { slug: 'public',                                   nameEn: 'Public Department',                                                                                                    nameTa: 'பொதுத் துறை',                                             icon: 'government' },
  { slug: 'public_elections',                         nameEn: 'Public (Elections) Department',                                                                                        nameTa: 'பொது (தேர்தல்கள்) துறை',                                  icon: 'government' },
  { slug: 'public_works',                             nameEn: 'Public Works Department',                                                                                              nameTa: 'பொதுப்பணித் துறை',                                       icon: 'road' },
  { slug: 'revenue_disaster_management',              nameEn: 'Revenue and Disaster Management Department',                                                                           nameTa: 'வருவாய் மற்றும் பேரிடர் மேலாண்மை துறை',                  icon: 'finance' },
  { slug: 'rural_development_panchayat_raj',          nameEn: 'Rural Development and Panchayat Raj Department',                                                                       nameTa: 'ஊரக வளர்ச்சி மற்றும் ஊராட்சித் துறை',                    icon: 'village' },
  { slug: 'school_education',                         nameEn: 'School Education Department',                                                                                          nameTa: 'பள்ளிக் கல்வித் துறை',                                    icon: 'education' },
  { slug: 'social_justice',                           nameEn: 'Social Justice Department',                                                                                            nameTa: 'ஆதி திராவிடர் மற்றும் பழங்குடியினர் நலத் துறை',          icon: 'justice' },
  { slug: 'social_reforms',                           nameEn: 'Social Reforms Department',                                                                                            nameTa: 'சமூக சீர்திருத்த துறை',                                   icon: 'welfare' },
  { slug: 'social_welfare_women_empowerment',         nameEn: 'Social Welfare and Women Empowerment Department',                                                                      nameTa: 'சமூக நலம் மற்றும் மகளிர் மேம்பாட்டுத் துறை',              icon: 'welfare' },
  { slug: 'special_programme_implementation',         nameEn: 'Special Programme Implementation Department',                                                                          nameTa: 'சிறப்புத் திட்ட அமலாக்கத் துறை',                          icon: 'admin' },
  { slug: 'tamil_development_information',            nameEn: 'Tamil Development and Information Department',                                                                         nameTa: 'தமிழ் வளர்ச்சித் துறை மற்றும் செய்தித் துறை',              icon: 'culture' },
  { slug: 'tourism_culture_religious',                nameEn: 'Tourism, Culture and Religious Endowments Department',                                                                 nameTa: 'சுற்றுலா, பண்பாடு மற்றும் சமய அறநிலையத் துறை',           icon: 'tourism' },
  { slug: 'transport',                                nameEn: 'Transport Department',                                                                                                 nameTa: 'போக்குவரத்து துறை',                                      icon: 'traffic' },
  { slug: 'water_resources',                          nameEn: 'Water Resources Department',                                                                                           nameTa: 'நீர் வளத் துறை',                                         icon: 'water' },
  { slug: 'welfare_differently_abled',                nameEn: 'Welfare of Differently Abled Persons Department',                                                                      nameTa: 'மாற்றுத்திறனாளிகள் நலத் துறை',                            icon: 'welfare' },
  { slug: 'youth_welfare_sports',                     nameEn: 'Youth Welfare and Sports Development Department',                                                                      nameTa: 'இளைஞர் நலன் மற்றும் விளையாட்டு மேம்பாட்டுத்துறை',         icon: 'sports' },
];

const DISPLAY_TO_SLUG: Record<string, string> = {};
for (const d of DEPARTMENTS) {
  DISPLAY_TO_SLUG[d.nameEn] = d.slug;
}

export function getDeptI18nKey(displayName: string): string {
  const slug = DISPLAY_TO_SLUG[displayName] || 'municipal_admin_water_supply';
  return `departments.${slug}`;
}

export function getDeptTaName(displayName: string): string {
  const slug = DISPLAY_TO_SLUG[displayName] || 'municipal_admin_water_supply';
  const dept = DEPARTMENTS.find(d => d.slug === slug);
  return dept?.nameTa || displayName;
}

export function getDeptIconKeyword(displayName: string): string {
  const slug = DISPLAY_TO_SLUG[displayName] || 'municipal_admin_water_supply';
  const dept = DEPARTMENTS.find(d => d.slug === slug);
  return dept?.icon || 'water';
}

export const DEPARTMENT_SLUGS = DEPARTMENTS.map(d => d.slug);

export const DEPARTMENT_NAMES = DEPARTMENTS.map(d => d.nameEn);
