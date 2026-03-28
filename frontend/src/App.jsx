import { useState, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import Dashboard from './components/Dashboard';
import EmployeeDashboard from './components/EmployeeDashboard';
import HODDashboard from './components/HODDashboard';
import { getUser } from './api';

function App() {
  const [user, setUser] = useState(getUser());
  const [view, setView] = useState('login');

  useEffect(() => {
    const checkAuth = () => setUser(getUser());
    window.addEventListener('storage', checkAuth);
    return () => window.removeEventListener('storage', checkAuth);
  }, []);

  if (!user) {
    if (view === 'register') return <RegisterPage onBackToLogin={() => setView('login')} />;
    return <LoginPage onLogin={setUser} onRegister={() => setView('register')} />;
  }

  if (user?.role === 'head') return <HODDashboard />;
  if (user?.role === 'employee') return <EmployeeDashboard />;
  return <Dashboard />;   // manager
}

export default App;