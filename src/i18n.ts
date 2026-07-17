import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import enTranslation from './locales/en/translation.json';
import taTranslation from './locales/ta/translation.json';
import knTranslation from './locales/kn/translation.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enTranslation },
      ta: { translation: taTranslation },
      kn: { translation: knTranslation },
    },
    lng: 'en',
    fallbackLng: 'en',
    supportedLngs: ['en', 'ta', 'kn'],
    nonExplicitSupportedLngs: true,
    detection: {
      order: ['localStorage'],
      lookupLocalStorage: 'giips_lang',
      caches: ['localStorage'],
    },
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
