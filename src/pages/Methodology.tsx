import { FileText, Group, ChartBar as BarChart3, ArrowRight, TriangleAlert as AlertTriangle, CircleCheck as CheckCircle } from 'lucide-react';
import Header from '../components/Header';
import './Methodology.css';

const methodologySteps = [
  {
    number: 1,
    title: 'Complaint Ingestion',
    icon: FileText,
    description: 'Raw citizen complaints are collected from multiple channels including web portal, mobile app, and offline submission centers. Each complaint is timestamped, attributed to a ward, and assigned a unique identifier.',
    inputs: ['Citizen submissions', 'Location data', 'Timestamp'],
    outputs: ['Structured complaint records', 'Initial categorization', 'Deduplication flagging']
  },
  {
    number: 2,
    title: 'Similarity Analysis',
    icon: Group,
    description: 'Natural language processing algorithms analyze complaint text to identify semantic similarity. Complaints describing the same underlying incident are clustered using a similarity threshold (typically 0.85 or higher).',
    inputs: ['Complaint text', 'Location metadata', 'Category hints'],
    outputs: ['Similarity scores', 'Cluster assignments', 'Duplicate groupings']
  },
  {
    number: 3,
    title: 'Priority Scoring',
    icon: BarChart3,
    description: 'Each identified incident receives a priority score (0-100) based on weighted factors: severity of the issue, number of affected citizens, time since first complaint, and public safety implications.',
    inputs: ['Cluster size', 'Category severity weights', 'Days elapsed'],
    outputs: ['Priority score', 'Priority label', 'Recommended action']
  },
  {
    number: 4,
    title: 'Decision Support',
    icon: ArrowRight,
    description: 'Final output provides municipal officers with actionable intelligence: unique incidents ranked by priority, recommended actions based on category and severity, and resource allocation guidance.',
    inputs: ['Prioritized incidents', 'Historical resolution patterns', 'Resource constraints'],
    outputs: ['Executive dashboard', 'Action recommendations', 'Performance metrics']
  }
];

const Methodology = () => {
  return (
    <div className="methodology-page">
      <Header title="Methodology" subtitle="Understanding the intelligencd processing pipeline" />
      <div className="page-content">
        <div className="methodology-intro">
          <h2>The GIIPS Approach</h2>
          <p>GIIPS transforms raw citizen complaints into actionable intelligence through a four-stage pipeline. The system addresses a fundamental inefficiency: <strong>100 complaints may represent only 5 real incidents</strong>, leading to massive duplication of administrative effort.</p>
          <div className="efficiency-demo">
            <div className="efficiency-stat">
              <AlertTriangle size={24} className="before-icon" />
              <span className="before-value">100</span>
              <span className="before-label">Individual Complaints</span>
            </div>
            <ArrowRight size={32} className="arrow-icon" />
            <div className="efficiency-stat">
              <CheckCircle size={24} className="after-icon" />
              <span className="after-value">5</span>
              <span className="after-label">Unique Incidents</span>
            </div>
          </div>
        </div>

        <div className="pipeline-section">
          <div className="pipeline-header">
            <h3>Processing Pipeline</h3>
            <span className="pipeline-badge">4 Stages</span>
          </div>
          <div className="pipeline-steps">
            {methodologySteps.map((step, index) => (
              <div key={step.number} className="pipeline-step">
                <div className="step-header">
                  <div className="step-number">{step.number}</div>
                  <step.icon size={24} className="step-icon" />
                  <h4>{step.title}</h4>
                </div>
                <p className="step-description">{step.description}</p>
                <div className="step-details">
                  <div className="step-inputs">
                    <span className="detail-label">Inputs</span>
                    <ul>{step.inputs.map((input, i) => <li key={i}>{input}</li>)}</ul>
                  </div>
                  <div className="step-outputs">
                    <span className="detail-label">Outputs</span>
                    <ul>{step.outputs.map((output, i) => <li key={i}>{output}</li>)}</ul>
                  </div>
                </div>
                {index < methodologySteps.length - 1 && <div className="step-connector"></div>}
              </div>
            ))}
          </div>
        </div>

        <div className="metrics-section">
          <div className="metrics-header">
            <h3>Model Performance</h3>
          </div>
          <div className="metrics-explanation">
            <div className="metric-explanation-item">
              <span className="metric-name">Accuracy</span>
              <p>The proportion of all classifications that were correct. Higher values indicate better overall performance.</p>
            </div>
            <div className="metric-explanation-item">
              <span className="metric-name">Precision</span>
              <p>Of all complaints predicted to belong to a cluster, how many actually belong. Minimizes false clustering.</p>
            </div>
            <div className="metric-explanation-item">
              <span className="metric-name">Recall</span>
              <p>Of all complaints that should be in a cluster, how many were correctly identified. Minimizes missed groupings.</p>
            </div>
            <div className="metric-explanation-item">
              <span className="metric-name">F1 Score</span>
              <p>Harmonic mean of precision and recall. Balanced measure for overall model quality.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Methodology;
