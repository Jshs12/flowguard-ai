import { useState, useEffect } from 'react';
import { api, getUser, checkHealth } from '../api';

function Navbar({ user, online }) {
    const handleLogout = () => {
        localStorage.removeItem('fg_token');
        localStorage.removeItem('fg_user');
        window.location.reload();
    };
    return (
        <nav className="navbar">
            <div className="navbar-brand">
                <span className="navbar-logo">⚡ FLOWGUARD AI</span>
                <span className={`badge ${online ? 'badge-online' : 'badge-offline'}`}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', display: 'inline-block' }} />
                    {online ? 'ONLINE' : 'OFFLINE'}
                </span>
            </div>
            <div className="navbar-user">
                <span style={{ marginRight: '1rem' }}>
                    {user.full_name}{' '}
                    <span className="badge badge-in_progress">EMPLOYEE</span>
                </span>
                <button className="btn btn-secondary" onClick={handleLogout} style={{ padding: '6px 14px', fontSize: '0.72rem' }}>
                    Logout
                </button>
            </div>
        </nav>
    );
}

function RiskBadge({ score, isRisk }) {
    const color =
        isRisk ? 'var(--red)' :
            score > 0.75 ? 'var(--red)' :
                score > 0.5 ? 'var(--orange)' :
                    score > 0.25 ? 'var(--yellow)' :
                        'var(--green)';
    return (
        <div className="flex gap-1" style={{ alignItems: 'center' }}>
            <div className="risk-bar-bg">
                <div className="risk-bar-fill" style={{ width: `${score * 100}%`, background: color }} />
            </div>
            <span style={{ fontSize: '0.72rem', color, fontWeight: 600 }}>
                {(score * 100).toFixed(0)}%{isRisk ? ' ⚠️' : ''}
            </span>
        </div>
    );
}

function TimeLeft({ slaDeadline, deadline }) {
    const dl = slaDeadline || deadline;
    if (!dl) return <span style={{ color: 'var(--text-muted)' }}>No deadline</span>;
    const diff = new Date(dl) - new Date();
    if (diff <= 0) return <span style={{ color: 'var(--red)', fontWeight: 700 }}>⛔ Overdue</span>;
    const days = Math.floor(diff / 86400000);
    const hours = Math.floor((diff % 86400000) / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);

    let color;
    let text;
    if (days >= 1) {
        text = `${days}d ${hours}h left`;
        color = days <= 1 ? 'var(--red)' : days <= 3 ? 'var(--orange)' : 'var(--green)';
    } else {
        text = `${hours}h ${minutes}m left`;
        color = hours <= 6 ? 'var(--red)' : 'var(--orange)';
    }
    return <span style={{ fontSize: '0.72rem', color, fontWeight: 600 }}>{text}</span>;
}

