import React, { useState, useEffect } from 'react';
import { Bus, RefreshCw, Filter, Zap, Gauge, AlertTriangle, CheckCircle, Search, Compass } from 'lucide-react';
import { getLiveVehicles, getRoutes } from '../services/api';
import LeafletMap from '../maps/LeafletMap';

export default function LiveTrackingPage() {
  const [vehicles, setVehicles] = useState([]);
  const [feedInfo, setFeedInfo] = useState({
    feed_status: 'checking',
    is_live: false,
    feed_message: '',
    stale_count: 0,
    total_active_live: 0,
    total_registered_fleet: 6810,
  });
  const [selectedRoute, setSelectedRoute] = useState('');
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [routesList, setRoutesList] = useState([]);
  const [searchFilter, setSearchFilter] = useState('');

  // Fetch routes list for the dropdown
  useEffect(() => {
    async function loadRoutes() {
      try {
        const routes = await getRoutes('', 50);
        setRoutesList(routes);
      } catch (e) {
        console.error(e);
      }
    }
    loadRoutes();
  }, []);

  // Fetch live vehicles
  const fetchVehicles = async () => {
    setLoading(true);
    try {
      const data = await getLiveVehicles(selectedRoute || null, 200);
      if (data && data.vehicles) {
        setVehicles(data.vehicles);
        setFeedInfo({
          feed_status: data.feed_status || 'unavailable',
          is_live: Boolean(data.is_live),
          feed_message: data.feed_message || '',
          stale_count: data.stale_count ?? data.vehicles.length,
          total_active_live: data.total_active_live ?? data.vehicles.length,
          total_registered_fleet: data.total_registered_fleet ?? 6810,
        });
        setLastRefreshed(new Date());
      }
    } catch (e) {
      console.error('Error fetching live vehicles:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVehicles();
  }, [selectedRoute]);

  // Periodic polling every 5s if auto-refresh is active
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchVehicles();
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedRoute]);

  const filteredVehicles = vehicles.filter((v) => {
    if (!searchFilter) return true;
    const q = searchFilter.toLowerCase();
    return (
      v.vehicle_id.toLowerCase().includes(q) ||
      v.route_short_name.toLowerCase().includes(q) ||
      (v.route_long_name && v.route_long_name.toLowerCase().includes(q))
    );
  });

  const evCount = vehicles.filter((v) => v.is_electric).length;
  const highCongestionCount = vehicles.filter((v) => v.congestion_level === 'high').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight flex items-center gap-2.5">
            <Bus className="w-7 h-7 text-teal-700" />
            Delhi Bus Fleet Telemetry
          </h1>
          <p className="text-base text-slate-600 mt-1">
            GPS tracking across Delhi bus corridors with speed, timestamps, and EV status.
          </p>
        </div>

        {/* Live Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold border transition-all ${
              autoRefresh
                ? 'bg-emerald-50 text-emerald-900 border-emerald-300'
                : 'bg-white text-navy-800 border-slate-300'
            }`}
          >
            <span className={`w-2.5 h-2.5 rounded-full ${autoRefresh ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`}></span>
            {autoRefresh ? 'Auto-Refresh (5s)' : 'Paused'}
          </button>

          <button
            onClick={fetchVehicles}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-navy-900 hover:bg-teal-700 text-white rounded-xl text-sm font-bold shadow-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 text-teal-300 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Feed Status Banner (Honest Live vs Unavailable / Stale Handling) */}
      {feedInfo.feed_status !== 'checking' && (
        feedInfo.is_live ? (
          <div className="mb-5 p-4 bg-emerald-50 border border-emerald-300 rounded-2xl text-sm text-emerald-950 flex items-start gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-700 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-extrabold block">Authorized Delhi Buses GTFS-RT Feed Connected</span>
              <span className="text-emerald-900">{feedInfo.feed_message} Displaying {vehicles.length} vehicles on map.</span>
            </div>
          </div>
        ) : (
          <div className="mb-5 p-4 bg-amber-50 border border-amber-300 rounded-2xl text-sm text-amber-950 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-extrabold block">Authorized Live GPS Feed Unavailable</span>
              <span className="text-amber-900">{feedInfo.feed_message}</span>
            </div>
          </div>
        )
      )}

      {/* Fleet Metric Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-white p-4 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            {feedInfo.is_live ? 'Active Live Fleet' : 'Monitored Snapshot'}
          </span>
          <div className="text-3xl font-black text-navy-900 mt-1">
            {(feedInfo.is_live ? feedInfo.total_active_live : vehicles.length).toLocaleString()}
          </div>
          <span className="text-xs text-teal-800 font-semibold mt-0.5 block">
            {feedInfo.is_live ? `Showing ${vehicles.length} on map` : `of ${feedInfo.total_registered_fleet.toLocaleString()} Registered Fleet`}
          </span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Electric Buses</span>
          <div className="text-3xl font-black text-teal-700 mt-1">{evCount}</div>
          <span className="text-xs text-slate-600 font-medium mt-0.5 block">Zero-Emission Fleet</span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Stale / Offline GPS</span>
          <div className="text-3xl font-black text-amber-700 mt-1">{feedInfo.stale_count}</div>
          <span className="text-xs text-slate-600 font-medium mt-0.5 block">
            {feedInfo.is_live ? 'Older than 5 min' : 'Historical Oct Records'}
          </span>
        </div>
        <div className="bg-white p-4 rounded-2xl border border-slate-300/80 shadow-sm">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">Feed Status</span>
          <div className={`text-lg font-extrabold mt-1 ${feedInfo.is_live ? 'text-emerald-700' : 'text-amber-800'}`}>
            {feedInfo.is_live ? 'Live GPS Active' : 'Historical Fallback'}
          </div>
          <span className="text-xs text-slate-600 font-medium mt-0.5 block">
            Checked {lastRefreshed.toLocaleTimeString()}
          </span>
        </div>
      </div>

      {/* Main Content Grid: Left Vehicle Roster | Right Live Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Vehicle List & Filter */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Filters Card */}
          <div className="bg-white p-4 rounded-2xl border border-slate-300/80 shadow-sm space-y-3">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  placeholder="Filter by vehicle ID or route..."
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600"
                />
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              </div>

              <select
                value={selectedRoute}
                onChange={(e) => setSelectedRoute(e.target.value)}
                className="py-2.5 px-3 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600 max-w-[150px]"
              >
                <option value="">All Corridors</option>
                {routesList.map((r) => (
                  <option key={r.route_id} value={r.route_short_name}>
                    {r.route_short_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Vehicle Cards List */}
          <div className="bg-white rounded-2xl border border-slate-300/80 shadow-sm p-3 max-h-[540px] overflow-y-auto space-y-2.5">
            {filteredVehicles.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-600 font-medium">
                No active vehicles match the current filter.
              </div>
            ) : (
              filteredVehicles.map((v) => {
                const isSelected = selectedVehicle?.vehicle_id === v.vehicle_id;
                return (
                  <div
                    key={v.vehicle_id}
                    onClick={() => setSelectedVehicle(v)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'border-teal-600 ring-2 ring-teal-600/20 bg-teal-50/40'
                        : 'border-slate-200 hover:border-navy-600 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-base text-navy-900">{v.vehicle_id}</span>
                        {v.is_electric && (
                          <span className="px-2 py-0.5 rounded text-xs font-extrabold bg-emerald-100 text-emerald-900 flex items-center gap-0.5">
                            <Zap className="w-3 h-3" /> EV
                          </span>
                        )}
                      </div>
                      <span className="px-2.5 py-0.5 rounded-lg bg-navy-900 text-white text-xs font-extrabold whitespace-nowrap">
                        {v.route_short_name}
                      </span>
                    </div>

                    <div className="text-sm text-slate-700 truncate mb-1">
                      {v.last_stop_name ? `At: ${v.last_stop_name}` : (v.route_long_name || 'Delhi Transport Corridor')}
                    </div>

                    <div className="text-xs text-slate-500 mb-2 flex items-center justify-between">
                      <span>Updated: {v.last_updated ? v.last_updated.slice(0, 19).replace('T', ' ') : 'N/A'}</span>
                      {v.is_stale && (
                        <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-900 font-bold text-xs">STALE</span>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-sm pt-2 border-t border-slate-200">
                      <div className="flex items-center gap-1.5 text-slate-700">
                        <Gauge className="w-4 h-4 text-slate-500" />
                        <span className="font-bold text-navy-900">{v.speed_kmh} km/h</span>
                      </div>

                      <span className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                        v.congestion_level === 'high' ? 'bg-red-100 text-red-800' :
                        v.congestion_level === 'moderate' ? 'bg-amber-100 text-amber-800' :
                        'bg-emerald-100 text-emerald-800'
                      }`}>
                        {v.congestion_level}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

        </div>

        {/* Right Column: Live Map */}
        <div className="lg:col-span-7 sticky top-24">
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-300/80">
            <div className="flex items-center justify-between mb-3 px-1">
              <div>
                <span className="font-extrabold text-base text-navy-900">Vehicle Positions Map</span>
                <p className="text-xs sm:text-sm text-slate-600">
                  Showing {vehicles.length} buses. Click any marker for speed, route, and timestamp details.
                </p>
              </div>

              {selectedVehicle && (
                <div className="text-xs sm:text-sm font-bold text-teal-800 bg-teal-50 px-3 py-1 rounded-lg border border-teal-200">
                  Focused: {selectedVehicle.vehicle_id}
                </div>
              )}
            </div>

            <LeafletMap
              liveBuses={vehicles}
              selectedVehicle={selectedVehicle}
              className="w-full h-[540px] rounded-xl"
            />
          </div>
        </div>

      </div>
    </div>
  );
}
