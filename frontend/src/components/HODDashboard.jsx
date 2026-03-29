import { useState, useEffect } from 'react';
import { api, getUser, checkHealth } from '../api';

/* ─── Navbar ─────────────────────────────────────── */
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
                    <span className="badge badge-critical">HOD</span>
                </span>
                <button
                    className="btn btn-secondary"
                    onClick={handleLogout}
                    style={{ padding: '6px 14px', fontSize: '0.72rem' }}
                >
                    Logout
                </button>
            </div>
        </nav>
    );
}

/* ─── Risk Bar ────────────────────────────────────── */
function RiskBar({ score, isRisk }) {
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

/* ─── Stat Card ───────────────────────────────────── */
function StatCard({ icon, label, value, color }) {
    return (
        <div className="card" style={{ textAlign: 'center', padding: '1.2rem' }}>
            <div style={{ fontSize: '2rem', marginBottom: 4 }}>{icon}</div>
            <div style={{ fontSize: '2rem', fontWeight: 900, color: color || 'var(--cyan)' }}>{value}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
        </div>
    );
}

/* ─── Performance Leaderboard ─────────────────────── */
function PerformanceLeaderboard({ users }) {
    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">🏆 Team Performance Leaderboard</span>
                <span className="badge badge-online">{users.length} members</span>
            </div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Member</th>
                            <th>Department</th>
                            <th>Score</th>
                            <th>Reliability</th>
                            <th>Avg Speed</th>
                            <th>Workload</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.length === 0 && (
                            <tr>
                                <td colSpan={8} style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                    No team members found.
                                </td>
                            </tr>
                        )}
                        {users.map((u, i) => {
                            const score = u.performance_score ? (u.performance_score * 100).toFixed(0) : 0;
                            const color = score > 70 ? 'var(--green)' : score > 40 ? 'var(--yellow)' : 'var(--red)';
                            return (
                                <tr key={u.id}>
                                    <td style={{ color: 'var(--text-muted)', fontWeight: 700 }}>
                                        {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                                    </td>
                                    <td style={{ fontWeight: 600 }}>{u.full_name || u.name}</td>
                                    <td>{u.department}</td>
                                    <td style={{ color, fontWeight: 700 }}>{score}%</td>
                                    <td>{u.reliability ? `${(u.reliability * 100).toFixed(0)}%` : '—'}</td>
                                    <td>{u.avg_completion_time ? `${u.avg_completion_time}h` : '—'}</td>
                                    <td>
                                        <span className={`badge badge-${u.current_workload > 3 ? 'critical' : 'in_progress'}`}>
                                            {u.current_workload ?? 0} tasks
                                        </span>
                                    </td>
                                    <td>
                                        <span className={`badge badge-${u.availability_status === 'leave' ? 'critical' : 'online'}`}>
                                            {u.availability_status ? u.availability_status.toUpperCase() : 'ACTIVE'}
                                        </span>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/* ─── Tasks Overview ──────────────────────────────── */
function TasksOverview({ tasks }) {
    const [filter, setFilter] = useState('all');

    const filtered = filter === 'all' ? tasks :
        filter === 'high_risk' ? tasks.filter(t => t.risk_score > 0.7 || t.is_delayed_risk) :
            tasks.filter(t => t.status === filter);

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">📊 All Tasks ({tasks.length})</span>
                <div className="flex gap-1" style={{ flexWrap: 'wrap' }}>
                    {['all', 'pending', 'completed', 'high_risk'].map(f => (
                        <button
                            key={f}
                            className={`btn ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
                            style={{ padding: '3px 10px', fontSize: '0.68rem' }}
                            onClick={() => setFilter(f)}
                        >
                            {f.replace('_', ' ').toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Task</th>
                            <th>Assigned To</th>
                            <th>Department</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Risk</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.length === 0 && (
                            <tr>
                                <td colSpan={6} style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                    No tasks found.
                                </td>
                            </tr>
                        )}
                        {filtered.map(t => (
                            <tr key={t.id} style={{ borderLeft: t.is_delayed_risk ? '3px solid var(--red)' : t.parent_task_id ? '3px solid var(--cyan)' : 'none' }}>
                                <td style={{ maxWidth: 230 }}>
                                    {t.parent_task_id && <span style={{ color: 'var(--cyan)', marginRight: 5 }}>↳</span>}
                                    {t.title}
                                </td>
                                <td>{t.owner_name || '—'}</td>
                                <td>{t.department}</td>
                                <td><span className={`badge badge-${t.priority}`}>{t.priority}</span></td>
                                <td><span className={`badge badge-${t.status}`}>{t.status}</span></td>
                                <td><RiskBar score={t.risk_score || 0} isRisk={t.is_delayed_risk} /></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/* ─── Leave Approvals ─────────────────────────────── */
function LeaveApprovals({ onRefresh }) {
    const [leaves, setLeaves] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchLeaves = async () => {
        try {
            const data = await api('/api/leave/all');
            setLeaves(data);
        } catch (e) {
            console.error('Leave fetch error:', e);
        }
    };

    useEffect(() => { fetchLeaves(); }, []);

    const handleAction = async (leaveId, action) => {
        setLoading(true);
        try {
            await api(`/api/leave/${leaveId}/${action}`, { method: 'PUT' });
            fetchLeaves();
            if (onRefresh) onRefresh();
        } catch (e) {
            alert(e.message);
        } finally {
            setLoading(false);
        }
    };

    const pending = leaves.filter(l => l.status === 'pending');

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">📋 Leave Approvals</span>
                {pending.length > 0 && (
                    <span className="badge badge-critical">{pending.length} pending</span>
                )}
            </div>
            <div className="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>Employee</th>
                            <th>Department</th>
                            <th>From</th>
                            <th>To</th>
                            <th>Reason</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {leaves.length === 0 && (
                            <tr>
                                <td colSpan={7} style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                    No leave requests found.
                                </td>
                            </tr>
                        )}
                        {leaves.map(l => {
                            const emp = l.users || {};
                            return (
                                <tr key={l.id}>
                                    <td style={{ fontWeight: 600 }}>{emp.full_name || emp.name || '—'}</td>
                                    <td>{emp.department || '—'}</td>
                                    <td>{new Date(l.start_date).toLocaleDateString()}</td>
                                    <td>{new Date(l.end_date).toLocaleDateString()}</td>
                                    <td style={{ maxWidth: 150, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                        {l.reason || '—'}
                                    </td>
                                    <td>
                                        <span className={`badge badge-${l.status === 'approved' ? 'completed' :
                                            l.status === 'rejected' ? 'critical' : 'in_progress'
                                            }`}>
                                            {l.status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td>
                                        {l.status === 'pending' && (
                                            <div className="flex gap-1">
                                                <button
                                                    className="btn btn-secondary"
                                                    style={{ padding: '4px 10px', fontSize: '0.68rem', color: 'var(--green)', borderColor: 'var(--green)' }}
                                                    disabled={loading}
                                                    onClick={() => handleAction(l.id, 'approve')}
                                                >
                                                    ✓ Approve
                                                </button>
                                                <button
                                                    className="btn btn-secondary"
                                                    style={{ padding: '4px 10px', fontSize: '0.68rem', color: 'var(--red)', borderColor: 'var(--red)' }}
                                                    disabled={loading}
                                                    onClick={() => handleAction(l.id, 'reject')}
                                                >
                                                    ✕ Reject
                                                </button>
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

/* ─── Risk Summary ────────────────────────────────── */
function RiskSummary({ tasks }) {
    const high = tasks.filter(t => t.risk_score > 0.7 || t.is_delayed_risk).length;
    const med = tasks.filter(t => t.risk_score > 0.4 && t.risk_score <= 0.7 && !t.is_delayed_risk).length;
    const low = tasks.filter(t => t.risk_score <= 0.4 && !t.is_delayed_risk).length;
    const total = tasks.length || 1;
    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">🚨 Risk Overview</span>
            </div>
            <div className="flex gap-2" style={{ justifyContent: 'space-around', textAlign: 'center' }}>
                {[
                    { label: 'High Risk', count: high, color: 'var(--red)' },
                    { label: 'Medium', count: med, color: 'var(--yellow)' },
                    { label: 'Low Risk', count: low, color: 'var(--green)' },
                ].map(({ label, count, color }) => (
                    <div key={label}>
                        <div style={{ fontSize: '2rem', fontWeight: 900, color }}>{count}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
                        <div className="risk-bar-bg" style={{ width: 60, margin: '6px auto 0' }}>
                            <div className="risk-bar-fill" style={{ width: `${(count / total) * 100}%`, background: color }} />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════
   MAIN HOD DASHBOARD
   ═══════════════════════════════════════════════════ */
export default function HODDashboard() {
    const user = getUser();
    const [online, setOnline] = useState(false);
    const [tasks, setTasks] = useState([]);
    const [users, setUsers] = useState([]);
    const [splitReqs, setSplitReqs] = useState([]);

    const fetchSplitReqs = async () => {
        try {
            const data = await api('/api/tasks/split-requests');
            setSplitReqs(data || []);
        } catch { /* swallow */ }
    };

    useEffect(() => {
        checkHealth().then(setOnline);
        const iv = setInterval(() => checkHealth().then(setOnline), 15000);
        return () => clearInterval(iv);
    }, []);

    const fetchTasks = async () => {
        try {
            const data = await api('/api/tasks/');
            setTasks(data);
        } catch (e) { console.error(e); }
    };

    const fetchUsers = async () => {
        try {
            const data = await api('/api/auth/users');
            setUsers(data);
        } catch (e) { console.error(e); }
    };

    useEffect(() => {
        fetchTasks();
        fetchUsers();
        fetchSplitReqs();
    }, []);

    const completed = tasks.filter(t => t.status === 'completed').length;
    const pending = tasks.filter(t => t.status === 'pending').length;
    const highRisk = tasks.filter(t => t.risk_score > 0.7 || t.is_delayed_risk).length;
    const onLeave = users.filter(u => u.availability_status === 'leave').length;

    return (
        <div className="app-container">
            <Navbar user={user} online={online} />

            <h1 className="hero-title">HOD COMMAND CENTER</h1>
            <p className="hero-subtitle">Full team visibility • Leave approvals • Risk overview</p>

            {/* Stats row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <StatCard icon="👥" label="Team Members" value={users.length} color="var(--cyan)" />
                <StatCard icon="📋" label="Total Tasks" value={tasks.length} color="var(--cyan)" />
                <StatCard icon="✅" label="Completed" value={completed} color="var(--green)" />
                <StatCard icon="⏳" label="Pending" value={pending} color="var(--yellow)" />
                <StatCard icon="🚨" label="High Risk" value={highRisk} color="var(--red)" />
                <StatCard icon="🏖️" label="On Leave" value={onLeave} color="var(--orange)" />
            </div>

            {/* Risk + Leaderboard */}
            <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                <RiskSummary tasks={tasks} />
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">🏢 Department Breakdown</span>
                    </div>
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Department</th>
                                    <th>Members</th>
                                    <th>Active</th>
                                    <th>On Leave</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Array.from(new Set(users.map(u => u.department))).map(dept => {
                                    const deptUsers = users.filter(u => u.department === dept);
                                    const active = deptUsers.filter(u => u.availability_status !== 'leave').length;
                                    const leave = deptUsers.filter(u => u.availability_status === 'leave').length;
                                    return (
                                        <tr key={dept}>
                                            <td style={{ fontWeight: 600 }}>{dept}</td>
                                            <td>{deptUsers.length}</td>
                                            <td><span className="badge badge-online">{active}</span></td>
                                            <td><span className={`badge ${leave > 0 ? 'badge-critical' : 'badge-completed'}`}>{leave}</span></td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {/* Leaderboard */}
            <div style={{ marginBottom: '1.5rem' }}>
                <PerformanceLeaderboard users={users} />
            </div>

            {/* Leave approvals */}
            <div style={{ marginBottom: '1.5rem' }}>
                <LeaveApprovals onRefresh={() => { fetchTasks(); fetchUsers(); }} />
            </div>

            {/* Split requests */}
            {splitReqs.length > 0 && (
                <div className="card" style={{ marginBottom: '1.5rem', borderColor: 'var(--yellow)' }}>
                    <div className="card-header">
                        <span className="card-title">✂️ Task Split Requests</span>
                        <span className="badge badge-escalated">{splitReqs.length} Pending</span>
                    </div>
                    <div className="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>Task</th>
                                    <th>Employee</th>
                                    <th>Reason</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {splitReqs.map(req => (
                                    <tr key={req.id}>
                                        <td>{req.title}</td>
                                        <td>{req.owner_name}</td>
                                        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{req.split_reason}</td>
                                        <td>
                                            <button 
                                                className="btn btn-primary" 
                                                style={{ padding: '4px 10px', fontSize: '0.7rem' }}
                                                onClick={async () => {
                                                    if (!window.confirm('Approve this split? AI will create subtasks.')) return;
                                                    try {
                                                        await api(`/api/tasks/${req.id}/approve-split`, {
                                                            method: 'POST',
                                                            body: JSON.stringify({ subtasks: [
                                                                { title: `Part 1: ${req.title}`, deadline: req.sla_deadline },
                                                                { title: `Part 2: ${req.title}`, deadline: req.sla_deadline }
                                                            ]})
                                                        });
                                                        alert('Split approved.');
                                                        fetchTasks();
                                                        fetchSplitReqs();
                                                    } catch (e) { alert(e.message); }
                                                }}
                                            >
                                                ✓ Approve
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* All tasks */}
            <TasksOverview tasks={tasks} />
        </div>
    );
}