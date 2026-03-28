import { useState } from 'react';
import { api, setAuth } from '../api';


export default function LoginPage({ onLogin, onRegister }) {
  const [role, setRole] = useState('manager');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [department, setDepartment] = useState('Engineering');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);


  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          username,
          password,
          department: role === 'employee' ? department : null
        }),
      });
      setAuth(data);
      onLogin(data);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="login-page">
      <div className="login-card">
        <div style={{ marginBottom: '2rem' }}>
          <h1>FLOWGUARD</h1>
          <p>Autonomous Workflow Intelligence</p>
        </div>


        <div className="tabs" style={{ justifyContent: 'center', marginBottom: '1.5rem' }}>
          <button
            className={`tab ${role === 'manager' ? 'active' : ''}`}
            onClick={() => setRole('manager')}
          >
            MANAGER
          </button>
          <button
            className={`tab ${role === 'employee' ? 'active' : ''}`}
            onClick={() => setRole('employee')}
          >
            EMPLOYEE
          </button>
          <button
            className={`tab ${role === 'head' ? 'active' : ''}`}
            onClick={() => setRole('head')}
          >
            HOD
          </button>
        </div>


        {error && <div className="login-error">{error}</div>}


        <form onSubmit={handleSubmit}>
          <input
            className="input"
            type="text"
            placeholder={
              role === 'head' ? 'HOD Email/Username' :
                role === 'manager' ? 'Manager Email/Username' :
                  'Employee Email/Username'
            }
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            id="login-username"
          />
          <input
            className="input"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            id="login-password"
          />


          {role === 'employee' && (
            <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
              <label className="label">Department</label>
              <select
                className="select"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              >
                <option>Engineering</option>
                <option>Marketing</option>
                <option>Finance</option>
                <option>Design</option>
                <option>Legal</option>
              </select>
            </div>
          )}


          <button className="btn btn-primary" type="submit" disabled={loading} id="login-submit">
            {loading ? <span className="spinner" /> : 'SIGN IN'}
          </button>
        </form>


        <div style={{ marginTop: '1rem' }}>
          <button
            className="btn btn-secondary"
            style={{ width: '100%' }}
            onClick={onRegister}
          >
            CREATE AN ACCOUNT
          </button>
        </div>


      </div>
    </div>
  );
}