import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInteractions, editInteraction } from '../store/slices/interactionSlice';

export default function InteractionList() {
  const dispatch = useDispatch();
  const items = useSelector((s) => s.interactions.items);

  useEffect(() => {
    dispatch(fetchInteractions());
  }, [dispatch]);

  const handleQuickEdit = (item) => {
    const newNotes = window.prompt('Edit notes for this interaction:', item.raw_notes || '');
    if (newNotes !== null && newNotes !== item.raw_notes) {
      dispatch(editInteraction({ id: item.id, updates: { raw_notes: newNotes } }));
    }
  };

  if (!items.length) {
    return <p className="muted">No interactions logged yet. Use the form or chat above to log your first one.</p>;
  }

  return (
    <div className="interaction-list">
      {items.map((item) => (
        <div className="interaction-item" key={item.id}>
          <div className="interaction-item-header">
            <strong>{item.hcp_name} · {item.interaction_type}</strong>
            <span className={`tag ${item.sentiment?.toLowerCase() || 'neutral'}`}>{item.sentiment || 'Neutral'}</span>
          </div>
          <p style={{ margin: '4px 0' }}>{item.summary}</p>
          <div className="muted">
            Topics: {(item.topics_discussed || []).join(', ')} · Samples: {item.samples_dropped ?? 0}
            {item.followup_required && ` · Follow-up: ${item.followup_date}`}
          </div>
          <button className="ghost-btn" style={{ marginTop: 10 }} onClick={() => handleQuickEdit(item)}>
            Edit
          </button>
        </div>
      ))}
    </div>
  );
}
