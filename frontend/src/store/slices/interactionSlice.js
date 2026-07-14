import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { api } from '../../api/api';

export const fetchHcps = createAsyncThunk('interactions/fetchHcps', async () => {
  return await api.listHcps();
});

export const fetchInteractions = createAsyncThunk('interactions/fetchInteractions', async (hcpId) => {
  return await api.listInteractions(hcpId);
});

export const submitInteractionForm = createAsyncThunk(
  'interactions/submitForm',
  async (payload) => await api.logInteractionForm(payload)
);

export const editInteraction = createAsyncThunk(
  'interactions/edit',
  async ({ id, updates }) => await api.editInteraction(id, updates)
);

export const fetchHcpProfile = createAsyncThunk(
  'interactions/fetchHcpProfile',
  async (name) => await api.getHcpProfileByName(name)
);

export const fetchCallPrep = createAsyncThunk(
  'interactions/fetchCallPrep',
  async (name) => await api.callPrep(name)
);

export const scheduleFollowup = createAsyncThunk(
  'interactions/scheduleFollowup',
  async ({ interactionId, followupDate, note }) =>
    await api.scheduleFollowup({ interaction_id: interactionId, followup_date: followupDate, note })
);

const interactionSlice = createSlice({
  name: 'interactions',
  initialState: {
    hcps: [],
    items: [],
    status: 'idle',
    error: null,
    lastLogged: null,
    hcpProfile: null,
    callPrep: null,
    sidePanelStatus: 'idle',
    sidePanelError: null,
  },
  reducers: {
    upsertFromAgent(state, action) {
      const record = action.payload;
      const idx = state.items.findIndex((i) => i.id === record.id);
      if (idx >= 0) state.items[idx] = record;
      else state.items.unshift(record);
      state.lastLogged = record;
    },
    clearSidePanel(state) {
      state.hcpProfile = null;
      state.callPrep = null;
      state.sidePanelError = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.hcps = action.payload;
      })
      .addCase(fetchInteractions.pending, (state) => {
        state.status = 'loading';
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.items = action.payload;
      })
      .addCase(fetchInteractions.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.error.message;
      })
      .addCase(submitInteractionForm.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
        state.lastLogged = action.payload;
      })
      .addCase(editInteraction.fulfilled, (state, action) => {
        const idx = state.items.findIndex((i) => i.id === action.payload.id);
        if (idx >= 0) state.items[idx] = action.payload;
      })
      .addCase(fetchHcpProfile.pending, (state) => {
        state.sidePanelStatus = 'loading';
        state.callPrep = null;
      })
      .addCase(fetchHcpProfile.fulfilled, (state, action) => {
        state.sidePanelStatus = 'succeeded';
        state.hcpProfile = action.payload;
      })
      .addCase(fetchHcpProfile.rejected, (state, action) => {
        state.sidePanelStatus = 'failed';
        state.sidePanelError = action.error.message;
        state.hcpProfile = null;
      })
      .addCase(fetchCallPrep.pending, (state) => {
        state.sidePanelStatus = 'loading';
        state.hcpProfile = null;
      })
      .addCase(fetchCallPrep.fulfilled, (state, action) => {
        state.sidePanelStatus = 'succeeded';
        state.callPrep = action.payload;
      })
      .addCase(fetchCallPrep.rejected, (state, action) => {
        state.sidePanelStatus = 'failed';
        state.sidePanelError = action.error.message;
        state.callPrep = null;
      })
      .addCase(scheduleFollowup.fulfilled, (state, action) => {
        const idx = state.items.findIndex((i) => i.id === action.payload.id);
        if (idx >= 0) state.items[idx] = action.payload;
      });
  },
});

export const { upsertFromAgent, clearSidePanel } = interactionSlice.actions;
export default interactionSlice.reducer;
