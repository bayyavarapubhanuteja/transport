import React from 'react';
import { Compass, Bus, Activity, BarChart3 } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'planner', label: 'Journey Planner', icon: Compass },
    { id: 'live', label: 'Live Bus Tracking', icon: Bus },
    { id: 'traffic', label: 'Traffic & ML Engine', icon: Activity },
    { id: 'analytics', label: 'Analytics & Evals', icon: BarChart3 },
  ];

  return (
    <header className="sticky top-0 z-50 bg-navy-900 text-white border-b-4 border-teal-600 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Brand Logo */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white shadow-md ring-2 ring-teal-400/40 flex-shrink-0">
              <Bus className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl tracking-tight text-white whitespace-nowrap">
                  Delhi<span className="text-teal-400">Move</span>{' '}
                  <span className="text-xs px-2 py-0.5 rounded bg-teal-600 text-white font-bold uppercase tracking-wider">
                    AI
                  </span>
                </span>
              </div>
              <p className="text-xs font-medium text-slate-300 whitespace-nowrap">
                Delhi Public Bus Transit Portal
              </p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-bold whitespace-nowrap transition-all ${
                    isActive
                      ? 'bg-teal-600 text-white shadow-sm'
                      : 'text-slate-200 hover:text-white hover:bg-navy-800'
                  }`}
                >
                  <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-white' : 'text-teal-400'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Network Status Pill */}
          <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full bg-navy-800 border border-teal-500/40 text-teal-100 text-xs font-semibold whitespace-nowrap flex-shrink-0">
            <span className="relative flex h-2.5 w-2.5">
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400"></span>
            </span>
            <span>ML Engine Active</span>
            <span className="text-slate-500">|</span>
            <span>6,802 Stops</span>
          </div>
        </div>
      </div>

      {/* Mobile Nav Tabs */}
      <div className="md:hidden flex items-center justify-around border-t border-navy-800 py-2.5 bg-navy-900">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center gap-1 text-xs font-semibold px-2 py-1 rounded-lg ${
                isActive ? 'text-teal-300 bg-navy-800' : 'text-slate-300'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label.split(' ')[0]}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
}
