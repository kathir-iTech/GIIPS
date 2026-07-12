import type React from 'react';
import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const next = i18n.language === 'ta' ? 'en' : 'ta';
    i18n.changeLanguage(next);
  };

  return (
    <button className="lang-switcher" onClick={toggleLanguage} title={i18n.language === 'ta' ? 'Switch to English' : 'தமிழுக்கு மாற்று'}>
      {i18n.language === 'ta' ? 'English' : 'தமிழ்'}
    </button>
  );
};

export default LanguageSwitcher;
