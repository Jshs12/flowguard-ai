import { useState } from 'react';
import { api } from '../api';


export default function RegisterPage({ onBackToLogin }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'employee',
    department: 'Engineering'
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);


  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);


    if (formData.role === 'employee' && !formData.department) {
      setError('Department is required for employees');
      setLoading(false);
      return;
    }


    try {
      await api('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      setSuccess(true);
      setTimeout(() => onBackToLogin(), 2000);
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="login-page">
      <div className="login-card">
        <h1>JOIN FLOWGUARD</h1>
        <p>Create your autonomous workspace account</p>


        {error && <div className="login-error">{error}</div>}
        {success && (
          <div className="badge badge-online" style={{ marginBottom: '1rem', width: '100%', justifyContent: 'center' }}>
            Account created! Redirecting...
          </div>
        )}


        <form onSubmit={handleSubmit}>
          <input
            className="input"
            type="text"
            placeholder="Full Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
          <input
            className="input"
            type="email"
            placeholder="Email Address"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
          <input
            className="input"
            type="password"
            placeholder="Create Password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
          />


          <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
            <label className="label">I am a:</label>
            <select
              className="select"
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
            >
              <option value="employee">Employee</option>
              <option value="manager">Manager</option>
              <option value="head">Head of Department (HOD)</option>
            </select>
          </div>


          {formData.role === 'employee' && (
            <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
              <label className="label">Department</label>
              <select
                className="select"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              >
                <option>Engineering</option>
                <option>Marketing</option>
                <option>Finance</option>
                <option>Design</option>
                <option>Legal</option>
              </select>
            </div>
          )}


          <button className="btn btn-primary" type="submit" disabled={loading || success}>
            {loading ? <span className="spinner" /> : 'CREATE ACCOUNT'}
          </button>
        </form>


        <button
          className="btn btn-secondary"
          style={{ width: '100%', marginTop: '1rem' }}
          onClick={onBackToLogin}
        >
          BACK TO LOGIN
        </button>
      </div>
    </div>
  );
}