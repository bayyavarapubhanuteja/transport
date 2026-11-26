import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getHealth = async () => {
  const res = await api.get('/health');
  return res.data;
};

export const searchStops = async (query) => {
  const res = await api.get('/stops', { params: { q: query, limit: 12 } });
  return res.data.stops || [];
};

export const getNearbyStops = async (lat, lon, radius = 1500) => {
  const res = await api.get('/stops', { params: { lat, lon, radius, limit: 10 } });
  return res.data.stops || [];
};

export const getAllStops = async (limit = 100) => {
  const res = await api.get('/stops', { params: { limit } });
  return res.data.stops || [];
};

export const getRoutes = async (query = '', limit = 100) => {
  const res = await api.get('/routes', { params: { q: query, limit } });
  return res.data.routes || [];
};

export const getRouteDetails = async (routeId) => {
  const res = await api.get(`/routes/${encodeURIComponent(routeId)}`);
  return res.data.route;
};

export const getLiveVehicles = async (routeId = null, limit = 150) => {
  const params = { limit };
  if (routeId) params.route_id = routeId;
  const res = await api.get('/vehicles/live', { params });
  return res.data;
};

export const getVehicleDetails = async (vehicleId) => {
  const res = await api.get(`/vehicles/${encodeURIComponent(vehicleId)}`);
  return res.data.vehicle;
};

export const getTrafficOverview = async () => {
  const res = await api.get('/traffic/overview');
  return res.data;
};

export const predictTrafficSegment = async (params) => {
  const res = await api.post('/traffic/predict', params);
  return res.data;
};

export const planJourney = async (planData) => {
  const res = await api.post('/journey/plan', planData);
  return res.data;
};

export const getAnalyticsOverview = async () => {
  const res = await api.get('/analytics/overview');
  return res.data;
};

export default api;
