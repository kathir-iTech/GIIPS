import { FileText, Network, Gauge, Lightbulb, ArrowRight, AlertTriangle, CheckCircle, Layers, Zap } from 'lucide-react';
import Header from '../components/Header';
import './Methodology.css';

const Methodology = () => {
  return (
    <div className="methodology-page">
      <Header title="Methodology" subtitle="Understanding the intelligence processing pipeline" />
      <div className="page-content">
        <section className="intro-section">
          <div className="intro-content">
            <h2>The GIIPS Approach</h2>
            <p>GIIPS transforms raw citizen complaints into actionable intelligence through a four-stage pipeline. The system addresses a fundamental inefficiency in grievance redressal: <strong>thousands of complaints may represent only a few dozen actual incidents</strong>, leading to massive duplication of administrative effort.</p>
          </div>
          <div className="efficiency-showcase">
            <div className="showcase-block before-block"><AlertTriangle size={20} className="block-icon" /><span className="block-number">100</span><span className="block-label">Individual Complaints</span></div>
            <div className="showcase-arrow"><ArrowRight size={32} /><span className="reduction-label">85% Reduction</span></div>
            <div className="showcase-block after-block"><CheckCircle size={20} className="block-icon" /><span className="block-number">15</span><span className="block-label">Actionable Incidents</span></div>
          </div>
        </section>

        <section className="workflow-comparison">
          <div className="workflow-card current">
            <div className="workflow-header"><span className="workflow-badge current">Current Government Workflow</span></div>
            <div className="workflow-steps">
              <div className="workflow-step"><span className="step-num">1</span><span>Complaint Received</span></div>
              <div className="workflow-arrow">+</div>
              <div className="workflow-step"><span className="step-num">2</span><span>Manual Review</span></div>
              <div className="workflow-arrow">+</div>
              <div className="workflow-step"><span className="step-num">3</span><span>Individual Processing</span></div>
              <div className="workflow-arrow">+</div>
              <div className="workflow-step"><span className="step-num">4</span><span>100 Separate Actions</span></div>
            </div>
            <div className="workflow-issues"><h4>Problems</h4><ul><li>Massive duplication of effort</li><li>Delayed response times</li><li>Inconsistent prioritization</li><li>Resource wastage</li></ul></div>
          </div>
          <div className="workflow-card giips">
            <div className="workflow-header"><span className="workflow-badge giips">GIIPS Workflow</span></div>
            <div className="workflow-steps">
              <div className="workflow-step"><span className="step-num">1</span><span>Complaints Ingested</span></div>
              <div className="workflow-arrow success">+</div>
              <div className="workflow-step"><span className="step-num">2</span><span>AI Clustering</span></div>
              <div className="workflow-arrow success">+</div>
              <div className="workflow-step"><span className="step-num">3</span><span>Priority Scoring</span></div>
              <div className="workflow-arrow success">+</div>
              <div className="workflow-step"><span className="step-num">4</span><span>15 Focused Actions</span></div>
            </div>
            <div className="workflow-benefits"><h4>Benefits</h4><ul><li>85% workload reduction</li><li>Intelligent prioritization</li><li>Consistent assessment</li><li>Resource optimization</li></ul></div>
          </div>
        </section>

        <section className="pipeline-section">
          <div className="pipeline-header"><h2>Processing Pipeline</h2><span className="pipeline-badge">4 Stages</span></div>
          <div className="pipeline-visual">
            <div className="pipeline-stage">
              <div className="stage-icon"><FileText size={24} /></div>
              <div className="stage-content"><h3>Complaint Ingestion</h3><p>Raw complaints collected from multiple channels - web portal, mobile app, call center. Each complaint is timestamped, geotagged, and assigned a unique identifier.</p><div className="stage-flow"><span className="flow-label">Inputs</span><span className="flow-items">Citizen submissions, Location data, Timestamp</span></div></div>
            </div>
            <div className="stage-connector"><ArrowRight size={20} /></div>
            <div className="pipeline-stage">
              <div className="stage-icon"><Network size={24} /></div>
              <div className="stage-content"><h3>Similarity Analysis</h3><p>Natural Language Processing algorithms analyze complaint text to identify semantic similarity. Complaints describing the same incident are clustered using AI-based text matching.</p><div className="stage-flow"><span className="flow-label">AI Processing</span><span className="flow-items">Text embeddings, Clustering algorithm, Similarity scoring</span></div></div>
            </div>
            <div className="stage-connector"><ArrowRight size={20} /></div>
            <div className="pipeline-stage">
              <div className="stage-icon"><Gauge size={24} /></div>
              <div className="stage-content"><h3>Priority Scoring</h3><p>Each incident receives a priority score based on severity, affected citizens, urgency, and public safety impact. Automatic classification into Critical/High/Medium/Low.</p><div className="stage-flow"><span className="flow-label">Scoring</span><span className="flow-items">Severity weights, Impact metrics, Time factors</span></div></div>
            </div>
            <div className="stage-connector"><ArrowRight size={20} /></div>
            <div className="pipeline-stage">
              <div className="stage-icon"><Lightbulb size={24} /></div>
              <div className="stage-content"><h3>Decision Support</h3><p>Final output provides officers with prioritized incidents, recommended actions, and resource allocation guidance for efficient grievance resolution.</p><div className="stage-flow"><span className="flow-label">Output</span><span className="flow-items">Dashboard, Action recommendations, Metrics</span></div></div>
            </div>
          </div>
        </section>

        <section className="architecture-section">
          <div className="architecture-header"><h2>System Architecture</h2><span className="architecture-subtitle">Integration-ready design for AI backend</span></div>
          <div className="architecture-diagram">
            <div className="arch-layer source"><div className="layer-title">Data Sources</div><div className="layer-items"><span className="layer-item">Web Portal</span><span className="layer-item">Mobile App</span><span className="layer-item">Call Center</span></div></div>
            <div className="arch-arrow"><Layers size={18} /></div>
            <div className="arch-layer ingestion"><div className="layer-title">Data Ingestion Layer</div><div className="layer-items"><span className="layer-item">API Gateway</span><span className="layer-item">Message Queue</span></div></div>
            <div className="arch-arrow"><Layers size={18} /></div>
            <div className="arch-layer ai"><div className="layer-title"><Zap size={14} className="ai-icon" /> AI Processing Engine</div><div className="layer-items"><span className="layer-item">Classification</span><span className="layer-item">Clustering</span><span className="layer-item">Scoring</span></div></div>
            <div className="arch-arrow"><Layers size={18} /></div>
            <div className="arch-layer output"><div className="layer-title">Decision Support Layer</div><div className="layer-items"><span className="layer-item">Dashboard</span><span className="layer-item">Reports</span><span className="layer-item">Alerts</span></div></div>
          </div>
          <div className="architecture-note"><span className="note-label">Note:</span> The current prototype uses local JSON data. The AI Engine layer will be integrated via REST APIs without modifying the UI layer.</div>
        </section>

        <section className="metrics-guide">
          <h2>Understanding Model Metrics</h2>
          <div className="metrics-grid">
            <div className="metric-guide"><h4>Accuracy</h4><p>Overall correctness of the model across all categories. Measures how often the model correctly identifies duplicate vs non-duplicate complaints.</p><span className="metric-target">Target: &gt;90%</span></div>
            <div className="metric-guide"><h4>Precision</h4><p>Of all complaints predicted as duplicates, how many actually are. High precision means fewer false positives - the model does not cluster unrelated complaints.</p><span className="metric-target">Target: &gt;88%</span></div>
            <div className="metric-guide"><h4>Recall</h4><p>Of all actual duplicate complaints, how many the model correctly identified. High recall means the model catches most duplicates, minimizing missed groupings.</p><span className="metric-target">Target: &gt;92%</span></div>
            <div className="metric-guide"><h4>F1 Score</h4><p>Harmonic mean of precision and recall. Balanced metric for overall model quality when you need to consider both false positives and false negatives.</p><span className="metric-target">Target: &gt;90%</span></div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Methodology;
