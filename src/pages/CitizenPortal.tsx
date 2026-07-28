import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation, Trans } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import AddressSearch from '../components/AddressSearch';
import VoiceInput from '../components/VoiceInput';
import HelpWidget from '../components/HelpWidget';
import { CheckCircle, Upload, MapPin, FileText, ChevronRight, ChevronLeft, Loader2, Sparkles, AlertCircle, Clock } from 'lucide-react';
import './CitizenPortal.css';

const DRAFT_KEY = 'giips_complaint_wizard_draft';

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
  t: (key: string) => string;
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
          <Loader2 className="spinner" size={16} /> Checking for similar complaints…
        </div>
      )}

      {duplicateWarnings.length > 0 && (
        <div className="duplicate-warning">
          <AlertCircle size={18} />
          <div>
            <strong>Possible duplicate issue detected</strong>
            <p>The following similar complaint{duplicateWarnings.length > 1 ? 's were' : ' was'} found nearby:</p>
            <ul>
              {duplicateWarnings.map((d, i) => (
                <li key={i}>
                  <strong>{d.title || d.category}</strong>
                  {d.distance_km != null && <span> — {d.distance_km.toFixed(2)} km away</span>}
                  {d.status && <span> [{d.status}]</span>}
                </li>
              ))}
            </ul>
            <p className="dup-note">You can still submit your complaint if this is a different issue.</p>
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
  const [suggestedCategory, setSuggestedCategory] = useState<string | null>(null);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [catSuggestAccepted, setCatSuggestAccepted] = useState(false);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
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

  if (result && !isProcessing) {
    try { localStorage.removeItem(DRAFT_KEY); } catch {}
    return (
    <div className="portal-container success">
      <div className="glass-card success-card receipt" id="complaint-receipt">
        <CheckCircle size={64} className="success-icon" />
        <h2>{t('citizenPortal.successTitle')}</h2>
        <p>{t('citizenPortal.successBody')}</p>
        {result.duplicate && (
          <div className="merge-notice">
            📋 Your complaint has been grouped with <strong>{result.cluster_size - 1} other report{(result.cluster_size - 1) !== 1 ? 's' : ''}</strong> of the same issue.
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
              {suggestLoading && <div className="cat-suggest">Analyzing description...</div>}
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
              {photoError && <p className="field-error">{photoError}</p>}
              {imagePreview && <img src={imagePreview} className="preview" alt={t('complaintDetail.imageAlt')} />}
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
      <HelpWidget />
    </div>
  );
};

export default CitizenPortal;
