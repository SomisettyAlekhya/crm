import React, { useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInteractions } from '../store/slices/interactionSlice';

export default function ReportsScreen() {
  const dispatch = useDispatch();
  const items = useSelector((s) => s.interactions.items);

  useEffect(() => {
    dispatch(fetchInteractions());
  }, [dispatch]);

  const stats = useMemo(() => {
    const sentimentCounts = { Positive: 0, Neutral: 0, Negative: 0 };
    const perHcp = {};
    let totalSamples = 0;
    let pendingFollowups = 0;

    for (const item of items) {
      const sentiment = item.sentiment || 'Neutral';
      sentimentCounts[sentiment] = (sentimentCounts[sentiment] || 0) + 1;
      totalSamples += item.samples_dropped || 0;
      if (item.followup_required) pendingFollowups += 1;

      const key = item.hcp_name || 'Unknown';
      perHcp[key] = (perHcp[key] || 0) + 1;
    }

    return {
      total: items.length,
      sentimentCounts,
      totalSamples,
      pendingFollowups,
      perHcp: Object.entries(perHcp).sort((a, b) => b[1] - a[1]),
    };
  }, [items]);

  return (
    <div className="main">
      <h2 className="page-title">Reports</h2>
      <p className="page-subtitle">A quick rollup of activity logged this session.</p>

      <div className="stats-grid">
        <div className="card stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="muted">Interactions logged</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats.totalSamples}</div>
          <div className="muted">Samples distributed</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{stats.pendingFollowups}</div>
          <div className="muted">Pending follow-ups</div>
        </div>
      </div>

      <h3 className="section-heading">Sentiment Breakdown</h3>
      <div className="card">
        {Object.entries(stats.sentimentCounts).map(([label, count]) => (
          <div key={label} className="report-row">
            <span className={`tag ${label.toLowerCase()}`}>{label}</span>
            <span>{count}</span>
          </div>
        ))}
      </div>

      <h3 className="section-heading">Interactions per HCP</h3>
      <div className="card">
        {stats.perHcp.length === 0 && <p className="muted">No interactions logged yet.</p>}
        {stats.perHcp.map(([name, count]) => (
          <div key={name} className="report-row">
            <span>{name}</span>
            <span>{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
