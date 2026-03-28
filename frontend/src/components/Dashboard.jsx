import { useState, useEffect, useRef } from 'react';
import { api, getUser, logout, checkHealth } from '../api';



/* ─── Navbar ──────────────────────────────────────── */
function Navbar({ user, online }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">⚡ FLOWGUARD AI</span>
        <span className={`badge ${online ? 'badge-online' : 'badge-offline'}`}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'currentColor',
              display: 'inline-block',
            }}
          />
          {online ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>
      <div className="navbar-user">
        <span style={{ marginRight: '1rem' }}>
          {user.full_name}{' '}
          <span
            className={`badge badge-${user.role === 'head'
              ? 'critical'
              : user.role === 'manager'
                ? 'completed'
                : 'in_progress'
              }`}
          >
            {user.role.toUpperCase()}
          </span>
        </span>
        <button
          className="btn btn-secondary"
          onClick={logout}
          style={{ padding: '6px 14px', fontSize: '0.72rem' }}
        >
          Logout
        </button>
      </div>
    </nav>
  );
}



/* ─── Upload Panel ────────────────────────────────── */
function UploadPanel({ onResult }) {
  const [tab, setTab] = useState('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef();



  const processText = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await api('/api/workflows/process', {
        method: 'POST',
        body: JSON.stringify({ raw_input: text, title: 'Meeting Workflow' }),
      });
      onResult(res);
      setText('');
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };



  const processFile = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('title', `Media: ${file.name}`);
      const res = await api('/api/workflows/process-media', {
        method: 'POST',
        body: fd,
      });
      onResult(res);
      setFile(null);
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="card" style={{ maxWidth: 800, margin: '0 auto 1.5rem' }}>
      <div className="card-header">
        <span className="card-title">📋 Process Meeting</span>
      </div>



      <div className="tabs">
        <button
          className={`tab ${tab === 'text' ? 'active' : ''}`}
          onClick={() => setTab('text')}
        >
          📝 Text Input
        </button>
        <button
          className={`tab ${tab === 'media' ? 'active' : ''}`}
          onClick={() => setTab('media')}
        >
          🎥 Media Upload
        </button>
      </div>



      {tab === 'text' ? (
        <>
          <textarea
            className="textarea"
            placeholder={
              'Paste meeting transcript here...\n\nExample:\nDeploy new marketing campaign\nPrepare budget allocation\nFinalize vendor list'
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
            style={{ height: 120 }}
            id="transcript-input"
          />
          <div className="text-center mt-1">
            <button
              className="btn btn-primary"
              onClick={processText}
              disabled={loading || !text.trim()}
              id="process-btn"
            >
              {loading ? (
                <>
                  <span className="spinner" /> Processing...
                </>
              ) : (
                '⚡ Process Meeting'
              )}
            </button>
          </div>
        </>
      ) : (
        <>
          <div
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              setFile(e.dataTransfer.files[0]);
            }}
            onClick={() => fileRef.current.click()}
          >
            <div className="upload-icon">🎬</div>
            <div className="upload-text">
              Drag & drop video/audio file or click to browse
            </div>
            <div
              style={{
                fontSize: '0.7rem',
                color: 'var(--text-muted)',
                marginTop: 4,
              }}
            >
              Supports .mp4, .wav, .mp3, .webm
            </div>
            {file && <div className="upload-file-name">📎 {file.name}</div>}
            <input
              ref={fileRef}
              type="file"
              accept="video/*,audio/*"
              style={{ display: 'none' }}
              onChange={(e) => setFile(e.target.files[0])}
            />
          </div>
          <div className="text-center mt-1">
            <button
              className="btn btn-primary"
              onClick={processFile}
              disabled={loading || !file}
              id="upload-btn"
            >
              {loading ? (
                <>
                  <span className="spinner" /> Transcribing...
                </>
              ) : (
                '🚀 Upload & Process'
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
}



/* ─── Risk Bar ────────────────────────────────────── */
function RiskBar({ score, isRisk }) {
  const color = isRisk
    ? 'var(--red)'
    : score > 0.75
      ? 'var(--red)'
      : score > 0.5
        ? 'var(--orange)'
        : score > 0.25
          ? 'var(--yellow)'
          : 'var(--green)';
  return (
    <div className="flex gap-1" style={{ alignItems: 'center' }}>
      <div className="risk-bar-bg">
        <div
          className="risk-bar-fill"
          style={{ width: `${score * 100}%`, background: color }}
        />
      </div>
      <span
        style={{
          fontSize: '0.72rem',
          color,
          fontWeight: 600,
        }}
      >
        {(score * 100).toFixed(0)}%{isRisk ? ' ⚠️' : ''}
      </span>
    </div>
  );
}



/* ─── ✅ Phase 1: Deadline Countdown ──────────────── */
function DeadlineCountdown({ deadline }) {
  const [timeLeft, setTimeLeft] = useState('');
  const [color, setColor] = useState('var(--text-muted)');

  useEffect(() => {
    const calc = () => {
      if (!deadline) {
        setTimeLeft('No deadline');
        setColor('var(--text-muted)');
        return;
      }
      const diff = new Date(deadline) - new Date();
      if (diff <= 0) {
        setTimeLeft('⛔ Overdue');
        setColor('var(--red)');
        return;
      }
      const days = Math.floor(diff / 86400000);
      const hours = Math.floor((diff % 86400000) / 3600000);
      const minutes = Math.floor((diff % 3600000) / 60000);

      if (days >= 1) {
        setTimeLeft(`${days}d ${hours}h left`);
        setColor(
          days <= 1 ? 'var(--red)'
            : days <= 3 ? 'var(--orange)'
              : 'var(--green)'
        );
      } else {
        setTimeLeft(`${hours}h ${minutes}m left`);
        setColor(hours <= 6 ? 'var(--red)' : 'var(--orange)');
      }
    };

    calc();
    const iv = setInterval(calc, 60000);
    return () => clearInterval(iv);
  }, [deadline]);

  return (
    <span style={{ fontSize: '0.72rem', color, fontWeight: 600 }}>
      {timeLeft}
    </span>
  );
}



/* ─── Tasks Table ─────────────────────────────────── */
function TasksTable({ tasks, user, onSimulate, onUpdate, onAutoAssign }) {
  const canEdit = ['manager'].includes(user.role);



  const handleStatusChange = async (taskId, newStatus) => {
    try {
      await api(`/api/tasks/${taskId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
      });
      onUpdate();
    } catch (e) {
      alert(e.message);
    }
  };



  // ✅ Phase 3 Item 11: check if deadline is within 2 days
  const isDeadlineClose = (deadline) => {
    try {
      const daysLeft = (new Date(deadline) - new Date()) / 86400000;
      return daysLeft <= 2 && daysLeft > 0;
    } catch {
      return false;
    }
  };



  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">📊 Tasks ({tasks.length})</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Task Title</th>
              <th>Owner</th>
              <th>Dept</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Risk</th>
              {/* ✅ Phase 1: Deadline column */}
              <th>Deadline</th>
              {canEdit && <th>Action</th>}
              {user.role === 'employee' && <th>Action</th>}
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr
                key={t.id}
                style={{
                  borderLeft: t.parent_task_id
                    ? '3px solid var(--cyan)'
                    : 'none',
                }}
              >
                <td style={{ maxWidth: 250 }}>
                  {t.parent_task_id && (
                    <span
                      style={{ color: 'var(--cyan)', marginRight: 5 }}
                    >
                      ↳
                    </span>
                  )}
                  {t.title}
                </td>
                <td>{t.owner_name}</td>
                <td>{t.department}</td>
                <td>
                  <span className={`badge badge-${t.priority}`}>
                    {t.priority}
                  </span>
                </td>
                <td>
                  <span className={`badge badge-${t.status}`}>
                    {t.status}
                  </span>
                </td>
                <td>
                  <RiskBar
                    score={t.risk_score}
                    isRisk={t.is_delayed_risk}
                  />
                </td>
                {/* ✅ Phase 1: Live countdown cell */}
                <td>
                  <DeadlineCountdown
                    deadline={t.sla_deadline || t.deadline}
                  />
                </td>
                {canEdit && (
                  <td>
                    <div
                      className="flex gap-1"
                      style={{ flexWrap: 'wrap' }}
                    >
                      {t.status !== 'completed' && (
                        <button
                          className="btn btn-secondary"
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.68rem',
                          }}
                          onClick={() =>
                            handleStatusChange(t.id, 'completed')
                          }
                        >
                          ✓ Done
                        </button>
                      )}
                      {t.owner_name === 'Unassigned' && (
                        <button
                          className="btn btn-primary"
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.68rem',
                            backgroundColor: 'var(--cyan)',
                            color: 'black',
                          }}
                          onClick={() => onAutoAssign(t)}
                        >
                          🤖 Auto
                        </button>
                      )}
                      <button
                        className="btn btn-secondary"
                        style={{
                          padding: '4px 10px',
                          fontSize: '0.68rem',
                        }}
                        onClick={() => onSimulate(t.id)}
                      >
                        🔮 What If
                      </button>
                    </div>
                  </td>
                )}
                {user.role === 'employee' && (
                  <td>
                    <div
                      className="flex gap-1"
                      style={{ flexWrap: 'wrap' }}
                    >
                      {t.status !== 'completed' && (
                        <button
                          className="btn btn-secondary"
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.68rem',
                          }}
                          onClick={() =>
                            handleStatusChange(t.id, 'completed')
                          }
                        >
                          ✓ Mark Complete
                        </button>
                      )}
                      {/* ✅ Phase 3 Item 11: Split Task — only when ≤ 2 days left */}
                      {t.status !== 'completed' &&
                        isDeadlineClose(t.sla_deadline || t.deadline) && (
                          <button
                            className="btn btn-primary"
                            style={{
                              padding: '4px 10px',
                              fontSize: '0.68rem',
                              background: 'var(--orange)',
                              color: 'black',
                            }}
                            onClick={async () => {
                              try {
                                const res = await api(
                                  `/api/tasks/${t.id}/split`,
                                  { method: 'POST' }
                                );
                                alert(`✂️ Task split! Helper assigned: ${res.helper}`);
                                onUpdate();
                              } catch (e) {
                                alert(e.message);
                              }
                            }}
                          >
                            ✂️ Split Task
                          </button>
                        )}
                    </div>
                  </td>
                )}
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td
                  colSpan={
                    canEdit || user.role === 'employee' ? 8 : 7
                  }
                  className="text-center"
                  style={{
                    padding: '2rem',
                    color: 'var(--text-muted)',
                  }}
                >
                  No tasks yet. Process a meeting to generate tasks.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}



/* ─── Audit Logs ──────────────────────────────────── */
function AuditLogs({ logs }) {
  if (!logs || logs.length === 0) return null;
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          🧠 Explainable AI Audit Trail
        </span>
        <span className="badge badge-online">
          {logs.length} decisions
        </span>
      </div>
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        {logs.map((log, i) => (
          <div
            className="log-item"
            key={log.id || i}
            style={{ animationDelay: `${i * 0.08}s` }}
          >
            <div className="log-dot" />
            <div className="log-content">
              <div className="log-agent">{log.agent || log.agent_name}</div>
              <div className="log-action">{log.decision || log.action}</div>
              <div className="log-reason">{log.reason || ''}</div>
              <div className="log-meta">
                <span className="log-confidence">
                  Confidence:{' '}
                  {((log.confidence || 0) * 100).toFixed(0)}%
                </span>
                {/* ✅ FIX 2: safe timestamp parse — no "Invalid Date" */}
                <span className="log-time">
                  {log.created_at
                    ? (() => {
                      try {
                        return new Date(log.created_at).toLocaleTimeString();
                      } catch {
                        return 'N/A';
                      }
                    })()
                    : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}



/* ─── Leave Approval Panel (Manager/HOD only) ────── */
function LeaveApprovalPanel() {
  const [leaves, setLeaves] = useState([]);
  const [loading, setLoading] = useState(false);



  const fetchLeaves = async () => {
    try {
      const data = await api('/api/leave/pending');
      setLeaves(data);
    } catch (e) {
      console.error('Leave fetch failed:', e.message);
    }
  };



  useEffect(() => { fetchLeaves(); }, []);



  const handleAction = async (leaveId, action) => {
    setLoading(true);
    try {
      await api(`/api/leave/${leaveId}/${action}`, { method: 'PUT' });
      // ✅ Optimistically remove from UI immediately — don't wait for refetch
      setLeaves((prev) => prev.filter((l) => l.id !== leaveId));
    } catch (e) {
      // ✅ Even on error, remove from UI if it's a 404 (already processed)
      if (e.message?.includes('404') || e.message?.includes('not found')) {
        setLeaves((prev) => prev.filter((l) => l.id !== leaveId));
      } else {
        alert(e.message);
      }
    } finally {
      setLoading(false);
    }
  };



  if (leaves.length === 0) return (
    <div className="card" style={{ borderColor: 'var(--cyan)' }}>
      <div className="card-header">
        <span className="card-title">📋 Leave Requests</span>
        <span className="badge badge-online">0 Pending</span>
      </div>
      <p style={{ color: 'var(--text-muted)', padding: '1rem', textAlign: 'center' }}>
        No pending leave requests.
      </p>
    </div>
  );



  return (
    <div className="card" style={{ borderColor: 'var(--orange)' }}>
      <div className="card-header">
        <span className="card-title" style={{ color: 'var(--orange)' }}>
          📋 Pending Leave Requests
        </span>
        <span className="badge badge-escalated">{leaves.length} Pending</span>
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
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {leaves.map((l) => (
              <tr key={l.id}>
                <td>{l.users?.full_name || 'Unknown'}</td>
                <td>{l.users?.department || '—'}</td>
                <td>{l.start_date}</td>
                <td>{l.end_date}</td>
                <td style={{ color: 'var(--text-muted)' }}>{l.reason || '—'}</td>
                <td>
                  <div className="flex gap-1">
                    <button
                      className="btn btn-primary"
                      style={{ padding: '4px 12px', fontSize: '0.68rem', background: 'var(--green)', color: 'black' }}
                      onClick={() => handleAction(l.id, 'approve')}
                      disabled={loading}
                    >
                      ✓ Approve
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '4px 12px', fontSize: '0.68rem', color: 'var(--red)' }}
                      onClick={() => handleAction(l.id, 'reject')}
                      disabled={loading}
                    >
                      ✕ Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}



/* ─── Employee Leave Panel ────────────────────────── */
function EmployeeLeavePanel() {
  const [leaves, setLeaves] = useState([]);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);



  const fetchMyLeaves = async () => {
    try { setLeaves(await api('/api/leave/my')); }
    catch (e) { console.error('My leaves fetch failed:', e.message); }
  };



  useEffect(() => { fetchMyLeaves(); }, []);



  const applyLeave = async () => {
    if (!startDate || !endDate) return alert('Please select start and end dates');
    if (endDate < startDate) return alert('End date must be after start date');
    setSubmitting(true);
    try {
      await api('/api/leave/apply', {
        method: 'POST',
        body: JSON.stringify({ start_date: startDate, end_date: endDate, reason }),
      });
      setStartDate('');
      setEndDate('');
      setReason('');
      fetchMyLeaves();
    } catch (e) {
      alert(e.message);
    } finally {
      setSubmitting(false);
    }
  };



  const statusColor = {
    pending: 'var(--yellow)',
    approved: 'var(--green)',
    rejected: 'var(--red)',
    completed: 'var(--cyan)',
  };
  const statusLabel = {
    pending: '🕐 Pending',
    approved: '✅ Approved',
    rejected: '❌ Rejected',
    completed: '✔ Completed',
  };



  return (
    <div className="card" style={{ maxWidth: 800, margin: '0 auto 1.5rem' }}>
      <div className="card-header">
        <span className="card-title">🏖️ My Leave Requests</span>
        <span className="badge badge-online">{leaves.length} total</span>
      </div>



      {/* Apply form */}
      <div style={{ padding: '0 0 1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <label className="label">Start Date</label>
          <input
            className="input"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            min={new Date().toISOString().split('T')[0]}
          />
        </div>
        <div>
          <label className="label">End Date</label>
          <input
            className="input"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            min={startDate || new Date().toISOString().split('T')[0]}
          />
        </div>
        <div style={{ flex: 1, minWidth: 160 }}>
          <label className="label">Reason (optional)</label>
          <input
            className="input"
            type="text"
            placeholder="e.g. Personal"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <button
          className="btn btn-primary"
          onClick={applyLeave}
          disabled={submitting || !startDate || !endDate}
          style={{ height: 38 }}
        >
          {submitting ? <><span className="spinner" /> Submitting...</> : '📤 Apply'}
        </button>
      </div>



      {/* Leave history */}
      {leaves.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1rem' }}>
          No leave requests yet.
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>From</th>
                <th>To</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {leaves.map((l) => (
                <tr key={l.id}>
                  <td>{l.start_date}</td>
                  <td>{l.end_date}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{l.reason || '—'}</td>
                  <td style={{ color: statusColor[l.status], fontWeight: 700, fontSize: '0.75rem' }}>
                    {statusLabel[l.status] || l.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}



/* ─── Simulation Panel ────────────────────────────── */
function SimulationPanel({ taskId, onClose }) {
  const [days, setDays] = useState(2);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);



  const runSim = async () => {
    setLoading(true);
    try {
      const res = await api('/api/workflows/simulate', {
        method: 'POST',
        body: JSON.stringify({ task_id: taskId, delay_days: days }),
      });
      setResult(res);
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };



  return (
    <div
      className="card"
      style={{
        borderColor: 'var(--purple)',
        boxShadow: '0 0 30px #d500f922',
      }}
    >
      <div className="card-header">
        <span
          className="card-title"
          style={{ color: 'var(--purple)' }}
        >
          🔮 What-If Simulation
        </span>
        <button
          className="btn btn-secondary"
          onClick={onClose}
          style={{ padding: '4px 12px', fontSize: '0.7rem' }}
        >
          ✕ Close
        </button>
      </div>



      <div
        className="flex gap-2"
        style={{ alignItems: 'flex-end', marginBottom: '1rem' }}
      >
        <div style={{ flex: 1 }}>
          <label className="label">Delay (days)</label>
          <input
            className="input"
            type="number"
            min={1}
            max={30}
            value={days}
            onChange={(e) =>
              setDays(Number(e.target.value))
            }
          />
        </div>
        <button
          className="btn btn-primary"
          onClick={runSim}
          disabled={loading}
        >
          {loading ? <span className="spinner" /> : '⚡ Simulate'}
        </button>
      </div>



      {result && (
        <div className="sim-result">
          <div className="sim-row">
            <span className="sim-label">Task</span>
            <span className="sim-value">{result.task_title}</span>
          </div>
          <div className="sim-row">
            <span className="sim-label">Original Risk</span>
            <span className="sim-value">
              {(result.original_risk * 100).toFixed(0)}%
            </span>
          </div>
          <div className="sim-row">
            <span className="sim-label">Simulated Risk</span>
            <span
              className="sim-value"
              style={{
                color: result.sla_breach
                  ? 'var(--red)'
                  : 'var(--yellow)',
              }}
            >
              {(result.simulated_risk * 100).toFixed(0)}%
            </span>
          </div>
          <div className="sim-row">
            <span className="sim-label">SLA Breach</span>
            <span
              className={
                result.sla_breach ? 'sim-breach' : 'sim-safe'
              }
            >
              {result.sla_breach
                ? '⚠️ YES — BREACH'
                : '✅ No breach'}
            </span>
          </div>
          <div className="sim-row">
            <span className="sim-label">Impact</span>
            <span className="sim-value">
              {result.impact_summary}
            </span>
          </div>
          <div className="sim-row">
            <span className="sim-label">AI Suggestion</span>
            <span
              className="sim-value"
              style={{ color: 'var(--cyan)' }}
            >
              {result.suggestion}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}



/* ─── Risk Dashboard ──────────────────────────────── */
function RiskDashboard({ tasks }) {
  // ✅ FIX 1: >= 0.6 matches backend compute_risk (critical = 0.6)
  const high = tasks.filter(
    (t) => t.risk_score >= 0.6 || t.is_delayed_risk,
  ).length;
  const med = tasks.filter(
    (t) =>
      t.risk_score >= 0.4 &&
      t.risk_score < 0.6 &&
      !t.is_delayed_risk,
  ).length;
  const low = tasks.filter(
    (t) => t.risk_score < 0.4 && !t.is_delayed_risk,
  ).length;
  const total = tasks.length || 1;



  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">🚨 Risk Prediction</span>
      </div>
      <div
        className="flex gap-2"
        style={{
          justifyContent: 'space-around',
          textAlign: 'center',
        }}
      >
        <div>
          <div
            style={{
              fontSize: '2rem',
              fontWeight: 900,
              color: 'var(--red)',
            }}
          >
            {high}
          </div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: 1,
            }}
          >
            High Risk
          </div>
          <div
            className="risk-bar-bg"
            style={{ width: 60, margin: '6px auto 0' }}
          >
            <div
              className="risk-bar-fill"
              style={{
                width: `${(high / total) * 100}%`,
                background: 'var(--red)',
              }}
            />
          </div>
        </div>
        <div>
          <div
            style={{
              fontSize: '2rem',
              fontWeight: 900,
              color: 'var(--yellow)',
            }}
          >
            {med}
          </div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: 1,
            }}
          >
            Medium
          </div>
          <div
            className="risk-bar-bg"
            style={{ width: 60, margin: '6px auto 0' }}
          >
            <div
              className="risk-bar-fill"
              style={{
                width: `${(med / total) * 100}%`,
                background: 'var(--yellow)',
              }}
            />
          </div>
        </div>
        <div>
          <div
            style={{
              fontSize: '2rem',
              fontWeight: 900,
              color: 'var(--green)',
            }}
          >
            {low}
          </div>
          <div
            style={{
              fontSize: '0.7rem',
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: 1,
            }}
          >
            Low Risk
          </div>
          <div
            className="risk-bar-bg"
            style={{ width: 60, margin: '6px auto 0' }}
          >
            <div
              className="risk-bar-fill"
              style={{
                width: `${(low / total) * 100}%`,
                background: 'var(--green)',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}



/* ─── Leaderboard ─────────────────────────────────── */
function PerformanceLeaderboard({ users }) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          🏆 Team Performance Leaderboard
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Member</th>
              <th>Dept</th>
              <th>Score</th>
              <th>Reliability</th>
              <th>Speed</th>
              <th>Workload</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const score = (u.performance_score * 100).toFixed(0);
              const color =
                score > 70
                  ? 'var(--green)'
                  : score > 40
                    ? 'var(--yellow)'
                    : 'var(--red)';
              return (
                <tr key={u.id}>
                  <td>{u.full_name || u.name}</td>
                  <td>{u.department}</td>
                  <td style={{ color, fontWeight: 700 }}>
                    {score}%
                  </td>
                  <td>
                    {(u.reliability * 100).toFixed(0)}%
                  </td>
                  <td>
                    {u.avg_completion_time
                      ? `${u.avg_completion_time}h`
                      : 'N/A'}
                  </td>
                  <td>
                    <span
                      className={`badge badge-${u.current_workload > 3
                        ? 'critical'
                        : 'in_progress'
                        }`}
                    >
                      {u.current_workload} tasks
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



/* ─── Ambiguity Panel ────────────────────────────── */
function NeedsClarification({ tasks }) {
  const unassigned = tasks.filter(
    (t) => t.owner_name === 'Unassigned',
  );
  if (unassigned.length === 0) return null;
  return (
    <div
      className="card"
      style={{
        borderColor: 'var(--orange)',
        background: '#ff980008',
      }}
    >
      <div className="card-header">
        <span
          className="card-title"
          style={{ color: 'var(--orange)' }}
        >
          🤔 Needs Clarification ({unassigned.length})
        </span>
        <span className="badge badge-escalated">
          Action Required
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Flagged Task</th>
              <th>Department Match</th>
              <th>Issue</th>
            </tr>
          </thead>
          <tbody>
            {unassigned.map((t) => (
              <tr key={t.id}>
                <td>{t.title}</td>
                <td>{t.department}</td>
                <td style={{ color: 'var(--red)' }}>
                  No available employee found in department
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}



/* ─── ✅ Phase 3 Item 13: HOD Company Overview ────── */
function HODOverview({ tasks, users }) {
  const depts = [...new Set(users.map((u) => u.department).filter(Boolean))];
  const totalTasks = tasks.length;
  const doneTasks = tasks.filter((t) => t.status === 'completed').length;
  const pendingTsk = tasks.filter((t) => t.status === 'pending').length;
  const overdue = tasks.filter((t) => {
    try { return new Date(t.sla_deadline) < new Date() && t.status !== 'completed'; }
    catch { return false; }
  }).length;
  const onLeave = users.filter((u) => u.availability_status === 'on_leave').length;
  const active = users.filter((u) => u.availability_status === 'active').length;

  return (
    <div className="card" style={{ borderColor: 'var(--cyan)', marginBottom: '1.5rem' }}>
      <div className="card-header">
        <span className="card-title" style={{ color: 'var(--cyan)' }}>
          🏢 Company Overview
        </span>
        <span className="badge badge-online">{users.length} employees</span>
      </div>

      {/* KPI row */}
      <div
        className="flex gap-2"
        style={{
          justifyContent: 'space-around',
          textAlign: 'center',
          marginBottom: '1.5rem',
        }}
      >
        {[
          { label: 'Total Tasks', value: totalTasks, color: 'var(--cyan)' },
          { label: 'Completed', value: doneTasks, color: 'var(--green)' },
          { label: 'Pending', value: pendingTsk, color: 'var(--yellow)' },
          { label: 'Overdue', value: overdue, color: 'var(--red)' },
          { label: 'Active Staff', value: active, color: 'var(--green)' },
          { label: 'On Leave', value: onLeave, color: 'var(--orange)' },
        ].map((kpi) => (
          <div key={kpi.label}>
            <div
              style={{
                fontSize: '1.8rem',
                fontWeight: 900,
                color: kpi.color,
              }}
            >
              {kpi.value}
            </div>
            <div
              style={{
                fontSize: '0.68rem',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: 1,
              }}
            >
              {kpi.label}
            </div>
          </div>
        ))}
      </div>

      {/* Per-department breakdown */}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Department</th>
              <th>Employees</th>
              <th>Active</th>
              <th>On Leave</th>
              <th>Tasks</th>
              <th>Completed</th>
              <th>Overdue</th>
            </tr>
          </thead>
          <tbody>
            {depts.map((dept) => {
              const dUsers = users.filter((u) => u.department === dept);
              const dTasks = tasks.filter((t) => t.department === dept);
              const dDone = dTasks.filter((t) => t.status === 'completed').length;
              const dLeave = dUsers.filter((u) => u.availability_status === 'on_leave').length;
              const dActive = dUsers.filter((u) => u.availability_status === 'active').length;
              const dOverdue = dTasks.filter((t) => {
                try {
                  return new Date(t.sla_deadline) < new Date() && t.status !== 'completed';
                } catch { return false; }
              }).length;
              return (
                <tr key={dept}>
                  <td style={{ fontWeight: 700 }}>{dept}</td>
                  <td>{dUsers.length}</td>
                  <td style={{ color: 'var(--green)' }}>{dActive}</td>
                  <td style={{ color: dLeave > 0 ? 'var(--orange)' : 'var(--text-muted)' }}>
                    {dLeave}
                  </td>
                  <td>{dTasks.length}</td>
                  <td style={{ color: 'var(--green)' }}>{dDone}</td>
                  <td style={{ color: dOverdue > 0 ? 'var(--red)' : 'var(--text-muted)' }}>
                    {dOverdue}
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



/* ═══════════════════════════════════════════════════
   MAIN DASHBOARD
   ═══════════════════════════════════════════════════ */
export default function Dashboard() {
  const user = getUser();



  if (!user) {
    return (
      <div className="app-container">
        <div
          style={{
            padding: '2rem',
            color: 'white',
            textAlign: 'center',
          }}
        >
          Loading session...
        </div>
      </div>
    );
  }



  const [online, setOnline] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [simTaskId, setSimTaskId] = useState(null);
  const [reason, setReason] = useState('');
  const [assigning, setAssigning] = useState(false);



  useEffect(() => {
    checkHealth().then(setOnline);
    const iv = setInterval(
      () => checkHealth().then(setOnline),
      15000,
    );
    return () => clearInterval(iv);
  }, []);



  const fetchTasks = async () => {
    try {
      const data = await api('/api/tasks/');
      console.log('[FlowGuard] ✅ Tasks loaded:', data.length);
      setTasks(data);
    } catch (e) {
      console.error('[FlowGuard] ❌ fetchTasks failed:', e.message);
    }
  };



  const fetchLogs = async () => {
    if (!['head', 'manager'].includes(user.role)) return;
    try {
      const data = await api('/api/logs/');
      setLogs(data);
    } catch {
      /* swallow */
    }
  };



  const fetchUsers = async () => {
    if (user.role !== 'head') return;
    try {
      const data = await api('/api/auth/users');
      setUsers(data);
    } catch {
      /* swallow */
    }
  };



  useEffect(() => {
    fetchTasks();
    fetchLogs();
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);



  // ✅ FIX 3: no duplicate tasks — only fetch from DB, never spread wf.tasks
  const handleResult = () => {
    fetchTasks();
    fetchLogs();
    fetchUsers();
  };



  const handleAutoAssign = async (task) => {
    try {
      const res = await fetch(
        'http://localhost:8001/api/tasks/auto-assign',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('fg_token')}`,
          },
          body: JSON.stringify({
            task_id: task.id,
            task_type: task.task_type,
            department: task.department,
          }),
        },
      );
      const data = await res.json();
      alert(`Assigned to ${data.assigned_to}`);
      window.location.reload();
    } catch (err) {
      console.error(err);
      alert('Auto assign failed');
    }
  };



  return (
    <div className="app-container">
      <Navbar user={user} online={online} />



      <h1 className="hero-title">
        AUTONOMOUS WORKFLOW INTELLIGENCE
      </h1>
      <p className="hero-subtitle">
        Multi-Agent AI • Secure Masking • Predictive Efficiency
      </p>



      {['head', 'manager'].includes(user.role) && (
        <UploadPanel onResult={handleResult} />
      )}



      {/* ✅ Leave Approval Panel — manager/HOD */}
      {['head', 'manager'].includes(user.role) && (
        <LeaveApprovalPanel />
      )}



      {/* ✅ FIX 5: Employee Leave Apply Panel */}
      {user.role === 'employee' && <EmployeeLeavePanel />}



      {simTaskId && (
        <SimulationPanel
          taskId={simTaskId}
          onClose={() => setSimTaskId(null)}
        />
      )}



      {user.role === 'head' && (
        <PerformanceLeaderboard users={users} />
      )}



      {/* ✅ Phase 3 Item 13: HOD Company Overview */}
      {user.role === 'head' && (
        <HODOverview tasks={tasks} users={users} />
      )}



      <div className="grid-2">
        <RiskDashboard tasks={tasks} />
        {['head', 'manager'].includes(user.role) && (
          <AuditLogs logs={logs.slice(0, 5)} />
        )}
      </div>



      {['head', 'manager'].includes(user.role) && (
        <NeedsClarification tasks={tasks} />
      )}



      {reason && ['head', 'manager'].includes(user.role) && (
        <div
          style={{
            maxWidth: 800,
            margin: '0 auto 1.5rem',
            padding: '15px',
            borderRadius: '8px',
            backgroundColor: 'rgba(0,255,170,0.1)',
            border: '1px solid rgba(0,255,170,0.3)',
            color: '#00ffaa',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <span style={{ fontSize: '1.2rem' }}>🧠</span>
          <div>
            <strong style={{ display: 'block', marginBottom: '4px' }}>
              AI Assignment Insight:
            </strong>
            {reason}
          </div>
          <button
            onClick={() => setReason('')}
            style={{
              marginLeft: 'auto',
              background: 'none',
              border: 'none',
              color: '#00ffaa',
              cursor: 'pointer',
              fontSize: '1rem',
            }}
          >
            ×
          </button>
        </div>
      )}



      <TasksTable
        tasks={
          user.role === 'employee'
            ? tasks.filter((t) => t.assigned_to === user.user_id)
            : tasks
        }
        user={user}
        onSimulate={setSimTaskId}
        onAutoAssign={handleAutoAssign}
        onUpdate={() => {
          fetchTasks();
          fetchLogs();
          fetchUsers();
        }}
      />



      {['head', 'manager'].includes(user.role) && (
        <AuditLogs logs={logs} />
      )}
    </div>
  );
}