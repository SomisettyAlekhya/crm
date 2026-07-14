import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchHcps, fetchHcpProfile, clearSidePanel } from '../store/slices/interactionSlice';

export default function HcpDirectoryScreen() {
  const dispatch = useDispatch();
  const hcps = useSelector((s) => s.interactions.hcps);
  const hcpProfile = useSelector((s) => s.interactions.hcpProfile);
  const sidePanelStatus = useSelector((s) => s.interactions.sidePanelStatus);
  const [query, setQuery] = useState('');

  useEffect(() => {
    dispatch(fetchHcps());
    return () => dispatch(clearSidePanel());
  }, [dispatch]);

  const filtered = hcps.filter((h) =>
    h.name.toLowerCase().includes(query.toLowerCase()) ||
    h.specialty.toLowerCase().includes(query.toLowerCase())
  );

  // Uses the get_hcp_profile LangGraph tool via GET /api/hcps/profile
  const handleSelect = (name) => {
    dispatch(clearSidePanel());
    dispatch(fetchHcpProfile(name));
  };

  return (
    <div className="main">
      <h2 className="page-title">HCP Directory</h2>
      <p className="page-subtitle">Browse your Healthcare Professionals and view their full interaction history.</p>

      <div className="field" style={{ maxWidth: 360 }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name or specialty..."
        />
      </div>

      <div className="directory-grid">
        <div className="card" style={{ padding: 0 }}>
          {filtered.map((h) => (
            <div
              key={h.id}
              className={`directory-row ${hcpProfile?.id === h.id ? 'active' : ''}`}
              onClick={() => handleSelect(h.name)}
            >
              <div>
                <strong>{h.name}</strong>
                <div className="muted">{h.specialty} · {h.hospital}</div>
              </div>
              <span className="tag neutral">Tier {h.tier}</span>
            </div>
          ))}
          {filtered.length === 0 && <p className="muted" style={{ padding: 16 }}>No HCPs match your search.</p>}
        </div>

        <div className="card">
          {sidePanelStatus === 'loading' && <p className="muted">Loading profile…</p>}
          {!hcpProfile && sidePanelStatus !== 'loading' && (
            <p className="muted">Select an HCP to view their profile and interaction history.</p>
          )}
          {hcpProfile && (
            <div>
              <h3 className="panel-heading">{hcpProfile.name}</h3>
              <p className="muted" style={{ marginTop: -10 }}>
                {hcpProfile.specialty} · {hcpProfile.hospital} · Tier {hcpProfile.tier} · {hcpProfile.phone}
              </p>
              <h4 className="section-heading" style={{ marginTop: 20 }}>Interaction History</h4>
              {hcpProfile.interaction_history.length === 0 && (
                <p className="muted">No interactions logged yet with this HCP.</p>
              )}
              {hcpProfile.interaction_history.map((item) => (
                <div className="interaction-item" key={item.id}>
                  <div className="interaction-item-header">
                    <strong>{item.interaction_type} · {item.date || item.created_at.slice(0, 10)}</strong>
                    <span className={`tag ${item.sentiment?.toLowerCase() || 'neutral'}`}>{item.sentiment || 'Neutral'}</span>
                  </div>
                  <p style={{ margin: '4px 0' }}>{item.summary}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
