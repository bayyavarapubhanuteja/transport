import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  CheckCircle2,
  ShieldCheck,
  GitCompare,
  Plus,
  Trash2,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { getAnalyticsOverview, planJourney } from '../services/api';

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  // Google Maps & Ground-Truth Validation Log State
  const [valSource, setValSource] = useState('Rohini Sector 7');
  const [valDest, setValDest] = useState('Azadpur');
  const [valDepTime, setValDepTime] = useState('08:30');
  const [valActualMin, setValActualMin] = useState('');
  const [valDelhiMoveMin, setValDelhiMoveMin] = useState('');
  const [valGoogleMapsMin, setValGoogleMapsMin] = useState('');
  const [fetchingPrediction, setFetchingPrediction] = useState(false);
  const [valError, setValError] = useState('');

  const [validationRecords, setValidationRecords] = useState(() => {
    try {
      const saved = localStorage.getItem('delhimove_gmaps_validation');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    async function load() {
      try {
        const data = await getAnalyticsOverview();
        setAnalytics(data);
      } catch (e) {
        console.error('Error fetching analytics overview:', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem('delhimove_gmaps_validation', JSON.stringify(validationRecords));
    } catch {
      // ignore storage errors
    }
  }, [validationRecords]);

  const handleFetchDelhiMove = async () => {
    if (!valSource || !valDest) return;
    setFetchingPrediction(true);
    setValError('');
    try {
      const res = await planJourney({
        source: valSource,
        destination: valDest,
        departure_time: valDepTime,
        day_of_week: 0,
      });
      if (res.status === 'success' && res.journeys && res.journeys.length > 0) {
        setValDelhiMoveMin(String(res.journeys[0].total_duration_min));
      } else {
        setValError(res.message || 'No matching DelhiMove AI route found for this stop pair.');
      }
    } catch {
      setValError('Could not reach journey planner API.');
    } finally {
      setFetchingPrediction(false);
    }
  };

  const handleAddValidation = (e) => {
    e.preventDefault();
    setValError('');
    const actual = parseFloat(valActualMin);
    const dm = parseFloat(valDelhiMoveMin);
    const gm = parseFloat(valGoogleMapsMin);

    if (isNaN(actual) || isNaN(dm) || isNaN(gm) || actual <= 0 || dm <= 0 || gm <= 0) {
      setValError('Please enter valid positive travel times (in minutes) for Actual, DelhiMove AI, and Google Maps.');
      return;
    }

    const dmAbsErr = Math.round(Math.abs(dm - actual) * 10) / 10;
    const gmAbsErr = Math.round(Math.abs(gm - actual) * 10) / 10;

    const entry = {
      id: Date.now(),
      source: valSource.trim(),
      destination: valDest.trim(),
      departure_time: valDepTime,
      actual_min: actual,
      delhimove_min: dm,
      gmaps_min: gm,
      delhimove_abs_err: dmAbsErr,
      gmaps_abs_err: gmAbsErr,
    };

    setValidationRecords([entry, ...validationRecords]);
    setValActualMin('');
    setValGoogleMapsMin('');
  };

  const handleDeleteValidation = (id) => {
    setValidationRecords(validationRecords.filter((r) => r.id !== id));
  };

  const stats = analytics?.network_stats;
  const ml = analytics?.ml_evaluation;
  const rf = ml?.models?.random_forest || {};
  const base = ml?.models?.baseline_historical_avg || {};
  const featImp = ml?.feature_importances || {};
  const evalSamples = analytics?.actual_vs_predicted || [];

  const featureRows = [
    { key: 'distance_m', label: 'Segment Distance (m)', color: 'bg-teal-600' },
    { key: 'is_peak_hour', label: 'Peak Hour Indicator (8–10 AM, 5–8 PM)', color: 'bg-emerald-500' },
    { key: 'hour', label: 'Diurnal Hour of Day (0–23)', color: 'bg-amber-500' },
    { key: 'day_of_week', label: 'Day of Week (Mon–Sun)', color: 'bg-indigo-500' },
    { key: 'is_weekend', label: 'Weekend Indicator', color: 'bg-slate-400' },
  ];

  // Chart scaling for Actual vs Predicted SVG
  const maxSec = evalSamples.length > 0
    ? Math.max(...evalSamples.map((s) => Math.max(s.actual_sec, s.predicted_sec))) * 1.08
    : 800;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight flex items-center gap-2.5">
          <BarChart3 className="w-7 h-7 text-teal-700" />
          Network Analytics &amp; ML Model Evaluation
        </h1>
        <p className="text-base text-slate-600 mt-1">
          Verified SQLite GTFS counts, authentic held-out ML benchmarks, and ground-truth journey validation.
        </p>
      </div>

      {/* Network Scale KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">GTFS Bus Stops</span>
          <div className="text-3xl font-black text-navy-900 mt-1">
            {loading ? '...' : (stats?.total_stops ?? 0).toLocaleString()}
          </div>
          <span className="text-xs sm:text-sm text-teal-800 font-semibold mt-1 block">Verified in SQLite DB</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Bus Routes</span>
          <div className="text-3xl font-black text-navy-900 mt-1">
            {loading ? '...' : (stats?.total_routes ?? 0).toLocaleString()}
          </div>
          <span className="text-xs sm:text-sm text-teal-800 font-semibold mt-1 block">Indexed DTC &amp; DIMTS</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Scheduled Trips</span>
          <div className="text-3xl font-black text-navy-900 mt-1">
            {loading ? '...' : (stats?.total_scheduled_trips ?? 0).toLocaleString()}
          </div>
          <span className="text-xs sm:text-sm text-teal-800 font-semibold mt-1 block">
            {(stats?.total_traffic_segments ?? 0).toLocaleString()} road segments
          </span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Fleet Vehicles</span>
          <div className="text-3xl font-black text-teal-700 mt-1">
            {loading ? '...' : (stats?.registered_vehicle_fleet ?? 0).toLocaleString()}
          </div>
          <span className="text-xs sm:text-sm text-slate-600 font-medium mt-1 block">
            {(stats?.active_live_buses ?? 0).toLocaleString()} {stats?.is_live ? 'Live GTFS-RT Active' : 'Historical Snapshot'}
          </span>
        </div>
      </div>

      {/* ML Evaluation Benchmark */}
      <div className="bg-white rounded-2xl border border-slate-300/80 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-0.5 rounded-full text-xs font-black bg-navy-900 text-teal-300 uppercase tracking-wider">
                Model Evaluation Report
              </span>
              <span className="text-xs sm:text-sm font-bold text-slate-600">
                {ml?.split_strategy || 'Time-based held-out split'}
              </span>
            </div>
            <h2 className="text-xl font-extrabold text-navy-900 mt-1.5">
              Historical Baseline vs. Random Forest Regressor
            </h2>
          </div>

          {rf.improvement_vs_baseline_pct && (
            <div className="bg-teal-50 border border-teal-300 px-4 py-2 rounded-xl text-teal-900 text-sm font-bold">
              ⚡ {rf.improvement_vs_baseline_pct}% Reduction in Prediction Error (MAE)
            </div>
          )}
        </div>

        {/* Metrics Comparison Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm font-medium">
            <thead>
              <tr className="border-b-2 border-slate-200 text-navy-800 uppercase text-xs font-bold">
                <th className="py-3 px-4">Model Architecture</th>
                <th className="py-3 px-4">MAE (Seconds)</th>
                <th className="py-3 px-4">RMSE (Seconds)</th>
                <th className="py-3 px-4">MAPE (%)</th>
                <th className="py-3 px-4">R² Score</th>
                <th className="py-3 px-4">Evaluation Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              <tr className="hover:bg-slate-50">
                <td className="py-3.5 px-4 font-bold text-slate-800 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
                  Baseline (Historical Average Speed)
                </td>
                <td className="py-3.5 px-4 text-slate-700 font-mono text-base">{base.mae_seconds ?? '—'}s</td>
                <td className="py-3.5 px-4 text-slate-700 font-mono text-base">{base.rmse_seconds ?? '—'}s</td>
                <td className="py-3.5 px-4 text-slate-700 font-mono text-base">{base.mape_percent ?? '—'}%</td>
                <td className="py-3.5 px-4 text-slate-700 font-mono text-base">{base.r2_score ?? '—'}</td>
                <td className="py-3.5 px-4 text-slate-600 text-sm">Benchmark Reference</td>
              </tr>

              <tr className="bg-teal-50/60 hover:bg-teal-50">
                <td className="py-3.5 px-4 font-extrabold text-navy-900 flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-700"></span>
                  Random Forest Regressor (Production Model)
                </td>
                <td className="py-3.5 px-4 text-navy-900 font-mono font-bold text-base">
                  {rf.mae_seconds ?? '—'}s
                </td>
                <td className="py-3.5 px-4 text-navy-900 font-mono font-bold text-base">
                  {rf.rmse_seconds ?? '—'}s
                </td>
                <td className="py-3.5 px-4 text-navy-900 font-mono font-bold text-base">
                  {rf.mape_percent ?? '—'}%
                </td>
                <td className="py-3.5 px-4 text-navy-900 font-mono font-bold text-base">
                  {rf.r2_score ?? '—'}
                </td>
                <td className="py-3.5 px-4 text-emerald-800 font-bold text-sm flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> Deployed in API
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Actual vs Predicted Chart + Feature Importance */}
        <div className="mt-8 pt-6 border-t border-slate-200 grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Actual vs Predicted Travel-Time Comparison Chart */}
          <div>
            <h3 className="text-base font-extrabold text-navy-900 mb-1">
              Actual vs. Predicted Travel Time (Held-Out Test Set: Oct 22–31)
            </h3>
            <p className="text-sm text-slate-600 mb-3">
              36 stratified samples from the 19,000 held-out test records. Closer to the diagonal dashed line indicates lower error.
            </p>

            {evalSamples.length > 0 ? (
              <div className="bg-slate-50 rounded-xl border border-slate-300/80 p-3.5">
                <svg viewBox="0 0 420 260" className="w-full h-56 overflow-visible">
                  {/* Grid & Axes */}
                  <line x1="45" y1="20" x2="45" y2="220" stroke="#94a3b8" strokeWidth="1.5" />
                  <line x1="45" y1="220" x2="395" y2="220" stroke="#94a3b8" strokeWidth="1.5" />
                  {/* Perfect fit y = x line */}
                  <line x1="45" y1="220" x2="395" y2="20" stroke="#1e3a5f" strokeWidth="1.5" strokeDasharray="5 4" />
                  
                  {/* Axis labels */}
                  <text x="220" y="252" textAnchor="middle" fontSize="11" fill="#334155" fontWeight="700">
                    Actual Travel Time (seconds)
                  </text>
                  <text x="14" y="120" textAnchor="middle" fontSize="11" fill="#334155" fontWeight="700" transform="rotate(-90 14 120)">
                    Predicted (sec)
                  </text>
                  <text x="45" y="236" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">0s</text>
                  <text x="395" y="236" textAnchor="middle" fontSize="10" fill="#475569" fontWeight="600">{Math.round(maxSec)}s</text>

                  {/* Baseline points (slate) & RF points (teal) */}
                  {evalSamples.map((pt) => {
                    const x = 45 + (pt.actual_sec / maxSec) * 350;
                    const yRf = 220 - (pt.predicted_sec / maxSec) * 200;
                    const yBase = 220 - (pt.baseline_sec / maxSec) * 200;
                    return (
                      <g key={pt.id}>
                        <circle cx={x} cy={yBase} r="3" fill="#64748b" opacity="0.55">
                          <title>{`Baseline: ${pt.baseline_sec}s vs Actual: ${pt.actual_sec}s (${pt.distance_m}m @ ${pt.hour}:00)`}</title>
                        </circle>
                        <circle cx={x} cy={yRf} r="4.2" fill="#0f766e" stroke="#ffffff" strokeWidth="1">
                          <title>{`Random Forest: ${pt.predicted_sec}s vs Actual: ${pt.actual_sec}s (${pt.distance_m}m @ ${pt.hour}:00)`}</title>
                        </circle>
                      </g>
                    );
                  })}
                </svg>
                <div className="flex flex-wrap items-center justify-center gap-5 text-xs font-semibold text-slate-700 mt-1.5">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-teal-700 inline-block"></span>
                    Random Forest (MAE {rf.mae_seconds}s)
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-500 inline-block"></span>
                    Historical Baseline (MAE {base.mae_seconds}s)
                  </span>
                  <span className="text-navy-800">--- Ideal (y = x)</span>
                </div>
              </div>
            ) : (
              <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 text-sm text-slate-600">
                Loading held-out comparison samples...
              </div>
            )}
          </div>

          {/* Dynamic Feature Importance & Methodology */}
          <div className="space-y-5">
            <div>
              <h3 className="text-base font-extrabold text-navy-900 mb-1">Model Feature Importance (From Trained RF)</h3>
              <p className="text-sm text-slate-600 mb-3">
                Extracted directly from <code>model.feature_importances_</code> in <code>model_metrics.json</code>.
              </p>

              <div className="space-y-3">
                {featureRows.map((f) => {
                  const pct = Math.round((featImp[f.key] ?? 0) * 1000) / 10;
                  return (
                    <div key={f.key}>
                      <div className="flex justify-between text-sm font-bold text-slate-800 mb-1">
                        <span>{f.label}</span>
                        <span>{pct}%</span>
                      </div>
                      <div className="w-full h-2.5 bg-slate-200 rounded-full overflow-hidden">
                        <div className={`h-full ${f.color} rounded-full`} style={{ width: `${Math.max(0.5, pct)}%` }}></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 border border-slate-300/80">
              <h3 className="text-sm font-extrabold text-navy-900 mb-1.5 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-teal-700" />
                Anti-Leakage Protocol
              </h3>
              <p className="text-sm text-slate-700 leading-relaxed">
                Train set: <b>{(ml?.train_samples ?? 39900).toLocaleString()}</b> samples (Oct 1–21). Held-out test set: <b>{(ml?.test_samples ?? 19000).toLocaleString()}</b> samples (Oct 22–31). Full 24-hour diurnal schedules are preserved in both splits.
              </p>
            </div>
          </div>

        </div>
      </div>

      {/* Google Maps & Ground-Truth Validation Section */}
      <div className="bg-white rounded-2xl border border-slate-300/80 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-4">
          <div>
            <h2 className="text-xl font-extrabold text-navy-900 flex items-center gap-2">
              <GitCompare className="w-5 h-5 text-teal-700" />
              Google Maps &amp; Ground-Truth Validation Log
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Compare equivalent bus journeys across actual observed time, DelhiMove AI prediction, and manual Google Maps reference estimates.
              <span className="font-semibold text-navy-800"> (No live Google Maps API integrated — enter Google Maps reference times manually.)</span>
            </p>
          </div>
        </div>

        <form onSubmit={handleAddValidation} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-7 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-300/80 mb-5 items-end">
          <div>
            <label className="block text-xs font-bold text-navy-800 uppercase mb-1">Source</label>
            <input
              type="text"
              value={valSource}
              onChange={(e) => setValSource(e.target.value)}
              className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
              placeholder="e.g. Rohini Sector 7"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-navy-800 uppercase mb-1">Destination</label>
            <input
              type="text"
              value={valDest}
              onChange={(e) => setValDest(e.target.value)}
              className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
              placeholder="e.g. Azadpur"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-navy-800 uppercase mb-1">Departure</label>
            <input
              type="time"
              value={valDepTime}
              onChange={(e) => setValDepTime(e.target.value)}
              className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-navy-800 uppercase mb-1">Actual (min)</label>
            <input
              type="number"
              step="0.1"
              value={valActualMin}
              onChange={(e) => setValActualMin(e.target.value)}
              className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
              placeholder="e.g. 44.0"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-bold text-navy-800 uppercase">DelhiMove (min)</label>
              <button
                type="button"
                onClick={handleFetchDelhiMove}
                disabled={fetchingPrediction}
                className="text-xs font-bold text-teal-700 hover:underline flex items-center gap-0.5"
              >
                <Sparkles className="w-3 h-3" />
                {fetchingPrediction ? '...' : 'Fetch'}
              </button>
            </div>
            <input
              type="number"
              step="0.1"
              value={valDelhiMoveMin}
              onChange={(e) => setValDelhiMoveMin(e.target.value)}
              className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
              placeholder="e.g. 45.7"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-navy-800 uppercase mb-1">Google Maps (min)</label>
            <input
              type="number"
              step="0.1"
              value={valGoogleMapsMin}
              onChange={(e) => setValGoogleMapsMin(e.target.value)}
              className="w-full px-3 py-2.5 bg-white border border-slate-300 rounded-lg text-sm font-semibold text-slate-900"
              placeholder="e.g. 48.0"
            />
          </div>
          <div>
            <button
              type="submit"
              className="w-full py-2.5 px-3 bg-navy-900 hover:bg-teal-700 text-white text-sm font-bold rounded-lg flex items-center justify-center gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              Record Run
            </button>
          </div>
        </form>

        {valError && (
          <div className="mb-4 p-3.5 bg-amber-50 border border-amber-300 rounded-xl text-sm text-amber-900 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0" />
            <span>{valError}</span>
          </div>
        )}

        {validationRecords.length === 0 ? (
          <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-300 text-sm text-slate-600">
            No validation comparisons recorded yet. Click <b>Fetch</b> to pull DelhiMove AI&apos;s predicted time for a route, enter the actual observed time and Google Maps estimate, and click <b>Record Run</b>.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm font-medium">
              <thead>
                <tr className="border-b-2 border-slate-200 text-navy-800 uppercase text-xs font-bold">
                  <th className="py-3 px-3">Journey</th>
                  <th className="py-3 px-3">Dep</th>
                  <th className="py-3 px-3">Actual Observed</th>
                  <th className="py-3 px-3">DelhiMove AI</th>
                  <th className="py-3 px-3">Google Maps Ref</th>
                  <th className="py-3 px-3">DelhiMove Abs Error</th>
                  <th className="py-3 px-3">GMaps Abs Error</th>
                  <th className="py-3 px-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {validationRecords.map((rec) => (
                  <tr key={rec.id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-3 font-bold text-slate-800">{rec.source} ➔ {rec.destination}</td>
                    <td className="py-2.5 px-3 text-slate-500">{rec.departure_time}</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-800">{rec.actual_min} min</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-teal-700">{rec.delhimove_min} min</td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">{rec.gmaps_min} min</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-emerald-700">{rec.delhimove_abs_err} min</td>
                    <td className="py-2.5 px-3 font-mono text-slate-600">{rec.gmaps_abs_err} min</td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        type="button"
                        onClick={() => handleDeleteValidation(rec.id)}
                        className="text-slate-400 hover:text-rose-600"
                        title="Remove entry"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
