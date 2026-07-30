import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import Header from '../components/Header';
import { Building2, ArrowRight, Users } from 'lucide-react';
import './Admin.css';

const ESCALATION_DATA = [
  { department: 'CCMC Engineering Wing', escalatesTo: 'Zone Commissioner', authority: 'CCMC Commissioner' },
  { department: 'TWAD Board', escalatesTo: 'Executive Engineer', authority: 'Chief Engineer (TWAD)' },
  { department: 'CCMC Health Department', escalatesTo: 'Health Officer', authority: 'CCMC Commissioner' },
  { department: 'TANGEDCO', escalatesTo: 'Superintending Engineer', authority: 'Chief Engineer (TANGEDCO)' },
];

const EscalationMatrix = () => {
  const { t } = useTranslation();
  const [slaReport, setSlaReport] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getDepartmentSlaReport()
      .then(setSlaReport)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const getOfficerCount = (dept: string): number => {
    const report = slaReport.find(s => {
      const sDept = (s.department || '').toLowerCase();
      return sDept.includes(dept.toLowerCase().split(' ')[0]) ||
             dept.toLowerCase().includes(sDept);
    });
    return report?.total_open ?? 0;
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>{t('department.escalationMatrix')}</h1>
        <p>Department escalation hierarchy reference</p>
      </div>

      <div className="comparison-section">
        <div className="comparison-table-wrapper">
          <table className="comparison-table">
            <thead>
              <tr>
                <th>{t('departmentManagement.columnDepartment')}</th>
                <th>{t('department.escalatesTo')}</th>
                <th>{t('department.authority')}</th>
                <th>{t('department.activeOfficers')}</th>
              </tr>
            </thead>
            <tbody>
              {ESCALATION_DATA.map((item, i) => (
                <tr key={i}>
                  <td className="dept-name">
                    <Building2 size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                    {item.department}
                  </td>
                  <td>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                      {item.escalatesTo}
                      <ArrowRight size={12} style={{ color: 'var(--text-muted)' }} />
                    </span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{item.authority}</td>
                  <td>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Users size={14} />
                      {loading ? '—' : getOfficerCount(item.department)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="metrics-section" style={{ marginTop: '2rem' }}>
        <h2>How escalation works</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
          When a complaint remains open beyond its SLA deadline, it is automatically escalated to the next authority in the chain.
          The escalation matrix defines the reporting hierarchy for each department. Active officer counts reflect the number of
          open incidents currently assigned to each department.
        </p>
      </div>
    </div>
  );
};

export default EscalationMatrix;
