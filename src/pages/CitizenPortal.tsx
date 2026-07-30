import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation, Trans } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import AddressSearch from '../components/AddressSearch';
import VoiceInput from '../components/VoiceInput';
import HelpWidget from '../components/HelpWidget';
import { CheckCircle, Upload, MapPin, FileText, ChevronRight, ChevronLeft, Loader2, Sparkles, AlertCircle, Clock, WifiOff } from 'lucide-react';
import { saveOfflineComplaint, getOfflineCount, retryOfflineSubmissions } from '../utils/offlineQueue';
import './CitizenPortal.css';

const DRAFT_KEY = 'giips_complaint_wizard_draft';

const COMPLAINT_TEMPLATES = [
  { category: 'Roads', title: 'Pothole on my street needs repair', description: 'There is a large pothole on our road that has been causing issues for vehicles and pedestrians. It is located near the main junction and gets worse every time it rains. Please repair it as soon as possible.' },
  { category: 'Water Supply', title: 'No water supply in our area', description: 'We have not received water supply for the past few days. The entire street is affected and residents are struggling to get water for daily needs. Please restore water supply urgently.' },
  { category: 'Waste Management', title: 'Garbage not collected in our area', description: 'Garbage has not been collected from our street for over a week. The waste is piling up and creating unhygienic conditions. Please send the collection vehicle.' },
  { category: 'Sanitation', title: 'Drainage block on our street', description: 'The drainage line on our street is completely blocked, causing water to stagnate and creating a foul smell. Please clear the blockage at the earliest.' },
  { category: 'Street Lighting', title: 'Street light not working on our road', description: 'The street light near our house has not been working for several nights. The entire stretch is dark, making it unsafe especially for women and elderly residents.' },
  { category: 'Electricity', title: 'Frequent power cuts in our area', description: 'We are experiencing frequent power cuts throughout the day. Voltage fluctuations are also damaging appliances. Please look into this matter urgently.' },
  { category: 'Public Health', title: 'Mosquito menace due to stagnant water', description: 'Stagnant water in our area is breeding mosquitoes, creating a serious health risk. There is a risk of dengue and other diseases. Please arrange for fogging and drain cleaning.' },
];

interface DupCheckStepProps {
  formData: any;
  submitError: string | null;
  loading: boolean;
  handleSubmit: () => void;
  duplicateWarnings: any[];
  setDuplicateWarnings: (w: any[]) => void;
  dupCheckDone: boolean;
  setDupCheckDone: (d: boolean) => void;
  dupChecking: boolean;
  setDupChecking: (d: boolean) => void;
  t: (key: string, options?: any) => string;
}

