"""
Real-time data streaming and live updates module
"""
import asyncio
import json
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timedelta
import logging
from .crud import get_recent_profiles
from .db import get_db

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            'data_updates': set(),
            'chat': set(),
            'analytics': set(),
            'alerts': set()
        }
        self.user_preferences: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket, channel: str, user_id: str = None):
        """Connect a client to a specific channel"""
        await websocket.accept()
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        self.active_connections[channel].add(websocket)
        
        if user_id:
            self.user_preferences[user_id] = {
                'websocket': websocket,
                'channels': [channel],
                'last_seen': datetime.now()
            }
        
        logger.info(f"Client connected to {channel}. Total connections: {len(self.active_connections[channel])}")
    
    def disconnect(self, websocket: WebSocket, channel: str, user_id: str = None):
        """Disconnect a client from a channel"""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
        
        if user_id and user_id in self.user_preferences:
            del self.user_preferences[user_id]
        
        logger.info(f"Client disconnected from {channel}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific client"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_channel(self, message: str, channel: str):
        """Broadcast a message to all clients in a channel"""
        if channel not in self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections[channel]:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {channel}: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections[channel].discard(connection)
    
    async def send_data_update(self, data: Dict, filters: Dict = None):
        """Send real-time data updates to subscribed clients"""
        message = json.dumps({
            'type': 'data_update',
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'filters': filters
        })
        await self.broadcast_to_channel(message, 'data_updates')
    
    async def send_analytics_update(self, analytics: Dict):
        """Send real-time analytics updates"""
        message = json.dumps({
            'type': 'analytics_update',
            'timestamp': datetime.now().isoformat(),
            'analytics': analytics
        })
        await self.broadcast_to_channel(message, 'analytics')
    
    async def send_alert(self, alert: Dict):
        """Send system alerts"""
        message = json.dumps({
            'type': 'alert',
            'timestamp': datetime.now().isoformat(),
            'alert': alert
        })
        await self.broadcast_to_channel(message, 'alerts')

# Global connection manager instance
manager = ConnectionManager()

class DataStreamer:
    """Handles real-time data streaming"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
        self.streaming = False
        self.stream_interval = 30  # seconds
    
    async def start_streaming(self):
        """Start the data streaming service"""
        self.streaming = True
        logger.info("Data streaming service started")
        
        while self.streaming:
            try:
                # Get recent data updates
                db = next(get_db())
                recent_profiles = get_recent_profiles(db, hours=1)
                
                if recent_profiles:
                    await self.manager.send_data_update({
                        'new_profiles': len(recent_profiles),
                        'latest_data': [
                            {
                                'id': p.id,
                                'latitude': float(p.latitude),
                                'longitude': float(p.longitude),
                                'temperature': float(p.temperature),
                                'salinity': float(p.salinity),
                                'depth': float(p.depth),
                                'timestamp': p.created_at.isoformat() if hasattr(p, 'created_at') else None
                            }
                            for p in recent_profiles[:10]  # Send latest 10
                        ]
                    })
                
                # Send analytics updates
                await self.send_analytics_updates(db)
                
                await asyncio.sleep(self.stream_interval)
                
            except Exception as e:
                logger.error(f"Error in data streaming: {e}")
                await asyncio.sleep(self.stream_interval)
    
    async def send_analytics_updates(self, db):
        """Send real-time analytics updates"""
        try:
            # Calculate real-time statistics
            from .analytics import calculate_real_time_stats
            stats = calculate_real_time_stats(db)
            
            await self.manager.send_analytics_update(stats)
            
        except Exception as e:
            logger.error(f"Error sending analytics updates: {e}")
    
    def stop_streaming(self):
        """Stop the data streaming service"""
        self.streaming = False
        logger.info("Data streaming service stopped")

# Global data streamer instance
data_streamer = DataStreamer(manager)

class AlertSystem:
    """Handles real-time alerts and notifications"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
        self.alert_thresholds = {
            'temperature_anomaly': {'min': -2, 'max': 35},
            'salinity_anomaly': {'min': 30, 'max': 40},
            'depth_anomaly': {'max': 6000},
            'data_quality': {'min_confidence': 0.8}
        }
    
    async def check_anomalies(self, profile_data: Dict):
        """Check for data anomalies and send alerts"""
        alerts = []
        
        # Temperature anomaly check
        temp = profile_data.get('temperature')
        if temp and (temp < self.alert_thresholds['temperature_anomaly']['min'] or 
                    temp > self.alert_thresholds['temperature_anomaly']['max']):
            alerts.append({
                'type': 'temperature_anomaly',
                'severity': 'high',
                'message': f"Temperature anomaly detected: {temp}°C",
                'data': profile_data
            })
        
        # Salinity anomaly check
        salinity = profile_data.get('salinity')
        if salinity and (salinity < self.alert_thresholds['salinity_anomaly']['min'] or 
                        salinity > self.alert_thresholds['salinity_anomaly']['max']):
            alerts.append({
                'type': 'salinity_anomaly',
                'severity': 'medium',
                'message': f"Salinity anomaly detected: {salinity} PSU",
                'data': profile_data
            })
        
        # Send alerts
        for alert in alerts:
            await self.manager.send_alert(alert)
    
    async def send_system_alert(self, message: str, severity: str = 'info'):
        """Send system-wide alerts"""
        alert = {
            'type': 'system',
            'severity': severity,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        await self.manager.send_alert(alert)

# Global alert system instance
alert_system = AlertSystem(manager)
