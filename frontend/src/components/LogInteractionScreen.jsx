import React, { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { fetchHcps } from '../store/slices/interactionSlice';
import InteractionDetailsForm from './InteractionDetailsForm';
import ChatInterface from './ChatInterface';
import InteractionList from './InteractionList';

export default function LogInteractionScreen() {
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(fetchHcps());
  }, [dispatch]);

  return (
    <div className="main">
      <h2 className="page-title">Log HCP Interaction</h2>
      <p className="page-subtitle">
        Capture a Healthcare Professional interaction using the structured form,
        or describe it to the AI Assistant in plain language — both use the
        same LangGraph tools underneath.
      </p>

      <div className="log-interaction-grid">
        <InteractionDetailsForm />
        <ChatInterface />
      </div>

      <h3 className="section-heading">Recent Interactions</h3>
      <InteractionList />
    </div>
  );
}