const DuplicateCheckStep: React.FC<DupCheckStepProps> = ({
  formData, submitError, loading, handleSubmit,
  duplicateWarnings, setDuplicateWarnings,
  dupCheckDone, setDupCheckDone,
  dupChecking, setDupChecking, t,
}) => {
  useEffect(() => {
    if (dupCheckDone || dupChecking) return;
    const check = async () => {
      setDupChecking(true);
      try {
        const classifyRes = await fetch('http://localhost:8000/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: `${formData.title} ${formData.description}` }),
        });
        if (!classifyRes.ok) { setDupCheckDone(true); return; }
        const { predicted_category } = await classifyRes.json();
        if (!predicted_category) { setDupCheckDone(true); return; }

        const nearbyRes = await fetch(`http://localhost:8000/public/nearby-complaints?category=${encodeURIComponent(predicted_category)}&lat=${formData.latitude}&lon=${formData.longitude}`);
        if (!nearbyRes.ok) { setDupCheckDone(true); return; }
        const nearby: any[] = await nearbyRes.json();

        if (nearby.length > 0) {
          setDuplicateWarnings(nearby.slice(0, 5));
        }
      } catch {
        // non-blocking
      } finally {
        setDupCheckDone(true);
        setDupChecking(false);
      }
    };
    check();
  }, [dupCheckDone, dupChecking, formData]);

  return (
    <div className="form-step ai-step">
      <Sparkles className="ai-icon" />
      <h3>{t('citizenPortal.confirmTitle')}</h3>
      <p>{t('citizenPortal.confirmBody')}</p>

      {dupChecking && (
        <div className="dup-checking">
          <Loader2 className="spinner" size={16} /> {t('citizenPortal.checkingDuplicates')}
        </div>
      )}

      {duplicateWarnings.length > 0 && (
        <div className="duplicate-warning">
          <AlertCircle size={18} />
          <div>
            <strong>{t('citizenPortal.possibleDuplicate')}</strong>
            <p>{duplicateWarnings.length === 1 ? t('citizenPortal.similarFoundNearby') : t('citizenPortal.similarFoundNearbyPlural')}</p>
            <ul>
              {duplicateWarnings.map((d, i) => (
                <li key={i}>
                  <strong>{d.title || d.category}</strong>
                  {d.tracking_id && <span> — {t('citizenPortal.similarExists', { trackingId: d.tracking_id })}</span>}
                  {d.distance_km != null && <span> — {t('citizenPortal.kmAway', { distance: d.distance_km.toFixed(2) })}</span>}
                  {d.status && <span> [{d.status}]</span>}
                </li>
              ))}
            </ul>
            <p className="dup-note">{t('citizenPortal.duplicateNote')}</p>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
              {duplicateWarnings[0]?.tracking_id && (
                <button className="secondary" onClick={() => window.open(`/track?complaintId=${duplicateWarnings[0].tracking_id}`, '_blank')} style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '6px', border: '1px solid #475569', background: '#1e293b', color: '#94a3b8', cursor: 'pointer' }}>
                  {t('citizenPortal.trackExisting')}
                </button>
              )}
              <button onClick={handleSubmit} disabled={loading} style={{ padding: '6px 12px', fontSize: '0.8rem', borderRadius: '6px', border: '1px solid #3b82f6', background: '#3b82f6', color: 'white', cursor: 'pointer' }}>
                {loading ? t('citizenPortal.processingButton') : t('citizenPortal.submitAnyway')}
              </button>
            </div>
          </div>
        </div>
      )}

      {submitError && (
        <div className="error-banner">
          <AlertCircle size={16} />
          <span>{submitError}</span>
        </div>
      )}
      <button className="auth-button" onClick={handleSubmit} disabled={loading}>
        {loading ? t('citizenPortal.processingButton') : t('citizenPortal.confirmButton')}
      </button>
    </div>
  );
};

