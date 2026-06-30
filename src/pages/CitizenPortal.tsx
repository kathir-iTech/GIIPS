import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Header from '../components/Header';
import { CheckCircle, Upload, MapPin, FileText, ChevronRight, ChevronLeft, Loader2, Sparkles } from 'lucide-react';
import './CitizenPortal.css';

const CitizenPortal = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({ title: '', description: '', location: '', ward: '', image_path: '' });
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const response = await api.submitComplaint(formData);
      setResult(response);
    } catch (error: any) { alert(error.message); } finally { setLoading(false); }
  };

  const steps = ['Details', 'Complaint', 'Location', 'Upload', 'Review', 'AI Preview', 'Success'];

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
        <button onClick={() => navigate('/')}>Return to Dashboard</button>
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
          {step === 1 && <div className="form-step"><input type="text" placeholder="Personal Name" /> <input type="email" placeholder="Email" /></div>}
          {step === 2 && <div className="form-step"><input type="text" placeholder="Complaint Title" onChange={e => setFormData({...formData, title: e.target.value})} /><textarea placeholder="Detailed Description" onChange={e => setFormData({...formData, description: e.target.value})} /></div>}
          {step === 3 && <div className="form-step"><input type="text" placeholder="Location" onChange={e => setFormData({...formData, location: e.target.value})} /><input type="text" placeholder="Ward" onChange={e => setFormData({...formData, ward: e.target.value})} /></div>}
          {step === 4 && <div className="form-step"><label className="upload-box"><Upload /> <input type="file" onChange={e => e.target.files && setImagePreview(URL.createObjectURL(e.target.files[0]))} /> Select Image</label>{imagePreview && <img src={imagePreview} className="preview" alt="Preview" />}</div>}
          {step === 5 && <div className="form-step"><h3>Review Details</h3><p>{formData.title}</p><p>{formData.location}</p></div>}
          {step === 6 && <div className="form-step"><Sparkles className="ai-icon" /><h3>AI Preview</h3><p>Analyzing priority and department...</p>{loading ? <Loader2 className="animate-spin" /> : <button onClick={handleSubmit}>Confirm Submission</button>}</div>}
        </div>

        <div className="wizard-controls">
          <button disabled={step === 1} onClick={() => setStep(s => s - 1)}><ChevronLeft /> Back</button>
          <button disabled={step === 6} onClick={() => setStep(s => s + 1)}>Next <ChevronRight /></button>
        </div>
      </div>
    </div>
  );
};
export default CitizenPortal;
