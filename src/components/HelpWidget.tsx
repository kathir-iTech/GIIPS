import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { HelpCircle, X, ChevronDown, ChevronUp } from 'lucide-react';
import './HelpWidget.css';

const FAQ_KEYS = [
  { q: 'q1', a: 'a1' },
  { q: 'q2', a: 'a2' },
  { q: 'q3', a: 'a3' },
  { q: 'q4', a: 'a4' },
  { q: 'q5', a: 'a5' },
  { q: 'q6', a: 'a6' },
];

const HelpWidget = () => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const toggle = () => {
    setOpen(v => !v);
    setExpandedIndex(null);
  };

  return (
    <>
      {open && <div className="help-overlay" onClick={toggle} />}
      <div className={`help-widget ${open ? 'open' : ''}`}>
        {open && (
          <div className="help-panel">
            <div className="help-header">
              <span className="help-title">
                <HelpCircle size={16} />
                {t('helpWidget.title')}
              </span>
              <button className="help-close" onClick={toggle} title={t('helpWidget.close')}>
                <X size={16} />
              </button>
            </div>
            <div className="help-body">
              {FAQ_KEYS.map((item, idx) => (
                <div key={item.q} className="help-faq-item">
                  <button
                    className={`help-faq-q ${expandedIndex === idx ? 'expanded' : ''}`}
                    onClick={() => setExpandedIndex(expandedIndex === idx ? null : idx)}
                  >
                    <span>{t(`helpWidget.${item.q}`)}</span>
                    {expandedIndex === idx ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  {expandedIndex === idx && (
                    <div className="help-faq-a">
                      <p>{t(`helpWidget.${item.a}`)}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        <button className="help-toggle" onClick={toggle} title={t('helpWidget.help')}>
          <HelpCircle size={22} />
        </button>
      </div>
    </>
  );
};

export default HelpWidget;
