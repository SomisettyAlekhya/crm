import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage, resetChat } from '../store/slices/chatSlice';
import { upsertFromAgent } from '../store/slices/interactionSlice';

export default function ChatInterface() {
  const dispatch = useDispatch();
  const { messages, sending } = useSelector((s) => s.chat);
  const [draft, setDraft] = useState('');
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!draft.trim() || sending) return;
    const text = draft;
    setDraft('');
    const action = await dispatch(sendMessage(text));
    if (sendMessage.fulfilled.match(action)) {
      const toolResult = action.payload.response.tool_result;
      const toolUsed = action.payload.response.tool_used;
      if (toolResult && ['log_interaction', 'edit_interaction'].includes(toolUsed)) {
        dispatch(upsertFromAgent(toolResult));
      }
    }
  };

  return (
    <div className="card ai-assistant-card">
      <div className="ai-assistant-header">
        <span className="ai-assistant-icon">🤖</span>
        <div>
          <div className="panel-heading" style={{ margin: 0 }}>AI Assistant</div>
          <div className="muted" style={{ fontSize: 12 }}>Log interaction via chat</div>
        </div>
      </div>

      <div className="chat-window">
        <div className="chat-messages" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`bubble ${m.role === 'user' ? 'user' : 'agent'}`}>
              {m.toolUsed && <span className="tool-tag">🔧 {m.toolUsed.replace(/_/g, ' ')}</span>}
              {m.text}
            </div>
          ))}
          {sending && <div className="bubble agent muted">Agent is thinking…</div>}
        </div>
        <div className="chat-input-row">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder='Describe interaction... (e.g. "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure")'
          />
          <button className="primary-btn log-btn" onClick={handleSend} disabled={sending}>⚠ Log</button>
        </div>
      </div>
      <button
        className="ghost-btn small"
        style={{ marginTop: 12 }}
        onClick={() => dispatch(resetChat())}
      >
        Start New Conversation
      </button>
    </div>
  );
}
