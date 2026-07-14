import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInteractions, editInteraction } from '../store/slices/interactionSlice';

export default function FollowUpsScreen() {
  const dispatch = useDispatch();
  const items = useSelector((s) => s.interactions.items);

  useEffect(() => {
    dispatch(fetchInteractions());
  }, [dispatch]);

  const pending = items
    .filter((i) => i.followup_required)
    .sort((a, b) => (a.followup_date || '').localeCompare(b.followup_date || ''));

  // Marking a follow-up done goes through the edit_interaction tool
  // (PATCH /api/interactions/{id}), same tool the Edit button uses elsewhere.
  const markDone = (item) => {
    dispatch(editInteraction({ id: item.id, updates: { followup_required: false } }));
  };

  return (
    <div className="main">
      <h2 className="page-title">Follow-ups</h2>
      <p className="page-subtitle">Interactions flagged as needing a follow-up, soonest first.</p>

      {pending.length === 0 && (
        <p className="muted">No pending follow-ups. Log an interaction with a follow-up date, or schedule one from the Log Interaction screen.</p>
      )}

      <div className="interaction-list">
        {pending.map((item) => (
          <div className="interaction-item" key={item.id}>
            <div className="interaction-item-header">
              <strong>{item.hcp_name} · {item.interaction_type}</strong>
              <span className="tag neutral">Due {item.followup_date || 'unscheduled'}</span>
            </div>
            <p style={{ margin: '4px 0' }}>{item.summary}</p>
            {item.followup_note && <p className="muted">Note: {item.followup_note}</p>}
            <button className="ghost-btn small" onClick={() => markDone(item)}>Mark Done</button>
          </div>
        ))}
      </div>
    </div>
  );
}
