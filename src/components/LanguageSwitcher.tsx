import type React from 'react';
import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const current = i18n.language?.startsWith('ta') ? 'ta' : 'en';

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
