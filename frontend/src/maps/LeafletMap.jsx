import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet's default icon path issue with bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Custom colored pin icons
const createPinIcon = (color, text = '') => {
  return L.divIcon({
    className: 'custom-pin',
    html: `
      <div style="
        background-color: ${color};
        color: white;
        border: 2px solid white;
        border-radius: 9999px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 700;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: max-content;
        white-space: nowrap;
        transform: translate(-50%, -50%);
      ">
        ${text}
      </div>
    `,
    iconSize: null,
  });
};

const createBusIcon = (route, heading = 0, isEv = false, congestion = 'low') => {
  const bg = congestion === 'high' ? '#dc2626' : (congestion === 'moderate' ? '#d97706' : '#0f766e');
  return L.divIcon({
    className: 'custom-bus-icon',
    html: `
      <div style="
        background-color: ${bg};
        color: white;
        border: 2px solid white;
        border-radius: 8px;
        padding: 3px 8px;
        font-size: 11px;
        font-weight: 800;
        box-shadow: 0 3px 8px rgba(0,0,0,0.3);
        display: inline-flex;
        align-items: center;
        gap: 4px;
        width: max-content;
        white-space: nowrap;
        transform: translate(-50%, -50%);
        cursor: pointer;
      ">
        <span>${isEv ? '⚡' : '🚌'}</span>
        <span>${route}</span>
      </div>
    `,
    iconSize: null,
  });
};

