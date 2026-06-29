import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import './CitizenPortal.css';

const CitizenPortal = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({ title: '', description: '', location: '', ward: '', image_path: '' });
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
      setFormData({...formData, image_path: 'Prototype Preview: ' + file.name});
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await api.submitComplaint(formData);

console.log("API Response:", response);

setResult(response);

console.log("Result state being set:", response);
    } catch (error: any) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };
console.log("Current result:", result);
  if (result) {
    return (
      <div className="portal-container">
        <div className="success-card">
          <h2>Complaint Submitted</h2>
          <div className="card-grid">
            <p><strong>Complaint ID:</strong> {result.complaintId}</p>
            <p><strong>Incident ID:</strong> {result.incidentId}</p>
            <p><strong>Category:</strong> {result.predictedCategory}</p>
            <p><strong>Priority:</strong> {result.priority}</p>
            <p><strong>Confidence:</strong> {(result.confidence * 100).toFixed(1)}%</p>
            <p><strong>Duplicate:</strong> {result.duplicate ? 'Yes' : 'No'}</p>
            <p><strong>Status:</strong> Under Review</p>
          </div>
          <div className="button-group">
            <button onClick={() => navigate('/')}>View Dashboard</button>
            <button onClick={() => {setResult(null); setImagePreview(null);}}>Submit Another Complaint</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="portal-container">
      {loading ? (
        <div className="loading-state">🤖 AI is analysing your complaint...</div>
      ) : (
        <form onSubmit={handleSubmit} className="complaint-form">
          <h2>Submit Complaint</h2>
          <input type="text" placeholder="Title" required onChange={(e) => setFormData({...formData, title: e.target.value})} />
          <textarea placeholder="Description" required onChange={(e) => setFormData({...formData, description: e.target.value})} />
          <input type="text" placeholder="Location" required onChange={(e) => setFormData({...formData, location: e.target.value})} />
          <input type="text" placeholder="Ward" required onChange={(e) => setFormData({...formData, ward: e.target.value})} />
          
          <div className="file-upload">
            <label>Upload Image (JPG/PNG):</label>
            <input type="file" accept="image/png, image/jpeg" onChange={handleFileChange} />
            {imagePreview && <img src={imagePreview} alt="Preview" className="preview-img" />}
          </div>
          
          <button type="submit">Submit Complaint</button>
        </form>
      )}
    </div>
  );
};

export default CitizenPortal;