export default function EmployeeDashboard() {
    const user = getUser();
    const [online, setOnline] = useState(false);
    const [tasks, setTasks] = useState([]);
    const [myLeaves, setMyLeaves] = useState([]);
    const [showLeaveForm, setShowLeaveForm] = useState(false);
    const [loadingLeave, setLoadingLeave] = useState(false);
    const [leaveForm, setLeaveForm] = useState({ start_date: '', end_date: '', reason: '' });
    const [perf, setPerf] = useState({
        score: 0,
        reliability: 0,
        avg_speed: 0,
        tasks_completed: 0,
        tasks_total: 0,
        active_tasks: 0,
        availability_status: 'active'
    });

    useEffect(() => {
        checkHealth().then(setOnline);
        const iv = setInterval(() => checkHealth().then(setOnline), 15000);
        return () => clearInterval(iv);
    }, []);

    const fetchTasks = async () => {
        try {
            const data = await api('/api/tasks/');
            setTasks(data);
        } catch (e) {
            console.error('Tasks fetch error:', e);
        }
    };

    const fetchMyLeaves = async () => {
        try {
            const data = await api('/api/leave/my');
            setMyLeaves(data);
        } catch (e) {
            console.error('Leave fetch error:', e);
        }
    };

    const fetchPerformance = async () => {
        try {
            const data = await api('/api/tasks/performance');
            setPerf(data);
        } catch (e) {
            console.error('Performance fetch error:', e);
        }
    };

    useEffect(() => {
        fetchTasks();
        fetchMyLeaves();
        fetchPerformance();
    }, []);

    const completeTask = async (taskId) => {
        try {
            await api(`/api/tasks/${taskId}/complete`, { method: 'PUT' });
            fetchTasks();
            fetchPerformance();
        } catch (e) {
            alert(e.message);
        }
    };

    const splitTask = async (taskId) => {
        const reason = window.prompt('Why do you need to split this task? (e.g., deadline pressure, complexity)');
        if (!reason) return;
        try {
            await api(`/api/tasks/${taskId}/split-request`, { 
                method: 'POST',
                body: JSON.stringify({ reason })
            });
            alert('Split request submitted to your manager.');
            fetchTasks();
        } catch (e) {
            alert(e.message);
        }
    };

    const approveSplit = async (parentTaskId) => {
        try {
            await api(`/api/tasks/${parentTaskId}/approve-split`, { method: 'PATCH' });
            alert('Split approved!');
            fetchTasks();
        } catch (e) {
            alert(e.message);
        }
    };

    const applyLeave = async (e) => {
        e.preventDefault();
        if (!window.confirm('Apply for leave? Your availability will be set to inactive immediately.')) return;
        setLoadingLeave(true);
        try {
            await api('/api/leave/apply', {
                method: 'POST',
                body: JSON.stringify(leaveForm),
            });
            alert('Leave applied successfully. Your status is now inactive.');
            setShowLeaveForm(false);
            setLeaveForm({ start_date: '', end_date: '', reason: '' });
            fetchMyLeaves();
        } catch (e) {
            alert(e.message);
        } finally {
            setLoadingLeave(false);
        }
    };

    const isNearDeadline = (t) => {
        const dl = t.sla_deadline || t.deadline;
        if (!dl) return false;
        return new Date(dl) - new Date() < 24 * 3600000;
    };

    return (
        <div className="app-container">
            <Navbar user={user} online={online} />

            <h1 className="hero-title">EMPLOYEE DASHBOARD</h1>
            <p className="hero-subtitle">My Tasks • Leave Management • Performance</p>

            {/* Performance snapshot */}
            <div className="card" style={{ maxWidth: 500, margin: '0 auto 1.5rem' }}>
                <div className="card-header">
                    <span className="card-title">📊 My Performance</span>
                </div>
                <div style={{ padding: '1rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2.4rem', fontWeight: 900, color: 'var(--cyan)' }}>
                        {perf.score}%
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4, marginBottom: 8 }}>
                        Reliability: {perf.reliability}% &nbsp;·&nbsp;
                        Avg Speed: {perf.avg_speed}%
                    </div>
                    <div className="flex gap-2" style={{ justifyContent: 'center', flexWrap: 'wrap' }}>
                        <span className="badge badge-in_progress">
                            {perf.active_tasks} active tasks
                        </span>
                        <span className={`badge ${perf.availability_status === 'leave' ? 'badge-critical' : 'badge-online'}`}>
                            {perf.availability_status.toUpperCase()}
                        </span>
                    </div>
                </div>
            </div>

            {/* Leave section */}
            <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                {/* Apply leave card */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">📅 Leave Management</span>
                    </div>
                    {!showLeaveForm ? (
                        <div style={{ padding: '1rem', textAlign: 'center' }}>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                                While on leave, AI will skip you when assigning new tasks.
                            </p>
                            <button className="btn btn-primary" onClick={() => setShowLeaveForm(true)}>
                                Apply for Leave
                            </button>
                        </div>
                    ) : (
                        <form onSubmit={applyLeave} style={{ padding: '1rem' }}>
                            <div style={{ marginBottom: '0.75rem' }}>
                                <label className="label">Start Date</label>
                                <input
                                    className="input"
                                    type="date"
                                    required
                                    value={leaveForm.start_date}
                                    onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })}
                                />
                            </div>
                            <div style={{ marginBottom: '0.75rem' }}>
                                <label className="label">End Date</label>
                                <input
                                    className="input"
                                    type="date"
                                    required
                                    value={leaveForm.end_date}
                                    onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })}
                                />
                            </div>
                            <div style={{ marginBottom: '0.75rem' }}>
                                <label className="label">Reason (optional)</label>
                                <textarea
                                    className="textarea"
                                    rows={2}
                                    placeholder="Medical, family, etc."
                                    value={leaveForm.reason}
                                    onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
                                />
                            </div>
                            <div className="flex gap-2" style={{ justifyContent: 'flex-end' }}>
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => setShowLeaveForm(false)}
                                >
                                    Cancel
                                </button>
                                <button type="submit" className="btn btn-primary" disabled={loadingLeave}>
                                    {loadingLeave ? <span className="spinner" /> : 'Submit'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>

                {/* Leave history card */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">📜 My Leave History</span>
                    </div>
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>From</th>
                                    <th>To</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {myLeaves.length === 0 && (
                                    <tr>
                                        <td colSpan={3} style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                            No leave requests yet.
                                        </td>
                                    </tr>
                                )}
                                {myLeaves.map((lr) => (
                                    <tr key={lr.id}>
                                        <td>{new Date(lr.start_date).toLocaleDateString()}</td>
                                        <td>{new Date(lr.end_date).toLocaleDateString()}</td>
                                        <td>
                                            <span className={`badge badge-${lr.status === 'approved' ? 'completed' :
                                                lr.status === 'rejected' ? 'critical' : 'in_progress'
                                                }`}>
                                                {lr.status.toUpperCase()}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Removed Split Request Acceptance for employees as it is now manager-approved */}

            {/* Tasks table */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">🧾 My Tasks ({tasks.length})</span>
                </div>
                <div className="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Task</th>
                                <th>Department</th>
                                <th>Priority</th>
                                <th>Status</th>
                                <th>Time Left</th>
                                <th>Risk</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tasks.length === 0 && (
                                <tr>
                                    <td colSpan={7} style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                        No tasks assigned yet.
                                    </td>
                                </tr>
                            )}
                            {tasks.map((t) => (
                                <tr key={t.id} style={{ borderLeft: t.parent_task_id ? '3px solid var(--cyan)' : 'none' }}>
                                    <td style={{ maxWidth: 220 }}>
                                        {t.parent_task_id && <span style={{ color: 'var(--cyan)', marginRight: 5 }}>↳</span>}
                                        {t.title}
                                    </td>
                                    <td>{t.department}</td>
                                    <td><span className={`badge badge-${t.priority}`}>{t.priority}</span></td>
                                    <td><span className={`badge badge-${t.status}`}>{t.status}</span></td>
                                    <td><TimeLeft slaDeadline={t.sla_deadline} deadline={t.deadline} /></td>
                                    <td><RiskBadge score={t.risk_score || 0} isRisk={t.is_delayed_risk} /></td>
                                    <td>
                                        <div className="flex gap-1" style={{ flexWrap: 'wrap' }}>
                                            {t.status !== 'completed' && (
                                                <button
                                                    className="btn btn-secondary"
                                                    style={{ padding: '4px 10px', fontSize: '0.68rem' }}
                                                    onClick={() => completeTask(t.id)}
                                                >
                                                    ✓ Complete
                                                </button>
                                            )}
                                            {t.status !== 'completed' && !t.split_requested && t.status !== 'split_approved' && (t.risk_score > 0.7 || isNearDeadline(t)) && (
                                                <button
                                                    className="btn btn-primary"
                                                    style={{ padding: '4px 10px', fontSize: '0.68rem', backgroundColor: 'var(--cyan)', color: 'black' }}
                                                    onClick={() => splitTask(t.id)}
                                                >
                                                    ✂ Split
                                                </button>
                                            )}
                                            {t.split_requested && (
                                                <span className="badge" style={{ backgroundColor: 'var(--yellow)', color: '#000', fontSize: '0.65rem' }}>
                                                    SPLIT PENDING
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}