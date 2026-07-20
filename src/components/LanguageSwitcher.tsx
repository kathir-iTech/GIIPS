import type React from 'react';
import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

const LANG_MAP: Record<string, string> = {
  en: 'en',
  ta: 'ta',
};

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const lang = i18n.language?.split('-')[0] || 'en';
  const current = LANG_MAP[lang] || 'en';

  return (
    <div className="lang-switcher">
      <button
        className={`lang-option ${current === 'en' ? 'active' : ''}`}
        onClick={() => i18n.changeLanguage('en')}
      >
        English
      </button>
      <button
        className={`lang-option ${current === 'ta' ? 'active' : ''}`}
        onClick={() => i18n.changeLanguage('ta')}
      >
        தமிழ்
      </button>

    </div>
  );
};

export default LanguageSwitcher;