const CitizenPortal = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    title: '',
    description: '',
    location: '',
    ward: '',
    address: '',
    latitude: 0,
    longitude: 0,
  });
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [processingStatus, setProcessingStatus] = useState<string | null>(null);
  const [photoUploadStatus, setPhotoUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'failed'>('idle');
  const [nearMeStories, setNearMeStories] = useState<any[] | null>(null);
  const [nearMeLoading, setNearMeLoading] = useState(false);
  const [duplicateWarnings, setDuplicateWarnings] = useState<any[]>([]);
  const [dupCheckDone, setDupCheckDone] = useState(false);
  const [dupChecking, setDupChecking] = useState(false);
  const [offlineQueueCount, setOfflineQueueCount] = useState(0);
  const [suggestedCategory, setSuggestedCategory] = useState<string | null>(null);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [catSuggestAccepted, setCatSuggestAccepted] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [chatQuery, setChatQuery] = useState('');
  const [chatAnswers, setChatAnswers] = useState<any[]>([]);
  const classifyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const complaintIdRef = useRef<string | null>(null);
  const isUploadingRef = useRef(false);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  useEffect(() => {
    if (catSuggestAccepted) return;
    if (!formData.description || formData.description.trim().length < 20) {
      setSuggestedCategory(null);
      return;
    }
    if (classifyTimerRef.current) clearTimeout(classifyTimerRef.current);
    classifyTimerRef.current = setTimeout(async () => {
      setSuggestLoading(true);
      try {
        const res = await fetch('http://localhost:8000/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: formData.description }),
        });
        if (!res.ok) return;
        const { predicted_category } = await res.json();
        if (predicted_category) setSuggestedCategory(predicted_category);
      } catch {
        // non-blocking
      } finally {
        setSuggestLoading(false);
      }
    }, 500);
    return () => { if (classifyTimerRef.current) clearTimeout(classifyTimerRef.current); };
  }, [formData.description, catSuggestAccepted]);

  const ward = user?.ward || '';
  useEffect(() => {
    if (!ward) return;
    setNearMeLoading(true);
    api.getSuccessStories(ward)
      .then(setNearMeStories)
      .catch(() => setNearMeStories([]))
      .finally(() => setNearMeLoading(false));
  }, [ward]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(DRAFT_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setFormData(prev => ({ ...prev, ...parsed }));
      }
    } catch {}
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(formData));
    } catch {}
  }, [formData]);

  useEffect(() => {
    getOfflineCount().then(setOfflineQueueCount);
    const onOnline = () => { retryOfflineSubmissions().then(() => getOfflineCount().then(setOfflineQueueCount)); };
    window.addEventListener('online', onOnline);
    return () => window.removeEventListener('online', onOnline);
  }, []);

  const uploadPhoto = async (complaintId: string) => {
    if (!selectedFile || isUploadingRef.current) return;
    isUploadingRef.current = true;
    setPhotoUploadStatus('uploading');
    setSubmitError(null);
    try {
      await api.uploadComplaintPhoto(complaintId, selectedFile);
      setPhotoUploadStatus('done');
    } catch (uploadErr: any) {
      setPhotoUploadStatus('failed');
      setSubmitError(uploadErr.message);
    } finally {
      isUploadingRef.current = false;
    }
  };

  const skipPhoto = () => {
    isUploadingRef.current = false;
    setPhotoUploadStatus('done');
    setSubmitError(null);
  };

  const retryPhotoUpload = async () => {
    if (complaintIdRef.current) {
      await uploadPhoto(complaintIdRef.current);
    }
  };

  const handleSubmit = async () => {
    const errs: Record<string, string> = {};
    if (!user) { setSubmitError(t('citizenPortal.authRequired')); setLoading(false); return; }
    if (!formData.title.trim()) { errs.title = t('citizenPortal.titleRequired'); }
    else if (formData.title.trim().length < 10) { errs.title = t('citizenPortal.titleMinLength'); }
    if (!formData.description.trim()) { errs.description = t('citizenPortal.descRequired'); }
    else if (formData.description.trim().length < 20) { errs.description = t('citizenPortal.descMinLength'); }
    if (!formData.location.trim()) { errs.location = t('citizenPortal.locationRequired'); }
    if (Object.keys(errs).length > 0) { setFieldErrors(errs); setLoading(false); return; }
    setFieldErrors({});
    setLoading(true);
    setSubmitError(null);
    setProcessingStatus('submitting');
    setPhotoUploadStatus('idle');
    if (!navigator.onLine) {
      await saveOfflineComplaint({
        ...formData,
        ...(catSuggestAccepted && suggestedCategory ? { predicted_category: suggestedCategory } : {}),
        ...(tags.length > 0 ? { tags } : {}),
      });
      setResult({ offline: true, complaintId: `OFFLINE-${Date.now()}` });
      setLoading(false);
      setProcessingStatus(null);
      getOfflineCount().then(setOfflineQueueCount);
      return;
    }

    try {
      const response = await api.submitComplaint({
        ...formData,
        ...(catSuggestAccepted && suggestedCategory ? { predicted_category: suggestedCategory } : {}),
        ...(tags.length > 0 ? { tags } : {}),
      });
      if (response.statusUrl) {
        complaintIdRef.current = response.complaintId;
        setProcessingStatus('pending');

        if (selectedFile) {
          await uploadPhoto(response.complaintId);
        } else {
          setPhotoUploadStatus('done');
        }

        pollTimeoutRef.current = setTimeout(() => {
          stopPolling();
          setSubmitError(t('citizenPortal.statusTimedOut'));
          setLoading(false);
        }, 120000);
        pollingRef.current = setInterval(async () => {
          try {
            const status = await api.getComplaintStatus(response.complaintId);
            if (status.status === 'completed') {
              stopPolling();
              setProcessingStatus(null);
              setLoading(false);
              setResult(status.result || { complaintId: response.complaintId });
            } else if (status.status === 'failed') {
              stopPolling();
              setProcessingStatus(null);
              setSubmitError(status.detail || t('citizenPortal.processingFailed'));
              setLoading(false);
            } else {
              setProcessingStatus(status.status);
            }
          } catch {
            stopPolling();
            setSubmitError(t('citizenPortal.statusCheckError'));
            setLoading(false);
          }
        }, 1500);
      } else {
        setResult(response);
      }
    } catch (error: any) {
      setSubmitError(error.message);
      setProcessingStatus(null);
    } finally {
      if (!pollingRef.current) {
        setLoading(false);
      }
    }
  };

  const isProcessing = processingStatus && ['submitting', 'pending', 'processing'].includes(processingStatus);
  const isPhotoRetryable = photoUploadStatus === 'failed' && complaintIdRef.current;

  const steps = [t('citizenPortal.stepDetails'), t('citizenPortal.stepComplaint'), t('citizenPortal.stepLocation'), t('citizenPortal.stepPhoto'), t('citizenPortal.stepReview'), t('citizenPortal.stepSubmit')];

  const confettiColors = ['#3b82f6','#8b5cf6','#f59e0b','#16a34a','#ef4444','#06b6d4','#ea580c'];
  const confettiPieces = Array.from({ length: 24 }, (_, i) => ({
    left: `${(i / 24) * 100}%`, delay: `${i * 0.05}s`, color: confettiColors[i % confettiColors.length],
    size: 6 + (i % 3) * 2,
  }));

  const FAQ_DATA = [
    { q: "How do I track my complaint?", a: "Enter your complaint ID on the Track Complaint page or log in to see all your complaints under My Complaints." },
    { q: "What does Pending Verification mean?", a: "Your complaint has been marked resolved. You need to verify the resolution using the 6-digit code sent to you." },
    { q: "How do I reopen a resolved complaint?", a: "Open the complaint detail page and click Reopen if you're not satisfied." },
    { q: "How do I submit a complaint?", a: "Fill in the details on this page, add a location, optional photo, and submit. AI processes it automatically." },
    { q: "How do I rate a resolved complaint?", a: "After verifying the resolution, rate it using the star rating on the complaint detail page." },
    { q: "What happens after I submit?", a: "AI classifies, groups related complaints, assigns priority. You get a tracking ID and status updates." },
    { q: "How long does resolution take?", a: "Resolution time varies by category and department. Check your complaint for estimated time." },
    { q: "Can I edit my complaint?", a: "You can edit the description and location from the complaint detail page." },
    { q: "What is an incident?", a: "An incident groups multiple similar complaints together for efficient handling." },
    { q: "How is priority decided?", a: "Priority is based on cluster size, age, category severity, location, and trust score." },
    { q: "What is verification code?", a: "A 6-digit code sent via notification to confirm your issue has been resolved." },
    { q: "Can I submit anonymously?", a: "Authentication is required to submit complaints so you can track and verify them." },
    { q: "What languages are supported?", a: "English, Tamil, and Tanglish — our AI can understand all three." },
    { q: "What photo formats?", a: "JPG, PNG, and WebP are supported. Maximum size is 5MB." },
    { q: "How to contact support?", a: "Use the Help widget (bottom-right) for FAQs. For urgent issues, contact your ward councillor." },
    { q: "What is SLA?", a: "Service Level Agreement — target time for resolving different types of complaints." },
    { q: "Can I submit for another ward?", a: "Yes, select the correct ward when submitting your complaint." },
    { q: "What are tags?", a: "Tags help categorize complaints. They may be added automatically or by officers." },
    { q: "How to delete account?", a: "Contact your Executive to delete your account." },
    { q: "Is my data secure?", a: "Yes, all data is encrypted and handled according to Tamil Nadu data protection guidelines." },
  ];

  const handleChatQuery = () => {
    const q = chatQuery.toLowerCase().trim();
    if (!q) return;
    const keywords = q.split(/\s+/);
    const scored = FAQ_DATA.map(item => {
      const score = keywords.reduce((s, kw) => s + (item.q.toLowerCase().includes(kw) || item.a.toLowerCase().includes(kw) ? 1 : 0), 0);
      return { ...item, score };
    }).sort((a, b) => b.score - a.score).slice(0, 3).filter(item => item.score > 0);
    setChatAnswers(scored.length > 0 ? scored : [{ q: "No match found", a: "Please try rephrasing or check the Help widget for more options." }]);
  };

  if (result && !isProcessing) {
    try { localStorage.removeItem(DRAFT_KEY); } catch {}
    if (result.offline) {
      return (
        <div className="portal-container success">
          <div className="glass-card success-card">
            <WifiOff size={64} className="success-icon" style={{ color: '#f59e0b' }} />
            <h2>{t('citizenPortal.savedOfflineTitle')}</h2>
            <p>{t('citizenPortal.savedOfflineBody')}</p>
            <div className="summary-card">
              <p><strong>{t('citizenPortal.offlineReference')}</strong> {result.complaintId}</p>
              <p><strong>{t('citizenPortal.offlineDateTime')}</strong> {new Date().toLocaleString('en-IN')}</p>
              <p><strong>{t('citizenPortal.offlineWard')}</strong> {formData.ward || '—'}</p>
            </div>
            <div className="success-actions">
              <button onClick={() => navigate('/my-complaints')}>{t('citizenPortal.viewComplaintsButton')}</button>
              <button className="secondary" onClick={() => navigate('/citizen')}>{t('citizenPortal.submitAnotherButton')}</button>
            </div>
          </div>
        </div>
      );
    }
    return (
    <div className="portal-container success">
      <div className="glass-card success-card receipt" id="complaint-receipt">
        <div className="confetti-container">
          {confettiPieces.map((p, i) => (
            <div key={i} className="confetti-piece" style={{ left: p.left, animationDelay: p.delay, background: p.color, width: p.size, height: p.size }} />
          ))}
        </div>
        <CheckCircle size={64} className="success-icon" />
        <h2>{t('citizenPortal.successTitle')}</h2>
        <p>{t('citizenPortal.successBody')}</p>
        {result.duplicate && (
          <div className="merge-notice">
            📋 {t('citizenPortal.mergeNoticeText', { count: result.cluster_size - 1 })}
            <br />
            Current status: <strong>{result.incident_status || 'open'}</strong>
          </div>
        )}
        <div className="summary-card">
          <p><strong>{t('citizenPortal.summaryComplaintId')}</strong> {result.complaintId}</p>
          <p><strong>Date/Time</strong> {new Date().toLocaleString('en-IN')}</p>
          {result.predictedCategory && <p><strong>{t('citizenPortal.summaryCategory')}</strong> {result.predictedCategory}</p>}
          <p><strong>Ward</strong> {formData.ward || '—'}</p>
          <p><strong>Description</strong> {formData.description?.slice(0, 200)}{formData.description?.length > 200 ? '…' : ''}</p>
          {result.priority && <p><strong>{t('citizenPortal.summaryPriority')}</strong> {result.priority}</p>}
          {result.department && <p><strong>Department</strong> {result.department}</p>}
          {result.incidentId && <p><strong>{t('citizenPortal.summaryIncidentId')}</strong> {result.incidentId}</p>}
        </div>
        <div className="success-actions">
          <button onClick={() => navigate('/my-complaints')}>{t('citizenPortal.viewComplaintsButton')}</button>
          <button className="secondary" onClick={() => navigate('/citizen')}>{t('citizenPortal.submitAnotherButton')}</button>
          <button className="secondary print-receipt-btn" onClick={() => window.print()}>🖨 Print Receipt</button>
        </div>
      </div>
    </div>
  );
  }

  if (isProcessing) return (
    <div className="portal-container success">
      <div className="glass-card success-card">
        <Clock size={64} className="processing-icon" />
        <h2>{t('citizenPortal.processingTitle')}</h2>
        <p>{t('citizenPortal.processingSubtitle')}</p>
        <div className="processing-status">
          {photoUploadStatus !== 'failed' && <Loader2 className="spinner" size={32} />}
          <p className="status-text">
            {photoUploadStatus === 'failed'
              ? t('citizenPortal.photoFailedStatus')
              : processingStatus === 'submitting'
                ? t('citizenPortal.statusSubmitting')
                : processingStatus === 'pending'
                  ? t('citizenPortal.statusStarting')
                  : t('citizenPortal.statusProcessing')}
          </p>
          {photoUploadStatus === 'uploading' && <p className="status-text">{t('citizenPortal.statusUploading')}</p>}
          {photoUploadStatus === 'done' && selectedFile && <p className="status-text photo-done">{t('citizenPortal.statusPhotoDone')}</p>}
        </div>
        {submitError && (
          <div className="error-banner">
            <AlertCircle size={16} />
            <span>{submitError}</span>
          </div>
        )}
        {isPhotoRetryable && (
          <div className="photo-retry-actions">
            <button className="retry-btn" onClick={retryPhotoUpload}>
              <Upload size={16} /> {t('citizenPortal.retryPhotoButton')}
            </button>
            <button className="skip-btn" onClick={skipPhoto}>
              {t('citizenPortal.skipPhotoButton')}
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="portal-container">
      <Header title={t('citizenPortal.headerTitle')} subtitle={t('citizenPortal.headerSubtitle')} />
      {ward && nearMeStories && nearMeStories.length > 0 && (
        <div className="nearme-section">
          <div className="nearme-header">
            <CheckCircle size={16} />
            <span>{t('citizenPortal.nearMeTitle', { ward })}</span>
          </div>
          <div className="nearme-list">
            {nearMeStories.slice(0, 3).map((s, i) => (
              <div key={i} className="nearme-item">
                <span className="nearme-category">{s.category}</span>
                <span className="nearme-note">{s.resolution_note || s.days_to_resolve + ' days'}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {offlineQueueCount > 0 && (
        <div className="offline-queue-indicator">
          <WifiOff size={14} />
          <span>{offlineQueueCount === 1 ? t('citizenPortal.offlineQueueMessage', { count: 1 }) : t('citizenPortal.offlineQueueMessagePlural', { count: offlineQueueCount })}</span>
        </div>
      )}
      <div className="wizard glass-card">
        <div className="progress-bar-container">
          <div className="progress-fill" style={{ width: `${(step / steps.length) * 100}%` }}></div>
        </div>
        <div className="steps-header">{steps[step - 1]}</div>
        
        <div className="form-content">
          {step === 1 && (
            <div className="form-step">
              <input
                type="text"
                placeholder={t('citizenPortal.fullNamePlaceholder')}
                value={formData.full_name}
                onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                required
              />
              <input
                type="email"
                placeholder={t('citizenPortal.emailPlaceholder')}
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>
          )}
          {step === 2 && (
            <div className="form-step">
              {/* Quick Start Templates */}
              <div className="quick-templates">
                <h4>{t('citizenPortal.quickStart')}</h4>
                <p className="template-hint">{t('citizenPortal.pickTemplate')}</p>
                <div className="template-grid">
                  {COMPLAINT_TEMPLATES.map((tmpl, i) => (
                    <button
                      key={i}
                      className="template-btn"
                      onClick={() => {
                        setFormData(prev => ({ ...prev, title: tmpl.title, description: tmpl.description }));
                        setSuggestedCategory(tmpl.category);
                      }}
                    >
                      <span className="template-category">{tmpl.category}</span>
                      <span className="template-title">{tmpl.title}</span>
                    </button>
                  ))}
                </div>
              </div>
              <input
                type="text"
                placeholder={t('citizenPortal.complaintTitlePlaceholder')}
                value={formData.title}
                onChange={e => { setFormData({ ...formData, title: e.target.value }); if (fieldErrors.title) setFieldErrors(prev => ({ ...prev, title: '' })); }}
                className={fieldErrors.title ? 'input-error' : ''}
              />
              {fieldErrors.title && <p className="field-error">{fieldErrors.title}</p>}
              <div className="voice-textarea-wrapper">
                <textarea
                  placeholder={t('citizenPortal.descriptionPlaceholder')}
                  value={formData.description}
                  onChange={e => { setFormData({ ...formData, description: e.target.value }); if (fieldErrors.description) setFieldErrors(prev => ({ ...prev, description: '' })); }}
                  className={fieldErrors.description ? 'input-error' : ''}
                />
                {formData.description.length < 20 && formData.description.length > 0 && (
                  <p style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: 4 }}>
                    <Clock size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                    {t('citizenPortal.addMoreDetails')}: {t('citizenPortal.detailHint')}
                  </p>
                )}
                <VoiceInput
                  onTranscript={(text) => setFormData(prev => ({ ...prev, description: text }))}
                  disabled={loading}
                />
              </div>
              {fieldErrors.description && <p className="field-error">{fieldErrors.description}</p>}
              <div className="cat-guide-hint">
                <Trans i18nKey="citizenPortal.categoryGuideHint">
                  Not sure which category applies? See the <Link to="/categories">Category Guide</Link>
                </Trans>
              </div>
              {suggestLoading && <div className="cat-suggest">{t('citizenPortal.analyzingDescription')}</div>}
              {suggestedCategory && !catSuggestAccepted && (
                <div className="cat-suggest">
                  Suggested category: <strong>{suggestedCategory}</strong>
                  <span className="accept-link" onClick={() => setCatSuggestAccepted(true)}>Accept</span>
                </div>
              )}
            </div>
          )}
          {step === 3 && (
            <div className="form-step">
              <input
                type="text"
                placeholder={t('citizenPortal.locationPlaceholder')}
                value={formData.location}
                onChange={e => { setFormData({ ...formData, location: e.target.value }); if (fieldErrors.location) setFieldErrors(prev => ({ ...prev, location: '' })); }}
                className={fieldErrors.location ? 'input-error' : ''}
              />
              {fieldErrors.location && <p className="field-error">{fieldErrors.location}</p>}
              <label style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: -8 }}>
                {t('citizenPortal.searchMapLabel')}
              </label>
              <AddressSearch
                value={formData.address}
                onChange={(data) => setFormData(prev => ({
                  ...prev,
                  address: data.address,
                  latitude: data.lat,
                  longitude: data.lon,
                  ward: data.ward || prev.ward || '',
                }))}
                placeholder={t('citizenPortal.addressSearchPlaceholder')}
              />
              {formData.latitude !== 0 && (
                <small style={{ color: '#60a5fa', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <MapPin size={12} />
                  {t('citizenPortal.locationPinned')}
                </small>
              )}
            </div>
          )}
          {step === 4 && (
            <div className="form-step">
              <label className="upload-box">
                <Upload size={18} />
                <span>{selectedFile ? selectedFile.name : t('citizenPortal.photoUploadLabel')}</span>
                <input
                  type="file"
                  accept=".jpg,.jpeg,.png"
                  onChange={e => {
                    setPhotoError(null);
                    const file = e.target.files?.[0];
                    if (!file) { setSelectedFile(null); setImagePreview(null); return; }
                    if (!['image/jpeg', 'image/png'].includes(file.type)) {
                      setPhotoError(t('citizenPortal.photoErrorFormat'));
                      return;
                    }
                    if (file.size > 5 * 1024 * 1024) {
                      setPhotoError(t('citizenPortal.photoErrorSize'));
                      return;
                    }
                    setSelectedFile(file);
                    setImagePreview(URL.createObjectURL(file));
                  }}
                />
              </label>
              {selectedFile && ['uploading', 'idle'].includes(photoUploadStatus) && (
                <p className="compressing-hint" style={{ fontSize: '0.8rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
                  <Loader2 size={14} className="spin" /> {t('citizenPortal.compressingImage')}
                </p>
              )}
              {photoError && <p className="field-error">{photoError}</p>}
              {imagePreview && <img src={imagePreview} className="preview" alt={t('complaintDetail.imageAlt')} />}
              {!selectedFile && !imagePreview && (
                <p className="photo-hint">{t('citizenPortal.photoHint')}</p>
              )}
            </div>
          )}
          {step === 5 && (
            <div className="form-step review-step">
              <h3>{t('citizenPortal.reviewTitle')}</h3>
              <div className="review-grid">
                <div><strong>{t('citizenPortal.reviewName')}</strong> {formData.full_name || '—'}</div>
                <div><strong>{t('citizenPortal.reviewEmail')}</strong> {formData.email || '—'}</div>
                <div><strong>{t('citizenPortal.reviewTitleLabel')}</strong> {formData.title || '—'}</div>
                <div><strong>{t('citizenPortal.reviewLocation')}</strong> {formData.location || '—'}</div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <strong>{t('citizenPortal.reviewAddress')}</strong> {formData.address || formData.location || '—'}
                </div>
                {formData.latitude !== 0 && (
                  <div style={{ gridColumn: '1 / -1' }}>
                    <strong>{t('citizenPortal.reviewLocationPinned')}</strong> {t('common.yes')}
                  </div>
                )}
              </div>
              <div className="tag-input-area">
                {tags.map((tag, i) => (
                  <span key={i} className="tag-badge">{tag} <span className="tag-remove" onClick={() => setTags(prev => prev.filter((_, j) => j !== i))}>×</span></span>
                ))}
                {tags.length < 3 && (
                  <input className="tag-input" placeholder="Add tag..." value={tagInput}
                    onChange={e => setTagInput(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && tagInput.trim()) { setTags(prev => [...prev, tagInput.trim()]); setTagInput(''); } }}
                  />
                )}
              </div>
            </div>
          )}
          {step === 6 && <DuplicateCheckStep
            formData={formData}
            submitError={submitError}
            loading={loading}
            handleSubmit={handleSubmit}
            duplicateWarnings={duplicateWarnings}
            setDuplicateWarnings={setDuplicateWarnings}
            dupCheckDone={dupCheckDone}
            setDupCheckDone={setDupCheckDone}
            dupChecking={dupChecking}
            setDupChecking={setDupChecking}
            t={t}
          />}
        </div>

        <div className="wizard-controls">
          <button disabled={step === 1} onClick={() => setStep(s => s - 1)}><ChevronLeft /> {t('citizenPortal.backButton')}</button>
          <button disabled={step >= steps.length} onClick={() => setStep(s => s + 1)}>{t('citizenPortal.nextButton')} <ChevronRight /></button>
        </div>
      </div>
      {/* F6: FAQ Chatbot */}
      <div className="faq-chatbot" style={{ marginTop: '2rem', background: '#1e293b', borderRadius: '12px', padding: '1.5rem', border: '1px solid #334155' }}>
        <h4>{t('citizenPortal.faqBotTitle')}</h4>
        <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.75rem' }}>{t('citizenPortal.faqBotSubtitle')}</p>
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <input
            type="text"
            value={chatQuery}
            onChange={(e) => setChatQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleChatQuery(); }}
            placeholder={t('citizenPortal.faqPlaceholder')}
            style={{ flex: 1, padding: '0.6rem 1rem', borderRadius: '8px', border: '1px solid #475569', background: '#0f172a', color: '#e2e8f0' }}
          />
          <button onClick={handleChatQuery} className="btn btn-primary">{t('citizenPortal.faqAsk')}</button>
        </div>
        {chatAnswers.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {chatAnswers.map((a: any, i: number) => (
              <div key={i} style={{ background: '#0f172a', borderRadius: '8px', padding: '0.75rem 1rem' }}>
                <p style={{ fontWeight: 600, fontSize: '0.85rem', color: '#60a5fa' }}>Q: {a.question}</p>
                <p style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>{a.answer}</p>
              </div>
            ))}
            <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>{t('citizenPortal.faqDisclaimer')}</p>
          </div>
        )}
      </div>
      <HelpWidget />
    </div>
  );
};

export default CitizenPortal;
