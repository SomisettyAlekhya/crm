import React, { useState } from 'react';
import LogInteractionScreen from './components/LogInteractionScreen';
import HcpDirectoryScreen from './components/HcpDirectoryScreen';
import CallPrepScreen from './components/CallPrepScreen';
import FollowUpsScreen from './components/FollowUpsScreen';
import ReportsScreen from './components/ReportsScreen';

const SCREENS = {
  log: { label: 'Log Interaction', component: LogInteractionScreen },
  directory: { label: 'HCP Directory', component: HcpDirectoryScreen },
  callPrep: { label: 'Call Prep', component: CallPrepScreen },
  followUps: { label: 'Follow-ups', component: FollowUpsScreen },
  reports: { label: 'Reports', component: ReportsScreen },
};

export default function App() {
  const [activeScreen, setActiveScreen] = useState('log');
  const ActiveComponent = SCREENS[activeScreen].component;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>HCP CRM</h1>
        {Object.entries(SCREENS).map(([key, { label }]) => (
          <div
            key={key}
            className={`sidebar-item ${activeScreen === key ? 'active' : ''}`}
            onClick={() => setActiveScreen(key)}
          >
            {label}
          </div>
        ))}
      </aside>
      <ActiveComponent />
    </div>
  );
}
