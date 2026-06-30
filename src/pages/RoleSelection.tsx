import { Link } from 'react-router-dom';
import { User, ShieldAlert, BarChart3 } from 'lucide-react';
import './RoleSelection.css';

const RoleSelection = () => {
  return (
    <div className="role-selection">
      <h1>Select Your Portal</h1>
      <div className="role-grid">
        <Link to="/citizen" className="role-card">
          <User size={48} />
          <h2>Citizen Portal</h2>
          <p>Submit and track grievances</p>
          <span className="btn">Enter</span>
        </Link>
        <Link to="/officer" className="role-card">
          <ShieldAlert size={48} />
          <h2>Officer Dashboard</h2>
          <p>Prioritize and resolve incidents</p>
          <span className="btn">Enter</span>
        </Link>
        <Link to="/executive" className="role-card">
          <BarChart3 size={48} />
          <h2>Executive Dashboard</h2>
          <p>City-wide intelligence</p>
          <span className="btn">Enter</span>
        </Link>
      </div>
    </div>
  );
};

export default RoleSelection;
