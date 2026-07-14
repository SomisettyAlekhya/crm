const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listHcps: () => request('/api/hcps'),
  getHcp: (id) => request(`/api/hcps/${id}`),
  getHcpProfileByName: (name) => request(`/api/hcps/profile?name=${encodeURIComponent(name)}`),

  listInteractions: (hcpId) =>
    request(`/api/interactions${hcpId ? `?hcp_id=${hcpId}` : ''}`),
  logInteractionForm: (payload) =>
    request('/api/interactions', { method: 'POST', body: JSON.stringify(payload) }),
  previewSummary: (rawNotes) =>
    request('/api/interactions/preview-summary', { method: 'POST', body: JSON.stringify({ raw_notes: rawNotes }) }),
  editInteraction: (id, updates) =>
    request(`/api/interactions/${id}`, { method: 'PATCH', body: JSON.stringify(updates) }),
  deleteInteraction: (id) =>
    request(`/api/interactions/${id}`, { method: 'DELETE' }),
  scheduleFollowup: (payload) =>
    request('/api/interactions/followup', { method: 'POST', body: JSON.stringify(payload) }),
  callPrep: (hcpName) =>
    request(`/api/interactions/call-prep/${encodeURIComponent(hcpName)}`),

  sendChatMessage: (sessionId, message) =>
    request('/api/chat', { method: 'POST', body: JSON.stringify({ session_id: sessionId, message }) }),
  resetChatSession: (sessionId) =>
    request(`/api/chat/reset/${sessionId}`, { method: 'POST' }),
};
