import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { Link } from 'react-router-dom';
import './Unauthorized.css';

const Unauthorized = () => (
  <div className="unauthorized-page">
    <div className="unauthorized-card">
      <ShieldAlert size={56} className="unauthorized-icon" />
      <h1>Access Denied</h1>
      <p>You do not have the required permissions to view this page.</p>
      <Link to="/" className="back-link">Return to Home</Link>
    </div>
  </div>
);

export default Unauthorized;
