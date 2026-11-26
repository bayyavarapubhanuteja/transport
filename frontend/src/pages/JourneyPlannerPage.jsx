import React, { useState, useEffect } from 'react';
import {
  Compass,
  ArrowRightLeft,
  Clock,
  MapPin,
  Bus,
  Footprints,
  Sparkles,
  ChevronRight,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  Share2,
  Calendar
} from 'lucide-react';
import { searchStops, planJourney } from '../services/api';
import LeafletMap from '../maps/LeafletMap';

export default function JourneyPlannerPage() {
  const [sourceQuery, setSourceQuery] = useState('Rohini Sector 7');
  const [sourceStop, setSourceStop] = useState({ stop_name: 'Rohini Sector 7' });
  const [sourceSuggestions, setSourceSuggestions] = useState([]);

  const [destQuery, setDestQuery] = useState('Azadpur');
  const [destStop, setDestStop] = useState({ stop_name: 'Azadpur' });
  const [destSuggestions, setDestSuggestions] = useState([]);

  const [departureTime, setDepartureTime] = useState('08:30');
  const [dayOfWeek, setDayOfWeek] = useState(0); // Monday (0=Mon..6=Sun)

  const [loading, setLoading] = useState(false);
  const [journeyResponse, setJourneyResponse] = useState(null);
  const [selectedJourneyId, setSelectedJourneyId] = useState(null);
  const [expandedJourneyId, setExpandedJourneyId] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  // Autocomplete suggestions for source
  useEffect(() => {
    if (sourceQuery.length >= 3 && (!sourceStop || sourceStop.stop_name !== sourceQuery)) {
      const timer = setTimeout(async () => {
        try {
          const stops = await searchStops(sourceQuery);
          setSourceSuggestions(stops);
        } catch (e) {
          setSourceSuggestions([]);
        }
      }, 250);
      return () => clearTimeout(timer);
    } else {
      setSourceSuggestions([]);
    }
  }, [sourceQuery, sourceStop]);

  // Autocomplete suggestions for destination
  useEffect(() => {
    if (destQuery.length >= 3 && (!destStop || destStop.stop_name !== destQuery)) {
      const timer = setTimeout(async () => {
        try {
          const stops = await searchStops(destQuery);
          setDestSuggestions(stops);
        } catch (e) {
          setDestSuggestions([]);
        }
      }, 250);
      return () => clearTimeout(timer);
    } else {
      setDestSuggestions([]);
    }
  }, [destQuery, destStop]);

  // Initial journey search on page load
  useEffect(() => {
    handleSearch();
  }, []);

  const handleSearch = async (src = sourceQuery, dst = destQuery) => {
    if (!src || !dst) {
      setErrorMsg('Please specify both a starting point and destination.');
      return;
    }

    setLoading(true);
    setErrorMsg('');

    try {
      const res = await planJourney({
        source: src,
        destination: dst,
        departure_time: departureTime,
        day_of_week: dayOfWeek,
      });

      if (res.status === 'success' && res.journeys && res.journeys.length > 0) {
        setJourneyResponse(res);
        setSelectedJourneyId(res.journeys[0].journey_id);
        setExpandedJourneyId(res.journeys[0].journey_id);
      } else {
        setJourneyResponse(res);
        setErrorMsg(res.message || 'No direct or single-transfer bus routes found for this pair.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Failed to communicate with journey planning engine. Please check backend server.');
    } finally {
      setLoading(false);
    }
  };

  const handleSwap = () => {
    const tempQ = sourceQuery;
    const tempS = sourceStop;
    setSourceQuery(destQuery);
    setSourceStop(destStop);
    setDestQuery(tempQ);
    setDestStop(tempS);
  };

  const handlePreset = (src, dst) => {
    setSourceQuery(src);
    setSourceStop({ stop_name: src });
    setDestQuery(dst);
    setDestStop({ stop_name: dst });
    handleSearch(src, dst);
  };

  const selectedJourney = journeyResponse?.journeys?.find(
    (j) => j.journey_id === selectedJourneyId
  ) || journeyResponse?.journeys?.[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-navy-900 tracking-tight">
          Intelligent Bus Journey Planner
        </h1>
        <p className="text-base text-slate-600 mt-1">
          Predictive multi-modal routing powered by machine learning, historical bus GPS traces, and traffic telemetry.
        </p>
      </div>

      {/* Main Grid: Left Controls & Results | Right Interactive Map */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Column: Input Form & Journey Cards */}
        <div className="lg:col-span-5 space-y-5">
          
          {/* Planner Input Card */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-300/80 relative">
            <div className="space-y-4">
              
              {/* Source Input */}
              <div className="relative">
                <label className="block text-xs font-bold text-navy-800 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-teal-600"></span>
                  Source (Bus Stop or Area)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={sourceQuery}
                    onChange={(e) => {
                      setSourceQuery(e.target.value);
                      setSourceStop(null);
                    }}
                    placeholder="Enter starting stop (e.g. Rohini, Kashmere Gate)..."
                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-base font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:bg-white transition-all"
                  />
                  <MapPin className="w-4 h-4 text-teal-700 absolute left-3.5 top-3.5" />
                </div>
                {/* Suggestions Dropdown */}
                {sourceSuggestions.length > 0 && (
                  <div className="absolute z-30 left-0 right-0 mt-1 bg-white border border-slate-300 rounded-xl shadow-lg max-h-56 overflow-y-auto">
                    {sourceSuggestions.map((st) => (
                      <button
                        key={st.stop_id}
                        type="button"
                        onClick={() => {
                          setSourceQuery(st.stop_name);
                          setSourceStop(st);
                          setSourceSuggestions([]);
                        }}
                        className="w-full text-left px-3.5 py-2.5 hover:bg-teal-50 text-sm font-medium text-slate-900 flex items-center justify-between border-b border-slate-100 last:border-0"
                      >
                        <span className="truncate">{st.stop_name}</span>
                        <span className="text-xs text-slate-500 ml-2">ID: {st.stop_id}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Swap Button */}
              <div className="flex justify-center -my-2 relative z-10">
                <button
                  type="button"
                  onClick={handleSwap}
                  title="Swap Source and Destination"
                  className="p-2 bg-white border border-slate-300 rounded-full text-navy-800 hover:text-teal-700 hover:border-teal-600 shadow-sm transition-all"
                >
                  <ArrowRightLeft className="w-4 h-4" />
                </button>
              </div>

              {/* Destination Input */}
              <div className="relative">
                <label className="block text-xs font-bold text-navy-800 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-600"></span>
                  Destination (Bus Stop or Area)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={destQuery}
                    onChange={(e) => {
                      setDestQuery(e.target.value);
                      setDestStop(null);
                    }}
                    placeholder="Enter destination stop (e.g. Azadpur, AIIMS)..."
                    className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-base font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:bg-white transition-all"
                  />
                  <MapPin className="w-4 h-4 text-rose-600 absolute left-3.5 top-3.5" />
                </div>
                {/* Suggestions Dropdown */}
                {destSuggestions.length > 0 && (
                  <div className="absolute z-30 left-0 right-0 mt-1 bg-white border border-slate-300 rounded-xl shadow-lg max-h-56 overflow-y-auto">
                    {destSuggestions.map((st) => (
                      <button
                        key={st.stop_id}
                        type="button"
                        onClick={() => {
                          setDestQuery(st.stop_name);
                          setDestStop(st);
                          setDestSuggestions([]);
                        }}
                        className="w-full text-left px-3.5 py-2.5 hover:bg-rose-50 text-sm font-medium text-slate-900 flex items-center justify-between border-b border-slate-100 last:border-0"
                      >
                        <span className="truncate">{st.stop_name}</span>
                        <span className="text-xs text-slate-500 ml-2">ID: {st.stop_id}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Departure Time & Day Controls */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="block text-xs font-bold text-navy-800 uppercase tracking-wider mb-1.5">
                    Departure Time
                  </label>
                  <div className="relative">
                    <input
                      type="time"
                      value={departureTime}
                      onChange={(e) => setDepartureTime(e.target.value)}
                      className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600"
                    />
                    <Clock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-navy-800 uppercase tracking-wider mb-1.5">
                    Day of Week
                  </label>
                  <div className="relative">
                    <select
                      value={dayOfWeek}
                      onChange={(e) => setDayOfWeek(parseInt(e.target.value))}
                      className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-600"
                    >
                      <option value={0}>Monday (Weekday)</option>
                      <option value={1}>Tuesday (Weekday)</option>
                      <option value={2}>Wednesday (Weekday)</option>
                      <option value={3}>Thursday (Weekday)</option>
                      <option value={4}>Friday (Weekday)</option>
                      <option value={5}>Saturday (Weekend)</option>
                      <option value={6}>Sunday (Weekend)</option>
                    </select>
                    <Calendar className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                  </div>
                </div>
              </div>

              {/* Find Journeys Button */}
              <button
                type="button"
                onClick={() => handleSearch()}
                disabled={loading}
                className="w-full mt-2 py-3.5 px-4 bg-navy-900 hover:bg-teal-700 text-white text-base font-bold rounded-xl shadow-md flex items-center justify-center gap-2 transition-all disabled:opacity-60"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    <span>Computing Optimal Bus Routes...</span>
                  </>
                ) : (
                  <>
                    <Compass className="w-5 h-5 text-teal-300" />
                    <span>Find Bus Journeys</span>
                  </>
                )}
              </button>

              {/* Popular Delhi Presets */}
              <div className="pt-3 border-t border-slate-200">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-2">
                  Popular Delhi Transit Corridors:
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => handlePreset('Rohini Sector 7', 'Azadpur')}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-teal-50 hover:text-teal-800 border border-slate-200 text-xs font-semibold text-slate-700 transition-colors"
                  >
                    Rohini ➔ Azadpur
                  </button>
                  <button
                    onClick={() => handlePreset('Anand Vihar ISBT', 'Kashmere Gate')}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-teal-50 hover:text-teal-800 border border-slate-200 text-xs font-semibold text-slate-700 transition-colors"
                  >
                    Anand Vihar ➔ Kashmere Gate
                  </button>
                  <button
                    onClick={() => handlePreset('Connaught Place', 'Nehru Place')}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-teal-50 hover:text-teal-800 border border-slate-200 text-xs font-semibold text-slate-700 transition-colors"
                  >
                    CP ➔ Nehru Place
                  </button>
                  <button
                    onClick={() => handlePreset('AIIMS', 'Dhaula Kuan')}
                    className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-teal-50 hover:text-teal-800 border border-slate-200 text-xs font-semibold text-slate-700 transition-colors"
                  >
                    AIIMS ➔ Dhaula Kuan
                  </button>
                </div>
              </div>

            </div>
          </div>

          {/* Error Notice */}
          {errorMsg && (
            <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl text-sm text-amber-900 flex items-start gap-2.5">
              <AlertCircle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block">Route Search Note:</span>
                <span>{errorMsg}</span>
              </div>
            </div>
          )}

          {/* Journey Options List */}
          {journeyResponse && journeyResponse.journeys && journeyResponse.journeys.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm font-bold text-navy-800 uppercase tracking-wider px-1">
                <span>Available Journeys ({journeyResponse.journeys.length})</span>
                <span className="text-teal-700 font-semibold normal-case">Sorted by ML Travel Time</span>
              </div>

              {journeyResponse.journeys.map((j) => {
                const isSelected = selectedJourneyId === j.journey_id;
                const isExpanded = expandedJourneyId === j.journey_id;

                return (
                  <div
                    key={j.journey_id}
                    onClick={() => setSelectedJourneyId(j.journey_id)}
                    className={`bg-white rounded-2xl p-5 border transition-all cursor-pointer ${
                      isSelected
                        ? 'border-teal-600 ring-2 ring-teal-600/25 shadow-md'
                        : 'border-slate-300/80 hover:border-navy-600 shadow-sm'
                    }`}
                  >
                    {/* Header Tags & Recommendation */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                      <div className="flex flex-wrap items-center gap-2">
                        {j.tags.map((tag, tIdx) => (
                          <span
                            key={tIdx}
                            className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${
                              tag.includes('Fastest')
                                ? 'bg-amber-100 text-amber-900 border border-amber-300'
                                : 'bg-navy-50 text-navy-900 border border-navy-100'
                            }`}
                          >
                            {tag}
                          </span>
                        ))}
                        <span className="text-xs font-semibold text-slate-600">
                          {j.transfers === 0 ? 'Direct Route' : `${j.transfers} Transfer`}
                        </span>
                      </div>

                      {/* Congestion Badge */}
                      <span className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wide ${
                        j.overall_congestion === 'high' ? 'bg-red-100 text-red-800' :
                        j.overall_congestion === 'moderate' ? 'bg-amber-100 text-amber-800' :
                        'bg-emerald-100 text-emerald-800'
                      }`}>
                        {j.overall_congestion} Congestion
                      </span>
                    </div>

                    {/* Time & Routes Summary */}
                    <div className="flex items-baseline justify-between mb-3">
                      <div>
                        <div className="text-3xl font-black text-navy-900">
                          {j.total_duration_min} <span className="text-sm font-bold text-slate-600">min</span>
                        </div>
                        <div className="text-sm text-slate-600 font-semibold mt-0.5">
                          {j.departure_time} ➔ {j.arrival_time}
                        </div>
                      </div>

                      {/* Route badges */}
                      <div className="flex items-center gap-1.5">
                        {j.routes.map((r, rIdx) => (
                          <React.Fragment key={rIdx}>
                            <span className="px-3 py-1.5 rounded-lg bg-navy-900 text-white font-extrabold text-sm shadow-sm flex items-center gap-1.5">
                              <Bus className="w-3.5 h-3.5 text-teal-300" />
                              {r}
                            </span>
                            {rIdx < j.routes.length - 1 && (
                              <span className="text-slate-400 font-bold">➔</span>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>

                    {/* Sub-breakdown: Walking, In-bus, Waiting, Distance */}
                    <div className="grid grid-cols-4 gap-2 py-2.5 px-3.5 bg-slate-50 rounded-xl text-sm border border-slate-200 mb-3">
                      <div>
                        <span className="text-slate-500 block text-xs uppercase font-bold">In Bus</span>
                        <span className="font-bold text-navy-900">{j.bus_travel_time_min}m</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-xs uppercase font-bold">Walk</span>
                        <span className="font-bold text-navy-900">{j.walking_time_min}m</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-xs uppercase font-bold">Wait</span>
                        <span className="font-bold text-navy-900">{j.waiting_time_min}m</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-xs uppercase font-bold">Distance</span>
                        <span className="font-bold text-navy-900">{j.total_distance_km} km</span>
                      </div>
                    </div>

                    {/* ML Model vs Baseline Comparison Bar */}
                    <div className="pt-2.5 border-t border-slate-200 flex items-center justify-between text-xs sm:text-sm">
                      <div className="flex items-center gap-1.5 text-teal-800 font-semibold">
                        <Sparkles className="w-4 h-4 text-teal-600" />
                        <span>
                          {j.prediction_method === 'random_forest_regressor' ? 'ML Predicted' : 'Historical Avg'}: <b>{j.total_duration_min} min</b>
                        </span>
                        <span className="text-slate-500">(Baseline: {j.baseline_duration_min} min)</span>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedJourneyId(isExpanded ? null : j.journey_id);
                        }}
                        className="text-sm font-bold text-navy-800 hover:text-teal-700 flex items-center gap-0.5"
                      >
                        <span>{isExpanded ? 'Hide Steps' : 'View Itinerary'}</span>
                        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                      </button>
                    </div>

                    {/* Expanded Turn-by-Turn Itinerary */}
                    {isExpanded && (
                      <div className="mt-4 pt-3.5 border-t border-slate-200 space-y-3.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-navy-800 uppercase tracking-wider">
                            Turn-by-Turn Journey Itinerary
                          </span>
                          <span className="text-xs font-semibold text-teal-800 bg-teal-50 border border-teal-200 px-2.5 py-0.5 rounded">
                            {j.reliability || 'ML Calibrated'} ({j.ml_coverage_pct ?? 100}% ML)
                          </span>
                        </div>

                        {/* Initial Walk to Boarding Stop */}
                        <div className="flex items-start gap-2.5 text-sm">
                          <div className="w-6 h-6 rounded-full bg-slate-200 text-navy-800 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <Footprints className="w-3.5 h-3.5" />
                          </div>
                          <div>
                            <span className="font-semibold text-slate-900">
                              Walk {Math.round(j.initial_walk_m ?? 0)} m to {j.legs[0]?.board_stop}
                            </span>
                            <span className="text-slate-600 block text-xs mt-0.5">
                              ~{j.initial_walk_min ?? 0} min walk • Wait ~{j.waiting_time_min - (j.transfer_wait_min || 0)} min at stop
                            </span>
                          </div>
                        </div>

                        {/* Transit Legs */}
                        {j.legs.map((leg, lIdx) => (
                          <React.Fragment key={lIdx}>
                            {lIdx > 0 && (
                              <div className="flex items-start gap-2.5 text-sm bg-amber-50 p-2.5 rounded-lg border border-amber-200">
                                <span className="text-amber-700 font-bold">🔄</span>
                                <div>
                                  <span className="font-bold text-amber-900">
                                    Transfer at {leg.board_stop}
                                  </span>
                                  <span className="text-amber-800 block text-xs">
                                    Wait ~{j.transfer_wait_min || 8} min for Route {leg.route_short_name}
                                  </span>
                                </div>
                              </div>
                            )}
                            <div className="border-l-2 border-teal-600 pl-3.5 ml-2.5 space-y-2">
                              <div className="flex items-start gap-2 text-sm">
                                <Bus className="w-4 h-4 text-teal-700 flex-shrink-0 mt-0.5" />
                                <div>
                                  <span className="font-bold text-navy-900">
                                    Board Route {leg.route_short_name} {leg.board_time ? `at ${leg.board_time}` : ''}
                                  </span>
                                  <span className="text-slate-700 block text-xs mt-0.5">
                                    From <b>{leg.board_stop}</b> towards {leg.trip_headsign || leg.alight_stop}
                                  </span>
                                </div>
                              </div>

                              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-1.5">
                                <div className="flex justify-between font-semibold text-slate-800">
                                  <span>Transit Duration ({leg.prediction_method === 'random_forest_regressor' ? 'ML Predicted' : 'Historical Avg'}):</span>
                                  <span className="font-bold text-teal-800">{leg.duration_min} min</span>
                                </div>
                                <div className="flex justify-between text-slate-600">
                                  <span>Distance &amp; Stops:</span>
                                  <span>{leg.distance_km} km • {leg.stops_count} stops</span>
                                </div>
                                {leg.stops && leg.stops.length > 2 && (
                                  <div className="pt-1.5 border-t border-slate-200 text-xs text-slate-600 leading-relaxed">
                                    <span className="font-semibold text-slate-700">Intermediate stops: </span>
                                    {leg.stops.slice(1, -1).slice(0, 6).map((s) => s.stop_name).join(' • ')}
                                    {leg.stops.length - 2 > 6 ? ` (+${leg.stops.length - 8} more)` : ''}
                                  </div>
                                )}
                              </div>

                              <div className="text-sm text-slate-800 font-semibold">
                                ➔ Alight at <b>{leg.alight_stop}</b> {leg.alight_time ? `(${leg.alight_time})` : ''}
                              </div>
                            </div>
                          </React.Fragment>
                        ))}

                        {/* Final Walk & Arrival */}
                        <div className="flex items-start gap-2.5 text-sm pt-1">
                          <div className="w-6 h-6 rounded-full bg-rose-100 text-rose-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                            <MapPin className="w-3.5 h-3.5" />
                          </div>
                          <div>
                            <span className="font-bold text-navy-900">
                              Walk {Math.round(j.final_walk_m ?? 0)} m ({j.final_walk_min ?? 0} min) to {journeyResponse.destination?.name || 'Destination'}
                            </span>
                            <span className="text-slate-600 block text-xs mt-0.5">
                              Estimated arrival: <b>{j.arrival_time}</b>
                            </span>
                          </div>
                        </div>
                      </div>
                    )}

                  </div>
                );
              })}
            </div>
          )}

        </div>

        {/* Right Column: Interactive Delhi Map & Polyline */}
        <div className="lg:col-span-7 sticky top-24">
          <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-300/80">
            <div className="flex items-center justify-between mb-3 px-1">
              <div>
                <span className="font-extrabold text-base text-navy-900">Route Geometry &amp; Traffic Map</span>
                <p className="text-xs sm:text-sm text-slate-600">
                  {selectedJourney
                    ? `Visualizing ${selectedJourney.routes.join(' + ')} with ML-calibrated road segment traffic`
                    : 'Showing Delhi bus network. Search for directions to see route polyline.'}
                </p>
              </div>

              {selectedJourney && (
                <div className="text-sm font-bold text-teal-800 bg-teal-50 px-3 py-1 rounded-lg border border-teal-200 whitespace-nowrap">
                  {selectedJourney.total_distance_km} km total
                </div>
              )}
            </div>

            <LeafletMap
              journey={selectedJourney}
              className="w-full h-[540px] rounded-xl"
            />
          </div>
        </div>

      </div>
    </div>
  );
}
