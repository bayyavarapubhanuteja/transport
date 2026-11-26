import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import JourneyPlannerPage from './pages/JourneyPlannerPage';
import LiveTrackingPage from './pages/LiveTrackingPage';
import TrafficPage from './pages/TrafficPage';
import AnalyticsPage from './pages/AnalyticsPage';
import { getHealth } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('planner');
  const [healthInfo, setHealthInfo] = useState(null);

  useEffect(() => {
    async function checkBackend() {
      try {
        const h = await getHealth();
        setHealthInfo(h);
      } catch (e) {
        console.warn('Backend not yet reachable:', e);
      }
    }
    checkBackend();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 text-slate-900">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthInfo={healthInfo}
      />

      {/* Main Page Content */}
      <main className="flex-1">
        {activeTab === 'planner' && <JourneyPlannerPage />}
        {activeTab === 'live' && <LiveTrackingPage />}
        {activeTab === 'traffic' && <TrafficPage />}
        {activeTab === 'analytics' && <AnalyticsPage />}
      </main>

      {/* Footer */}
      <footer className="bg-navy-900 text-slate-300 border-t-4 border-teal-600 mt-12 py-6 text-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-white">DelhiMove AI</span>
            <span className="text-slate-500">•</span>
            <span>Transport Stack Hackathon 2026 Problem 1</span>
          </div>
          <div className="flex items-center gap-4 text-slate-300">
            <span>GTFS 2.7M Records</span>
            <span className="text-slate-500">•</span>
            <span>6,810 GPS Buses</span>
            <span className="text-slate-500">•</span>
            <span className="text-teal-300 font-semibold">Random Forest MAE 10.96s</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
