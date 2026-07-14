import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  submitInteractionForm,
  fetchHcpProfile,
  fetchCallPrep,
  scheduleFollowup,
  clearSidePanel,
} from '../store/slices/interactionSlice';
import { api } from '../api/api';

const INTERACTION_TYPES = ['Meeting', 'Phone Call', 'Email', 'Conference'];

export default function InteractionDetailsForm() {
  const dispatch = useDispatch();
  const hcps = useSelector((s) => s.interactions.hcps);
  const lastLogged = useSelector((s) => s.interactions.lastLogged);
  const hcpProfile = useSelector((s) => s.interactions.hcpProfile);
  const callPrep = useSelector((s) => s.interactions.callPrep);
  const sidePanelStatus = useSelector((s) => s.interactions.sidePanelStatus);

  const [hcpName, setHcpName] = useState('');
  const [interactionType, setInteractionType] = useState(INTERACTION_TYPES[0]);
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [attendees, setAttendees] = useState('');
  const [notes, setNotes] = useState('');
  const [materialInput, setMaterialInput] = useState('');
  const [materials, setMaterials] = useState([]);
  const [sampleInput, setSampleInput] = useState('');
  const [samples, setSamples] = useState([]);
  const [sentiment, setSentiment] = useState('');
  const [outcomes, setOutcomes] = useState('');
  const [followupActions, setFollowupActions] = useState('');
  const [followupDate, setFollowupDate] = useState('');
  const [voicePreview, setVoicePreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const addMaterial = () => {
    if (materialInput.trim()) {
      setMaterials([...materials, materialInput.trim()]);
      setMaterialInput('');
    }
  };

  const addSample = () => {
    if (sampleInput.trim()) {
      setSamples([...samples, { name: sampleInput.trim(), quantity: 1 }]);
      setSampleInput('');
    }
  };

  // Tool #3: get_hcp_profile -- surfaces the HCP's profile + history right
  // next to the Name field, exercising the same tool chat mode uses.
  const handleViewProfile = () => {
    if (!hcpName.trim()) return;
    dispatch(clearSidePanel());
    dispatch(fetchHcpProfile(hcpName));
  };

  // Tool #5: generate_call_prep_summary
  const handleCallPrep = () => {
    if (!hcpName.trim()) return;
    dispatch(clearSidePanel());
    dispatch(fetchCallPrep(hcpName));
  };

  // "Summarize from Voice Note" -- previews what the AI summarization step
  // would produce from the current Topics Discussed text (stand-in for a
  // real speech-to-text pipeline, which needs mic/API access this offline
  // build intentionally avoids).
  const handleVoiceSummarize = async () => {
    if (!notes.trim()) return;
    const consented = window.confirm(
      'Summarizing from a voice note requires the HCP\'s consent to be recorded. Confirm consent was obtained?'
    );
    if (!consented) return;
    try {
      const preview = await api.previewSummary(notes);
      setVoicePreview(preview);
    } catch (e) {
      setVoicePreview({ summary: `Error: ${e.message}` });
    }
  };

  // Tool #1: log_interaction
  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const action = await dispatch(
        submitInteractionForm({
          hcp_name: hcpName,
          interaction_type: interactionType,
          raw_notes: notes,
          date,
          time,
          attendees,
          materials_shared: materials,
          samples_distributed: samples,
          manual_sentiment: sentiment || null,
          outcomes,
          followup_actions: followupActions,
        })
      );
      if (submitInteractionForm.fulfilled.match(action)) {
        setNotes('');
        setMaterials([]);
        setSamples([]);
        setOutcomes('');
        setFollowupActions('');
        setVoicePreview(null);
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Tool #4: schedule_followup -- applied to the interaction we just logged.
  const handleScheduleFollowup = () => {
    if (!lastLogged || !followupDate) return;
    dispatch(scheduleFollowup({ interactionId: lastLogged.id, followupDate, note: followupActions }));
  };

  const applySuggestion = (suggestion) => {
    setFollowupActions((prev) => (prev ? `${prev}\n${suggestion}` : suggestion));
  };

  return (
    <div className="card">
      <h3 className="panel-heading">Interaction Details</h3>
      <form onSubmit={handleSubmit}>
        <div className="two-col">
          <div className="field">
            <label>HCP Name</label>
            <div className="inline-input-row">
              <input
                list="hcp-options"
                value={hcpName}
                onChange={(e) => setHcpName(e.target.value)}
                placeholder="Search or select HCP..."
                required
              />
            </div>
            <datalist id="hcp-options">
              {hcps.map((h) => (
                <option key={h.id} value={h.name} />
              ))}
            </datalist>
            <div className="mini-actions">
              <button type="button" className="link-btn" onClick={handleViewProfile}>View Profile</button>
              <button type="button" className="link-btn" onClick={handleCallPrep}>Call Prep</button>
            </div>
          </div>

          <div className="field">
            <label>Interaction Type</label>
            <select value={interactionType} onChange={(e) => setInteractionType(e.target.value)}>
              {INTERACTION_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>

        {(hcpProfile || callPrep || sidePanelStatus === 'loading') && (
          <div className="side-panel-result">
            {sidePanelStatus === 'loading' && <span className="muted">Loading…</span>}
            {hcpProfile && (
              <div>
                <strong>{hcpProfile.name}</strong> · {hcpProfile.specialty} · {hcpProfile.hospital} · Tier {hcpProfile.tier}
                <div className="muted" style={{ marginTop: 4 }}>
                  {hcpProfile.interaction_history.length} prior interaction(s) on file.
                </div>
              </div>
            )}
            {callPrep && (
              <div>
                <strong>Call Prep Briefing</strong>
                <p style={{ margin: '4px 0' }}>{callPrep.briefing}</p>
                {callPrep.open_followups?.length > 0 && (
                  <div className="muted">{callPrep.open_followups.length} open follow-up(s)</div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="two-col">
          <div className="field">
            <label>Date</label>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div className="field">
            <label>Time</label>
            <input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label>Attendees</label>
          <input value={attendees} onChange={(e) => setAttendees(e.target.value)} placeholder="Enter names or search..." />
        </div>

        <div className="field">
          <label>Topics Discussed</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Enter key discussion points..."
            required
          />
          <button type="button" className="ghost-btn small" style={{ marginTop: 8 }} onClick={handleVoiceSummarize}>
            🎙 Summarize from Voice Note (Requires Consent)
          </button>
          {voicePreview && (
            <div className="side-panel-result" style={{ marginTop: 8 }}>
              <div className="muted">AI preview</div>
              <p style={{ margin: '4px 0' }}>{voicePreview.summary}</p>
            </div>
          )}
        </div>

        <div className="field">
          <label>Materials Shared</label>
          <div className="inline-input-row">
            <input
              value={materialInput}
              onChange={(e) => setMaterialInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addMaterial())}
              placeholder="Search / add material..."
            />
            <button type="button" className="ghost-btn small" onClick={addMaterial}>Add</button>
          </div>
          <div className="chip-row">
            {materials.map((m, i) => <span className="chip" key={i}>{m}</span>)}
            {materials.length === 0 && <span className="muted">No materials added</span>}
          </div>
        </div>

        <div className="field">
          <label>Samples Distributed</label>
          <div className="inline-input-row">
            <input
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSample())}
              placeholder="Sample name..."
            />
            <button type="button" className="ghost-btn small" onClick={addSample}>Add Sample</button>
          </div>
          <div className="chip-row">
            {samples.map((s, i) => <span className="chip" key={i}>{s.name} × {s.quantity}</span>)}
            {samples.length === 0 && <span className="muted">No samples added</span>}
          </div>
        </div>

        <div className="field">
          <label>Observed / Inferred HCP Sentiment</label>
          <div className="radio-row">
            {['Positive', 'Neutral', 'Negative'].map((s) => (
              <label key={s} className="radio-option">
                <input
                  type="radio"
                  name="sentiment"
                  value={s}
                  checked={sentiment === s}
                  onChange={() => setSentiment(s)}
                />
                {s}
              </label>
            ))}
          </div>
          <div className="muted" style={{ marginTop: 4 }}>Leave blank to let the AI infer sentiment from your notes.</div>
        </div>

        <div className="field">
          <label>Outcomes</label>
          <textarea value={outcomes} onChange={(e) => setOutcomes(e.target.value)} placeholder="Key outcomes or agreements..." />
        </div>

        <div className="field">
          <label>Follow-up Actions</label>
          <textarea value={followupActions} onChange={(e) => setFollowupActions(e.target.value)} placeholder="Enter next steps or tasks..." />
          <div className="inline-input-row" style={{ marginTop: 8 }}>
            <input type="date" value={followupDate} onChange={(e) => setFollowupDate(e.target.value)} />
            <button
              type="button"
              className="ghost-btn small"
              onClick={handleScheduleFollowup}
              disabled={!lastLogged || !followupDate}
              title={!lastLogged ? 'Log an interaction first' : ''}
            >
              Schedule Follow-up
            </button>
          </div>
        </div>

        {lastLogged?.suggested_followups?.length > 0 && (
          <div className="field">
            <label>AI Suggested Follow-ups</label>
            <ul className="suggestion-list">
              {lastLogged.suggested_followups.map((s, i) => (
                <li key={i}>
                  <button type="button" className="link-btn" onClick={() => applySuggestion(s)}>+ {s}</button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button className="primary-btn" type="submit" disabled={submitting}>
          {submitting ? 'Logging...' : 'Log Interaction'}
        </button>
      </form>

      {lastLogged && (
        <div style={{ marginTop: 20, paddingTop: 20, borderTop: '1px solid var(--color-border)' }}>
          <div className="muted" style={{ marginBottom: 6 }}>AI-generated summary (Groq · gemma2-9b-it)</div>
          <p style={{ margin: '0 0 10px 0' }}>{lastLogged.summary}</p>
          <span className={`tag ${lastLogged.sentiment.toLowerCase()}`}>{lastLogged.sentiment}</span>
          {lastLogged.followup_required && (
            <span className="muted" style={{ marginLeft: 10 }}>
              Suggested follow-up: {lastLogged.followup_date}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
