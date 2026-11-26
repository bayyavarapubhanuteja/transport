"""SQLAlchemy Database Models for DelhiMove AI.
Matches GTFS specifications and real-time vehicle/traffic models.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Index, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Stop(Base):
    __tablename__ = "stops"

    stop_id = Column(Integer, primary_key=True)
    stop_code = Column(String(50), index=True)
    stop_name = Column(String(255), nullable=False, index=True)
    stop_lat = Column(Float, nullable=False)
    stop_lon = Column(Float, nullable=False)

    # Relationships
    stop_times = relationship("StopTime", back_populates="stop", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_stops_lat_lon", "stop_lat", "stop_lon"),
    )

    def to_dict(self):
        return {
            "stop_id": self.stop_id,
            "stop_code": self.stop_code,
            "stop_name": self.stop_name,
            "stop_lat": self.stop_lat,
            "stop_lon": self.stop_lon
        }

class Route(Base):
    __tablename__ = "routes"

    route_id = Column(Integer, primary_key=True)
    agency_id = Column(String(50), index=True)
    route_short_name = Column(String(100), nullable=False, index=True)
    route_long_name = Column(String(255), nullable=False)
    route_desc = Column(Text)
    route_type = Column(Integer, default=3)  # 3 = Bus

    # Relationships
    trips = relationship("Trip", back_populates="route", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "route_id": self.route_id,
            "agency_id": self.agency_id,
            "route_short_name": self.route_short_name,
            "route_long_name": self.route_long_name,
            "route_desc": self.route_desc,
            "route_type": self.route_type
        }

class Trip(Base):
    __tablename__ = "trips"

    trip_id = Column(String(100), primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=False, index=True)
    service_id = Column(Integer, index=True)
    trip_headsign = Column(String(255))
    shape_id = Column(String(100), index=True)
    direction_id = Column(Integer, default=0)

    # Relationships
    route = relationship("Route", back_populates="trips")
    stop_times = relationship("StopTime", back_populates="trip", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "service_id": self.service_id,
            "trip_headsign": self.trip_headsign,
            "shape_id": self.shape_id,
            "direction_id": self.direction_id
        }

class StopTime(Base):
    __tablename__ = "stop_times"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(String(100), ForeignKey("trips.trip_id"), nullable=False, index=True)
    stop_id = Column(Integer, ForeignKey("stops.stop_id"), nullable=False, index=True)
    stop_sequence = Column(Integer, nullable=False)
    arrival_time = Column(String(20), nullable=False)
    departure_time = Column(String(20), nullable=False)
    stop_dist = Column(Float)

    # Relationships
    trip = relationship("Trip", back_populates="stop_times")
    stop = relationship("Stop", back_populates="stop_times")

    __table_args__ = (
        Index("idx_trip_sequence", "trip_id", "stop_sequence"),
    )

    def to_dict(self):
        return {
            "trip_id": self.trip_id,
            "stop_id": self.stop_id,
            "stop_sequence": self.stop_sequence,
            "arrival_time": self.arrival_time,
            "departure_time": self.departure_time,
            "stop_dist": self.stop_dist
        }

class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(String(50), primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.route_id"), nullable=True, index=True)
    trip_id = Column(String(100), nullable=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    speed = Column(Float, default=0.0)
    congestion_level = Column(String(20), default="low")  # low, moderate, high
    last_updated = Column(DateTime, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "vehicle_id": self.vehicle_id,
            "route_id": self.route_id,
            "trip_id": self.trip_id,
            "lat": self.lat,
            "lon": self.lon,
            "speed": self.speed,
            "congestion_level": self.congestion_level,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "is_active": self.is_active
        }

class GpsObservation(Base):
    __tablename__ = "gps_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(String(50), index=True)
    route_id = Column(Integer, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    speed = Column(Float)
    timestamp = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index("idx_gps_veh_time", "vehicle_id", "timestamp"),
    )

class TrafficSegment(Base):
    __tablename__ = "traffic_segments"

    segment_id = Column(String(100), primary_key=True)  # e.g. "stopA_stopB"
    from_stop_id = Column(Integer, ForeignKey("stops.stop_id"), nullable=False, index=True)
    to_stop_id = Column(Integer, ForeignKey("stops.stop_id"), nullable=False, index=True)
    distance_m = Column(Float, nullable=False)
    historical_avg_speed = Column(Float, default=18.0)  # km/h
    current_speed = Column(Float, default=18.0)         # km/h
    congestion_level = Column(String(20), default="low") # low (green), moderate (yellow), high (red)
    last_updated = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "segment_id": self.segment_id,
            "from_stop_id": self.from_stop_id,
            "to_stop_id": self.to_stop_id,
            "distance_m": self.distance_m,
            "historical_avg_speed": self.historical_avg_speed,
            "current_speed": self.current_speed,
            "congestion_level": self.congestion_level,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }

class PredictionHistory(Base):
    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_stop = Column(String(255), nullable=False)
    dest_stop = Column(String(255), nullable=False)
    departure_time = Column(String(20), nullable=False)
    predicted_duration_min = Column(Float, nullable=False)
    baseline_duration_min = Column(Float, nullable=False)
    confidence = Column(String(20), default="high")
    created_at = Column(DateTime, default=datetime.utcnow)
