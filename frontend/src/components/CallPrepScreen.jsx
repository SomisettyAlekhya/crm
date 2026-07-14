import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchHcps, fetchCallPrep, clearSidePanel } from '../store/slices/interactionSlice';

export default function CallPrepScreen() {
  const dispatch = useDispatch();
  const hcps = useSelector((s) => s.interactions.hcps);
  const callPrep = useSelector((s) => s.interactions.callPrep);
  const sidePanelStatus = useSelector((s) => s.interactions.sidePanelStatus);
  const sidePanelError = useSelector((s) => s.interactions.sidePanelError);
  const [hcpName, setHcpName] = useState('');

  useEffect(() => {
    dispatch(fetchHcps());
    return () => dispatch(clearSidePanel());
  }, [dispatch]);

  // Uses the generate_call_prep_summary LangGraph tool.
  const handleGenerate = (e) => {
    e.preventDefault();
    if (!hcpName.trim()) return;
    dispatch(clearSidePanel());
    dispatch(fetchCallPrep(hcpName));
  };

  return (
    <div className="main">
      <h2 className="page-title">Call Prep</h2>
      <p className="page-subtitle">
        Generate a quick pre-visit briefing from an HCP's interaction history before you walk into a meeting.
      </p>

      <form onSubmit={handleGenerate} className="card" style={{ maxWidth: 480, marginBottom: 24 }}>
        <div className="field">
          <label>Healthcare Professional</label>
          <input
            list="cp-hcp-options"
            value={hcpName}
            onChange={(e) => setHcpName(e.target.value)}
            placeholder="e.g. Dr. Emily Carter"
          />
          <datalist id="cp-hcp-options">
            {hcps.map((h) => <option key={h.id} value={h.name} />)}
          </datalist>
        </div>
        <button className="primary-btn" type="submit">Generate Briefing</button>
      </form>

      {sidePanelStatus === 'loading' && <p className="muted">Generating briefing…</p>}
      {sidePanelError && <p style={{ color: 'var(--color-negative)' }}>{sidePanelError}</p>}

      {callPrep && (
        <div className="card" style={{ maxWidth: 640 }}>
          <h3 className="panel-heading">{callPrep.hcp?.name}</h3>
          <p className="muted" style={{ marginTop: -10 }}>
            {callPrep.hcp?.specialty} · {callPrep.hcp?.hospital}
          </p>
          <h4 className="section-heading">Briefing</h4>
          <p>{callPrep.briefing}</p>
          {callPrep.sentiment_trend && (
            <p><span className={`tag ${callPrep.sentiment_trend.toLowerCase()}`}>{callPrep.sentiment_trend}</span> sentiment trend</p>
          )}
          {callPrep.last_topics?.length > 0 && (
            <p className="muted">Recent topics: {callPrep.last_topics.join(', ')}</p>
          )}
          {callPrep.open_followups?.length > 0 && (
            <div>
              <h4 className="section-heading">Open Follow-ups</h4>
              {callPrep.open_followups.map((f) => (
                <div className="interaction-item" key={f.id}>
                  <strong>{f.interaction_type}</strong> — due {f.followup_date}
                  <p className="muted" style={{ margin: '4px 0 0 0' }}>{f.summary}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
