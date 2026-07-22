import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import AddressSearch from '../components/AddressSearch';
import { CheckCircle, Upload, MapPin, FileText, ChevronRight, ChevronLeft, Loader2, Sparkles, AlertCircle, Clock } from 'lucide-react';
import './CitizenPortal.css';

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
      const response = await api.submitComplaint(formData);
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

  if (result && !isProcessing) return (
    <div className="portal-container success">
      <div className="glass-card success-card">
        <CheckCircle size={64} className="success-icon" />
        <h2>{t('citizenPortal.successTitle')}</h2>
        <p>{t('citizenPortal.successBody')}</p>
        <div className="summary-card">
          <p><strong>{t('citizenPortal.summaryComplaintId')}</strong> {result.complaintId}</p>
          {result.priority && <p><strong>{t('citizenPortal.summaryPriority')}</strong> {result.priority}</p>}
          {result.predictedCategory && <p><strong>{t('citizenPortal.summaryCategory')}</strong> {result.predictedCategory}</p>}
          {result.incidentId && <p><strong>{t('citizenPortal.summaryIncidentId')}</strong> {result.incidentId}</p>}
        </div>
        <div className="success-actions">
          <button onClick={() => navigate('/my-complaints')}>{t('citizenPortal.viewComplaintsButton')}</button>
          <button className="secondary" onClick={() => navigate('/citizen')}>{t('citizenPortal.submitAnotherButton')}</button>
        </div>
      </div>
    </div>
  );

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
              <textarea
                placeholder={t('citizenPortal.descriptionPlaceholder')}
                value={formData.description}
                onChange={e => { setFormData({ ...formData, description: e.target.value }); if (fieldErrors.description) setFieldErrors(prev => ({ ...prev, description: '' })); }}
                className={fieldErrors.description ? 'input-error' : ''}
              />
              {fieldErrors.description && <p className="field-error">{fieldErrors.description}</p>}
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
                  ward: prev.ward || '',
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
            </div>
          )}
          {step === 6 && (
            <div className="form-step ai-step">
              <Sparkles className="ai-icon" />
              <h3>{t('citizenPortal.confirmTitle')}</h3>
              <p>{t('citizenPortal.confirmBody')}</p>
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
          )}
        </div>

        <div className="wizard-controls">
          <button disabled={step === 1} onClick={() => setStep(s => s - 1)}><ChevronLeft /> {t('citizenPortal.backButton')}</button>
          <button disabled={step >= steps.length} onClick={() => setStep(s => s + 1)}>{t('citizenPortal.nextButton')} <ChevronRight /></button>
        </div>
      </div>
    </div>
  );
};

export default CitizenPortal;
