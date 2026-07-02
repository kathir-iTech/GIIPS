import React from 'react';
import { Link } from 'react-router-dom';
import { UserPlus, LogIn, User } from 'lucide-react';
import './Auth.css';

const CitizenServices = () => {
  return (
    <div className="auth-page">
      <div className="auth-card glass-card">
        <div className="auth-header">
          <User size={32} className="auth-icon" />
          <h2>Citizen Services</h2>
          <p>Submit and track grievances</p>
        </div>
        
        <div className="auth-form">
          <Link to="/register" className="auth-button">
            <UserPlus size={18} className="input-icon" />
            Register
          </Link>
          <Link to="/login" className="auth-button secondary">
            <LogIn size={18} className="input-icon" />
            Login
          </Link>
        </div>
      </div>
    </div>
  );
};

export default CitizenServices;