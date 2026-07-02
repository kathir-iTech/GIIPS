import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { UserPlus, Search, Lock, Unlock } from 'lucide-react';
import './Admin.css';

interface Officer {
  id: string;
  full_name: string;
  email: string;
  district: string;
  created_at: string;
  status: string;
}

const OfficerManagement = () => {
  const { token } = useAuth();
  const [officers, setOfficers] = useState<Officer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [formData, setFormData] = useState({ full_name: '', email: '', password: '', district: '', department: '' });

  useEffect(() => {
    fetchOfficers();
  }, []);

  const fetchOfficers = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await api.get('/admin/officers', token);
      const data = await response.json();
      setOfficers(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const filteredOfficers = officers.filter(o => 
    o.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.district.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDisable = async (id: string) => {
    if (!token) return;
    await api.patch(`/admin/officers/${id}/disable`, {}, token);
    fetchOfficers();
  };

  const handleEnable = async (id: string) => {
    if (!token) return;
    await api.patch(`/admin/officers/${id}/enable`, {}, token);
    fetchOfficers();
  };

  const handleCreateOfficer = async () => {
    if (!token) return;
    await api.post('/admin/officers', formData, token);
    setShowAddDialog(false);
    fetchOfficers();
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Officer Management</h1>
        <p>Manage government officers and their assignments</p>
      </div>

      <div className="admin-controls">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search officers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <button className="btn-primary" onClick={() => setShowAddDialog(true)}>
          <UserPlus size={16} /> Add Officer
        </button>
      </div>

      <div className="stats-cards">
        <div className="stat-card">
          <h3>{officers.length}</h3>
          <p>Total Officers</p>
        </div>
        <div className="stat-card">
          <h3>{officers.filter(o => o.status === 'active').length}</h3>
          <p>Active Officers</p>
        </div>
        <div className="stat-card">
          <h3>{officers.filter(o => o.status === 'disabled').length}</h3>
          <p>Disabled Officers</p>
        </div>
      </div>

      <div className="table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Officer ID</th>
              <th>Name</th>
              <th>Email</th>
              <th>District</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="loading">Loading...</td></tr>
            ) : filteredOfficers.length === 0 ? (
              <tr><td colSpan={7} className="empty">No officers found</td></tr>
            ) : (
              filteredOfficers.map(officer => (
                <tr key={officer.id}>
                  <td>{officer.id}</td>
                  <td>{officer.full_name}</td>
                  <td>{officer.email}</td>
                  <td>{officer.district}</td>
                  <td><span className={`status ${officer.status}`}>{officer.status}</span></td>
                  <td>{officer.created_at?.split('T')[0]}</td>
                  <td>
                    <div className="actions">
                      {officer.status === 'active' ? 
                        <button onClick={() => handleDisable(officer.id)}><Lock size={16} /></button> :
                        <button onClick={() => handleEnable(officer.id)}><Unlock size={16} /></button>
                      }
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showAddDialog && (
        <div className="dialog-overlay">
          <div className="dialog">
            <h3>Add New Officer</h3>
            <div className="form-grid">
              <input placeholder="Full Name" value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} />
              <input placeholder="Email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
              <input placeholder="District" value={formData.district} onChange={e => setFormData({...formData, district: e.target.value})} />
              <input placeholder="Department" value={formData.department} onChange={e => setFormData({...formData, department: e.target.value})} />
              <input type="password" placeholder="Password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} />
            </div>
            <div className="dialog-actions">
              <button onClick={() => setShowAddDialog(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleCreateOfficer}>Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OfficerManagement;