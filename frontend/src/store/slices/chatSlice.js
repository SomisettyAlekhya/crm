import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { v4 as uuidv4 } from 'uuid';
import { api } from '../../api/api';

export const sendMessage = createAsyncThunk('chat/sendMessage', async (message, { getState }) => {
  const { sessionId } = getState().chat;
  const response = await api.sendChatMessage(sessionId, message);
  return { message, response };
});

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    sessionId: uuidv4(),
    messages: [
      {
        role: 'agent',
        text: "Hi! Tell me about an HCP interaction and I'll log it for you — e.g. \"Met Dr. Carter in person today, she was positive about Cardiozen and I dropped 10 samples, follow up next week.\"",
      },
    ],
    sending: false,
  },
  reducers: {
    resetChat(state) {
      state.messages = [state.messages[0]];
      state.sessionId = uuidv4();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.sending = true;
        state.messages.push({ role: 'user', text: action.meta.arg });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.sending = false;
        const { response } = action.payload;
        state.messages.push({
          role: 'agent',
          text: response.reply,
          toolUsed: response.tool_used,
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.sending = false;
        state.messages.push({ role: 'agent', text: `Error: ${action.error.message}` });
      });
  },
});

export const { resetChat } = chatSlice.actions;
export default chatSlice.reducer;
