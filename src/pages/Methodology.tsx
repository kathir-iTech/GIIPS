import { useTranslation } from 'react-i18next';
import { FileText, Network, Gauge, Lightbulb, ArrowRight, AlertTriangle, CheckCircle, Layers, Zap } from 'lucide-react';
import Header from '../components/Header';
import './Methodology.css';

const Methodology = () => {
  const { t } = useTranslation();
  return (
    <div className="methodology-page">
      <Header title={t('methodology.header.title')} subtitle={t('methodology.header.subtitle')} />
      <div className="page-content">
        <section className="intro-section">
          <div className="intro-content">
            <h2>{t('methodology.intro.title')}</h2>
            <p>{t('methodology.intro.body')}</p>
          </div>
          <div className="efficiency-showcase">
            <div className="showcase-block before-block"><AlertTriangle size={20} className="block-icon" /><span className="block-number">100</span><span className="block-label">{t('methodology.intro.individualComplaints')}</span></div>
            <div className="showcase-arrow"><ArrowRight size={32} /><span className="reduction-label">{t('methodology.intro.reduction')}</span></div>
            <div className="showcase-block after-block"><CheckCircle size={20} className="block-icon" /><span className="block-number">15</span><span className="block-label">{t('methodology.intro.actionableIncidents')}</span></div>
          </div>
        </section>

        <section className="workflow-comparison">
          <div className="workflow-card current">
            <div className="workflow-header"><span className="workflow-badge current">{t('methodology.workflow.current')}</span></div>
            <div className="workflow-steps">
              <div className="workflow-step"><span className="step-num">1</span><span>{t('methodology.workflow.complaintReceived')}</span></div>
              <div className="workflow-arrow">+</div>
              <div className="workflow-step"><span className="step-num">2</span><span>{t('methodology.workflow.manualReview')}</span></div>
              <div className="workflow-arrow">+</div>
              <div className="workflow-step"><span className="step-num">3</span><span>{t('methodology.workflow.individualProcessing')}</span></div>
              <div className="workflow-arrow">+</div>
              <div className="workflow-step"><span className="step-num">4</span><span>{t('methodology.workflow.hundredActions')}</span></div>
            </div>
            <div className="workflow-issues"><h4>{t('methodology.workflow.problems')}</h4><ul><li>{t('methodology.workflow.problemDuplication')}</li><li>{t('methodology.workflow.problemDelays')}</li><li>{t('methodology.workflow.problemPrioritization')}</li><li>{t('methodology.workflow.problemWastage')}</li></ul></div>
          </div>
          <div className="workflow-card giips">
            <div className="workflow-header"><span className="workflow-badge giips">{t('methodology.workflow.giips')}</span></div>
            <div className="workflow-steps">
              <div className="workflow-step"><span className="step-num">1</span><span>{t('methodology.workflow.complaintsIngested')}</span></div>
              <div className="workflow-arrow success">+</div>
              <div className="workflow-step"><span className="step-num">2</span><span>{t('methodology.workflow.aiClustering')}</span></div>
              <div className="workflow-arrow success">+</div>
              <div className="workflow-step"><span className="step-num">3</span><span>{t('methodology.workflow.priorityScoring')}</span></div>
              <div className="workflow-arrow success">+</div>
              <div className="workflow-step"><span className="step-num">4</span><span>{t('methodology.workflow.fifteenActions')}</span></div>
            </div>
            <div className="workflow-benefits"><h4>{t('methodology.workflow.benefits')}</h4><ul><li>{t('methodology.workflow.benefitReduction')}</li><li>{t('methodology.workflow.benefitPrioritization')}</li><li>{t('methodology.workflow.benefitConsistency')}</li><li>{t('methodology.workflow.benefitOptimization')}</li></ul></div>
          </div>
        </section>

        <section className="pipeline-section">
          <div className="pipeline-header"><h2>{t('methodology.pipeline.title')}</h2><span className="pipeline-badge">{t('methodology.pipeline.stages')}</span></div>
          <div className="pipeline-visual">
            <div className="pipeline-stage">
              <div className="stage-icon"><FileText size={24} /></div>
              <div className="stage-content"><h3>{t('methodology.pipeline.stage1Title')}</h3><p>{t('methodology.pipeline.stage1Desc')}</p><div className="stage-flow"><span className="flow-label">{t('methodology.pipeline.inputs')}</span><span className="flow-items">{t('methodology.pipeline.stage1Items')}</span></div></div>
            </div>
            <div className="stage-connector"><ArrowRight size={20} /></div>
            <div className="pipeline-stage">
              <div className="stage-icon"><Network size={24} /></div>
              <div className="stage-content"><h3>{t('methodology.pipeline.stage2Title')}</h3><p>{t('methodology.pipeline.stage2Desc')}</p><div className="stage-flow"><span className="flow-label">{t('methodology.pipeline.aiProcessing')}</span><span className="flow-items">{t('methodology.pipeline.stage2Items')}</span></div></div>
            </div>
            <div className="stage-connector"><ArrowRight size={20} /></div>
            <div className="pipeline-stage">
              <div className="stage-icon"><Gauge size={24} /></div>
              <div className="stage-content"><h3>{t('methodology.pipeline.stage3Title')}</h3><p>{t('methodology.pipeline.stage3Desc')}</p><div className="stage-flow"><span className="flow-label">{t('methodology.pipeline.scoring')}</span><span className="flow-items">{t('methodology.pipeline.stage3Items')}</span></div></div>
            </div>
            <div className="stage-connector"><ArrowRight size={20} /></div>
            <div className="pipeline-stage">
              <div className="stage-icon"><Lightbulb size={24} /></div>
              <div className="stage-content"><h3>{t('methodology.pipeline.stage4Title')}</h3><p>{t('methodology.pipeline.stage4Desc')}</p><div className="stage-flow"><span className="flow-label">{t('methodology.pipeline.output')}</span><span className="flow-items">{t('methodology.pipeline.stage4Items')}</span></div></div>
            </div>
          </div>
        </section>

        <section className="architecture-section">
          <div className="architecture-header"><h2>{t('methodology.architecture.title')}</h2><span className="architecture-subtitle">{t('methodology.architecture.subtitle')}</span></div>
          <div className="architecture-diagram">
            <div className="arch-layer source"><div className="layer-title">{t('methodology.architecture.dataSources')}</div><div className="layer-items"><span className="layer-item">{t('methodology.architecture.webPortal')}</span></div></div>
            <div className="arch-arrow"><Layers size={18} /></div>
            <div className="arch-layer ingestion"><div className="layer-title">{t('methodology.architecture.ingestionLayer')}</div><div className="layer-items"><span className="layer-item">{t('methodology.architecture.apiGateway')}</span></div></div>
            <div className="arch-arrow"><Layers size={18} /></div>
            <div className="arch-layer ai"><div className="layer-title"><Zap size={14} className="ai-icon" /> {t('methodology.architecture.aiEngine')}</div><div className="layer-items"><span className="layer-item">{t('methodology.architecture.classification')}</span><span className="layer-item">{t('methodology.architecture.clustering')}</span><span className="layer-item">{t('methodology.architecture.scoring')}</span></div></div>
            <div className="arch-arrow"><Layers size={18} /></div>
            <div className="arch-layer output"><div className="layer-title">{t('methodology.architecture.decisionLayer')}</div><div className="layer-items"><span className="layer-item">{t('methodology.architecture.dashboard')}</span><span className="layer-item">{t('methodology.architecture.reports')}</span><span className="layer-item">{t('methodology.architecture.alerts')}</span></div></div>
          </div>
          <div className="architecture-note"><span className="note-label">{t('methodology.architecture.noteLabel')}:</span> {t('methodology.architecture.noteBody')}</div>
        </section>

        <section className="metrics-guide">
          <h2>{t('methodology.metrics.title')}</h2>
          <div className="metrics-caveat">{t('methodology.metrics.caveat')}</div>
          <div className="metrics-grid">
            <div className="metric-guide"><h4>{t('methodology.metrics.accuracy')}</h4><p>{t('methodology.metrics.accuracyDesc')}</p><span className="metric-target">{t('methodology.metrics.target')}: &gt;90%</span></div>
            <div className="metric-guide"><h4>{t('methodology.metrics.precision')}</h4><p>{t('methodology.metrics.precisionDesc')}</p><span className="metric-target">{t('methodology.metrics.target')}: &gt;88%</span></div>
            <div className="metric-guide"><h4>{t('methodology.metrics.recall')}</h4><p>{t('methodology.metrics.recallDesc')}</p><span className="metric-target">{t('methodology.metrics.target')}: &gt;92%</span></div>
            <div className="metric-guide"><h4>{t('methodology.metrics.f1Score')}</h4><p>{t('methodology.metrics.f1ScoreDesc')}</p><span className="metric-target">{t('methodology.metrics.target')}: &gt;90%</span></div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Methodology;
