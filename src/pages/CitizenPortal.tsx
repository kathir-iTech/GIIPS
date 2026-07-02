import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import { CheckCircle, Upload, MapPin, FileText, ChevronRight, ChevronLeft, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import './CitizenPortal.css';

const CitizenPortal = () => {
  const navigate = useNavigate();
  const { token } = useAuth();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    title: '',
    description: '',
    location: '',
    ward: '',
  });
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setSubmitError(null);
    try {
      const response = await api.submitComplaint(formData, token);
      setResult(response);
    } catch (error: any) {
      setSubmitError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const steps = ['Details', 'Complaint', 'Location', 'Review', 'AI Preview', 'Success'];

  if (result) return (
    <div className="portal-container success">
      <div className="glass-card success-card">
        <CheckCircle size={64} className="success-icon" />
        <h2>Submission Received</h2>
        <p>Your complaint has been processed by the AI pipeline.</p>
        <div className="summary-card">
          <p><strong>Complaint ID:</strong> {result.complaintId}</p>
          <p><strong>Priority:</strong> {result.priority}</p>
        </div>
        <div className="success-actions">
          <button onClick={() => navigate('/my-complaints')}>View My Complaints</button>
          <button className="secondary" onClick={() => navigate('/citizen')}>Submit Another</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="portal-container">
      <Header title="Citizen Portal" subtitle="Submit grievance securely" />
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
                placeholder="Full Name"
                value={formData.full_name}
                onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                required
              />
              <input
                type="email"
                placeholder="Email Address"
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
                placeholder="Complaint Title"
                value={formData.title}
                onChange={e => setFormData({ ...formData, title: e.target.value })}
              />
              <textarea
                placeholder="Detailed Description"
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
          )}
          {step === 3 && (
            <div className="form-step">
              <input
                type="text"
                placeholder="Location / Area"
                value={formData.location}
                onChange={e => setFormData({ ...formData, location: e.target.value })}
              />
              <input
                type="text"
                placeholder="Ward Number"
                value={formData.ward}
                onChange={e => setFormData({ ...formData, ward: e.target.value })}
              />
            </div>
          )}
          {step === 4 && (
            <div className="form-step">
              <label className="upload-box">
                <Upload size={18} />
                <span>Select Image (optional)</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={e => e.target.files && e.target.files[0] && setImagePreview(URL.createObjectURL(e.target.files[0]))}
                />
              </label>
              {imagePreview && <img src={imagePreview} className="preview" alt="Preview" />}
            </div>
          )}
          {step === 5 && (
            <div className="form-step review-step">
              <h3>Review Details</h3>
              <div className="review-grid">
                <div><strong>Name:</strong> {formData.full_name || '—'}</div>
                <div><strong>Email:</strong> {formData.email || '—'}</div>
                <div><strong>Title:</strong> {formData.title || '—'}</div>
                <div><strong>Location:</strong> {formData.location || '—'}</div>
                <div><strong>Ward:</strong> {formData.ward || '—'}</div>
              </div>
            </div>
          )}
          {step === 6 && (
            <div className="form-step ai-step">
              <Sparkles className="ai-icon" />
              <h3>AI Preview</h3>
              <p>Analyzing priority and department...</p>
              {submitError && (
                <div className="error-banner">
                  <AlertCircle size={16} />
                  <span>{submitError}</span>
                </div>
              )}
              <button className="auth-button" onClick={handleSubmit} disabled={loading}>
                {loading ? 'Processing...' : 'Confirm Submission'}
              </button>
            </div>
          )}
        </div>

        <div className="wizard-controls">
          <button disabled={step === 1} onClick={() => setStep(s => s - 1)}><ChevronLeft /> Back</button>
          <button disabled={step >= steps.length - 1} onClick={() => setStep(s => s + 1)}>Next <ChevronRight /></button>
        </div>
      </div>
    </div>
  );
};

export default CitizenPortal;