export default function LeafletMap({
  center = [28.6139, 77.2090],
  zoom = 12,
  journey = null,
  liveBuses = [],
  onMapClick = null,
  selectedVehicle = null,
  highlightRoute = null,
  className = "w-full h-full min-h-[450px]"
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layersGroupRef = useRef(null);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center,
        zoom,
        zoomControl: false,
      });

      // OpenStreetMap tiles
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      const layersGroup = L.layerGroup().addTo(map);
      layersGroupRef.current = layersGroup;

      mapInstanceRef.current = map;

      setTimeout(() => {
        if (mapInstanceRef.current) {
          mapInstanceRef.current.invalidateSize();
        }
      }, 150);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
        layersGroupRef.current = null;
      }
    };
  }, []);

  // Handle Map Clicks
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    const handleClick = (e) => {
      if (onMapClick) {
        onMapClick({ lat: e.latlng.lat, lon: e.latlng.lng });
      }
    };

    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
    };
  }, [onMapClick]);

  // Update Layers (Journey, Buses, Shapes)
  useEffect(() => {
    const map = mapInstanceRef.current;
    const group = layersGroupRef.current;
    if (!map || !group) return;

    group.clearLayers();
    const bounds = [];

    // 1. Render Journey Polyline & Stops
    if (journey && journey.legs) {
      journey.legs.forEach((leg, legIdx) => {
        // Traffic Congestion Color-Coded Segments
        if (leg.traffic_segments && leg.traffic_segments.length > 0) {
          leg.traffic_segments.forEach((seg) => {
            const color = seg.congestion_level === 'high'
              ? '#ef4444' // Red: Heavy
              : (seg.congestion_level === 'moderate'
                ? '#f59e0b' // Amber: Moderate
                : '#10b981'); // Emerald: Low

            const poly = L.polyline([seg.from_coords, seg.to_coords], {
              color,
              weight: 6,
              opacity: 0.9,
              lineCap: 'round',
              lineJoin: 'round',
            }).addTo(group);

            poly.bindPopup(`
              <div class="p-2 text-xs font-sans">
                <div class="font-bold text-slate-800 text-sm mb-1">${leg.route_short_name} Bus Segment</div>
                <div class="text-slate-600 mb-1"><b>From:</b> ${seg.from_stop}</div>
                <div class="text-slate-600 mb-1"><b>To:</b> ${seg.to_stop}</div>
                <div class="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span class="font-semibold text-slate-700">${(seg.distance_m / 1000).toFixed(2)} km</span>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    seg.congestion_level === 'high' ? 'bg-red-100 text-red-700' :
                    seg.congestion_level === 'moderate' ? 'bg-amber-100 text-amber-700' :
                    'bg-emerald-100 text-emerald-700'
                  }">
                    ${seg.congestion_level} congestion (${seg.effective_speed_kmh} km/h)
                  </span>
                </div>
                <div class="text-[11px] text-teal-700 mt-1">Predicted: ${seg.duration_sec}s</div>
              </div>
            `);
          });
        } else if (leg.shape_coords && leg.shape_coords.length > 0) {
          // Fallback solid route polyline
          L.polyline(leg.shape_coords, {
            color: '#0d9488',
            weight: 6,
            opacity: 0.85,
          }).addTo(group);
        }

        // Add leg coordinates to bounds
        if (leg.shape_coords) {
          leg.shape_coords.forEach((coord) => bounds.push(coord));
        }

        // Stop markers along the journey
        if (leg.stops) {
          leg.stops.forEach((st, idx) => {
            const isBoard = idx === 0;
            const isAlight = idx === leg.stops.length - 1;
            
            if (isBoard) {
              const marker = L.marker([st.stop_lat, st.stop_lon], {
                icon: createPinIcon('#0d9488', `Board ${leg.route_short_name}`),
              }).addTo(group);
              marker.bindPopup(`<b>Board Here:</b> ${st.stop_name}<br/>Route: <b>${leg.route_short_name}</b>`);
              bounds.push([st.stop_lat, st.stop_lon]);
            } else if (isAlight) {
              const marker = L.marker([st.stop_lat, st.stop_lon], {
                icon: createPinIcon(legIdx === journey.legs.length - 1 ? '#ef4444' : '#8b5cf6', 
                  legIdx === journey.legs.length - 1 ? '🏁 Dest' : '🔄 Transfer'),
              }).addTo(group);
              marker.bindPopup(`<b>${legIdx === journey.legs.length - 1 ? 'Alight Destination' : 'Transfer Stop'}:</b> ${st.stop_name}`);
              bounds.push([st.stop_lat, st.stop_lon]);
            } else {
              // Intermediate transit stop dot
              const circle = L.circleMarker([st.stop_lat, st.stop_lon], {
                radius: 4,
                color: '#ffffff',
                weight: 1.5,
                fillColor: '#0f766e',
                fillOpacity: 0.9,
              }).addTo(group);
              circle.bindTooltip(st.stop_name, { direction: 'top', offset: [0, -4] });
            }
          });
        }
      });
    }

    // 2. Render Highlight Route (from Route Explorer)
    if (highlightRoute && highlightRoute.shape_coords && highlightRoute.shape_coords.length > 0) {
      const routePoly = L.polyline(highlightRoute.shape_coords, {
        color: '#0284c7',
        weight: 6,
        opacity: 0.85,
      }).addTo(group);
      highlightRoute.shape_coords.forEach((c) => bounds.push(c));

      if (highlightRoute.stops) {
        highlightRoute.stops.forEach((s) => {
          L.circleMarker([s.stop_lat, s.stop_lon], {
            radius: 4,
            color: '#ffffff',
            weight: 1.5,
            fillColor: '#0369a1',
            fillOpacity: 0.9,
          }).bindTooltip(s.stop_name).addTo(group);
        });
      }
    }

    // 3. Render Live Buses
    if (liveBuses && liveBuses.length > 0) {
      liveBuses.forEach((bus) => {
        const marker = L.marker([bus.latitude, bus.longitude], {
          icon: createBusIcon(bus.route_short_name, bus.bearing, bus.is_electric, bus.congestion_level),
          zIndexOffset: 100,
        }).addTo(group);

        marker.bindPopup(`
          <div class="p-2 font-sans text-xs">
            <div class="flex items-center justify-between gap-2 mb-1">
              <span class="font-extrabold text-slate-800 text-sm">${bus.vehicle_id}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                bus.is_electric ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-700'
              }">${bus.agency}</span>
            </div>
            <div class="text-slate-600 mb-1"><b>Route:</b> ${bus.route_short_name} (${bus.route_long_name || 'DTC Corridor'})</div>
            <div class="flex items-center gap-3 mt-2 pt-2 border-t border-slate-100">
              <div>
                <span class="text-slate-400 text-[10px] block">SPEED</span>
                <span class="font-bold text-slate-700 text-sm">${bus.speed_kmh} km/h</span>
              </div>
              <div>
                <span class="text-slate-400 text-[10px] block">CONGESTION</span>
                <span class="font-bold uppercase text-xs ${
                  bus.congestion_level === 'high' ? 'text-red-600' :
                  bus.congestion_level === 'moderate' ? 'text-amber-600' : 'text-emerald-600'
                }">${bus.congestion_level}</span>
              </div>
            </div>
            <div class="text-[10px] text-slate-500 mt-2">
              <b>Last Update:</b> ${bus.last_updated || 'Unknown'} ${bus.is_stale ? '<span style="color:#b45309;font-weight:700;">(STALE)</span>' : ''}
            </div>
            <div class="text-[10px] text-slate-400">Source: ${bus.data_source}</div>
          </div>
        `);

        if (selectedVehicle && selectedVehicle.vehicle_id === bus.vehicle_id) {
          bounds.push([bus.latitude, bus.longitude]);
          marker.openPopup();
        }
      });
    }

    // Adjust Map Bounds to fit content
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  }, [journey, liveBuses, highlightRoute, selectedVehicle]);

  return (
    <div className="relative w-full h-full rounded-2xl overflow-hidden shadow-sm border border-slate-200">
      <div ref={mapContainerRef} className={className} />
      
      {/* Map Legend Overlay */}
      <div className="absolute bottom-4 left-4 bg-white/95 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-300 shadow-md text-xs sm:text-sm font-semibold z-[1000] flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-emerald-600 inline-block"></span>
          <span className="text-slate-700">Low Congestion</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-amber-500 inline-block"></span>
          <span className="text-slate-700">Moderate</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-600 inline-block"></span>
          <span className="text-slate-700">Heavy Traffic</span>
        </div>
      </div>
    </div>
  );
}
