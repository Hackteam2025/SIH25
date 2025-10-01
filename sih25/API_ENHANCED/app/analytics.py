"""
Analytics and statistical analysis for ARGO float data
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from .models import Profile
import numpy as np
from datetime import datetime, timedelta

class AnalyticsEngine:
    def __init__(self, db: Session):
        self.db = db

    def get_basic_statistics(self) -> Dict[str, Any]:
        """Get basic statistics for all profiles"""
        stats = self.db.query(
            func.count(Profile.id).label('total_profiles'),
            func.avg(Profile.temperature).label('avg_temperature'),
            func.avg(Profile.salinity).label('avg_salinity'),
            func.min(Profile.depth).label('min_depth'),
            func.max(Profile.depth).label('max_depth'),
            func.min(Profile.latitude).label('min_latitude'),
            func.max(Profile.latitude).label('max_latitude'),
            func.min(Profile.longitude).label('min_longitude'),
            func.max(Profile.longitude).label('max_longitude')
        ).first()

        return {
            'total_profiles': stats.total_profiles or 0,
            'avg_temperature': round(float(stats.avg_temperature or 0), 2),
            'avg_salinity': round(float(stats.avg_salinity or 0), 3),
            'depth_range': {
                'min': stats.min_depth or 0,
                'max': stats.max_depth or 0
            },
            'latitude_range': {
                'min': stats.min_latitude or 0,
                'max': stats.max_latitude or 0
            },
            'longitude_range': {
                'min': stats.min_longitude or 0,
                'max': stats.max_longitude or 0
            }
        }

    def get_depth_distribution(self) -> List[Dict[str, Any]]:
        """Get distribution of profiles by depth"""
        results = self.db.query(
            Profile.depth,
            func.count(Profile.id).label('count')
        ).group_by(Profile.depth).order_by(Profile.depth).all()

        return [
            {'depth': result.depth, 'count': result.count}
            for result in results
        ]

    def get_temperature_salinity_correlation(self) -> Dict[str, Any]:
        """Calculate temperature-salinity correlation"""
        profiles = self.db.query(Profile.temperature, Profile.salinity).all()
        
        if len(profiles) < 2:
            return {'correlation': 0, 'r_squared': 0}
        
        temps = [p.temperature for p in profiles]
        salinities = [p.salinity for p in profiles]
        
        correlation = np.corrcoef(temps, salinities)[0, 1]
        r_squared = correlation ** 2
        
        return {
            'correlation': round(float(correlation), 4),
            'r_squared': round(float(r_squared), 4)
        }

    def get_geographic_distribution(self, grid_size: float = 5.0) -> List[Dict[str, Any]]:
        """Get geographic distribution in grid cells"""
        # Round coordinates to grid cells
        results = self.db.query(
            func.round(Profile.latitude / grid_size) * grid_size,
            func.round(Profile.longitude / grid_size) * grid_size,
            func.count(Profile.id).label('count'),
            func.avg(Profile.temperature).label('avg_temp'),
            func.avg(Profile.salinity).label('avg_salinity')
        ).group_by(
            func.round(Profile.latitude / grid_size) * grid_size,
            func.round(Profile.longitude / grid_size) * grid_size
        ).all()

        return [
            {
                'latitude': float(result[0]),
                'longitude': float(result[1]),
                'count': result[2],
                'avg_temperature': round(float(result[3] or 0), 2),
                'avg_salinity': round(float(result[4] or 0), 3)
            }
            for result in results
        ]

    def get_temporal_analysis(self) -> Dict[str, Any]:
        """Analyze data by month and year"""
        monthly_stats = self.db.query(
            Profile.month,
            func.count(Profile.id).label('count'),
            func.avg(Profile.temperature).label('avg_temp'),
            func.avg(Profile.salinity).label('avg_salinity')
        ).group_by(Profile.month).order_by(Profile.month).all()

        yearly_stats = self.db.query(
            Profile.year,
            func.count(Profile.id).label('count'),
            func.avg(Profile.temperature).label('avg_temp'),
            func.avg(Profile.salinity).label('avg_salinity')
        ).group_by(Profile.year).order_by(Profile.year).all()

        return {
            'monthly': [
                {
                    'month': result.month,
                    'count': result.count,
                    'avg_temperature': round(float(result.avg_temp or 0), 2),
                    'avg_salinity': round(float(result.avg_salinity or 0), 3)
                }
                for result in monthly_stats
            ],
            'yearly': [
                {
                    'year': result.year,
                    'count': result.count,
                    'avg_temperature': round(float(result.avg_temp or 0), 2),
                    'avg_salinity': round(float(result.avg_salinity or 0), 3)
                }
                for result in yearly_stats
            ]
        }

    def get_depth_profile_analysis(self, depth_range: Optional[tuple] = None) -> Dict[str, Any]:
        """Analyze temperature and salinity profiles by depth"""
        query = self.db.query(Profile)
        
        if depth_range:
            query = query.filter(
                and_(
                    Profile.depth >= depth_range[0],
                    Profile.depth <= depth_range[1]
                )
            )
        
        profiles = query.all()
        
        if not profiles:
            return {'depths': [], 'temperatures': [], 'salinities': []}
        
        # Group by depth and calculate averages
        depth_data = {}
        for profile in profiles:
            depth = profile.depth
            if depth not in depth_data:
                depth_data[depth] = {'temps': [], 'salinities': []}
            depth_data[depth]['temps'].append(profile.temperature)
            depth_data[depth]['salinities'].append(profile.salinity)
        
        # Calculate averages for each depth
        depths = sorted(depth_data.keys())
        avg_temps = [np.mean(depth_data[d]['temps']) for d in depths]
        avg_salinities = [np.mean(depth_data[d]['salinities']) for d in depths]
        
        return {
            'depths': depths,
            'temperatures': [round(float(t), 2) for t in avg_temps],
            'salinities': [round(float(s), 3) for s in avg_salinities]
        }

    def get_outlier_analysis(self, threshold: float = 2.0) -> Dict[str, List[Dict[str, Any]]]:
        """Identify outliers in temperature and salinity data"""
        profiles = self.db.query(Profile).all()
        
        if len(profiles) < 10:
            return {'temperature_outliers': [], 'salinity_outliers': []}
        
        temps = [p.temperature for p in profiles]
        salinities = [p.salinity for p in profiles]
        
        temp_mean = np.mean(temps)
        temp_std = np.std(temps)
        salinity_mean = np.mean(salinities)
        salinity_std = np.std(salinities)
        
        temp_outliers = []
        salinity_outliers = []
        
        for profile in profiles:
            temp_z_score = abs(profile.temperature - temp_mean) / temp_std
            salinity_z_score = abs(profile.salinity - salinity_mean) / salinity_std
            
            if temp_z_score > threshold:
                temp_outliers.append({
                    'id': profile.id,
                    'latitude': profile.latitude,
                    'longitude': profile.longitude,
                    'depth': profile.depth,
                    'temperature': profile.temperature,
                    'z_score': round(float(temp_z_score), 2)
                })
            
            if salinity_z_score > threshold:
                salinity_outliers.append({
                    'id': profile.id,
                    'latitude': profile.latitude,
                    'longitude': profile.longitude,
                    'depth': profile.depth,
                    'salinity': profile.salinity,
                    'z_score': round(float(salinity_z_score), 2)
                })
        
        return {
            'temperature_outliers': temp_outliers,
            'salinity_outliers': salinity_outliers
        }

    def get_advanced_queries(self, query_type: str, **kwargs) -> Dict[str, Any]:
        """Execute advanced analytical queries"""
        if query_type == 'spatial_clustering':
            return self._spatial_clustering_analysis(**kwargs)
        elif query_type == 'anomaly_detection':
            return self._anomaly_detection(**kwargs)
        elif query_type == 'trend_analysis':
            return self._trend_analysis(**kwargs)
        else:
            return {'error': f'Unknown query type: {query_type}'}

    def _spatial_clustering_analysis(self, **kwargs) -> Dict[str, Any]:
        """Perform spatial clustering analysis"""
        # Simplified clustering - group by geographic proximity
        grid_size = kwargs.get('grid_size', 10.0)
        geographic_data = self.get_geographic_distribution(grid_size)
        
        # Find clusters (grid cells with high density)
        clusters = []
        for cell in geographic_data:
            if cell['count'] > 5:  # Threshold for cluster
                clusters.append({
                    'center_lat': cell['latitude'],
                    'center_lon': cell['longitude'],
                    'density': cell['count'],
                    'avg_temperature': cell['avg_temperature'],
                    'avg_salinity': cell['avg_salinity']
                })
        
        return {
            'clusters': clusters,
            'total_clusters': len(clusters),
            'grid_size': grid_size
        }

    def _anomaly_detection(self, **kwargs) -> Dict[str, Any]:
        """Detect anomalies in the data"""
        outlier_analysis = self.get_outlier_analysis(kwargs.get('threshold', 2.0))
        
        return {
            'temperature_anomalies': len(outlier_analysis['temperature_outliers']),
            'salinity_anomalies': len(outlier_analysis['salinity_outliers']),
            'total_anomalies': len(outlier_analysis['temperature_outliers']) + len(outlier_analysis['salinity_outliers']),
            'details': outlier_analysis
        }

    def _trend_analysis(self, **kwargs) -> Dict[str, Any]:
        """Analyze trends in the data"""
        temporal_data = self.get_temporal_analysis()
        
        # Simple trend analysis
        monthly_counts = [m['count'] for m in temporal_data['monthly']]
        monthly_temps = [m['avg_temperature'] for m in temporal_data['monthly']]
        
        # Calculate simple linear trend
        if len(monthly_counts) > 1:
            x = list(range(len(monthly_counts)))
            count_trend = np.polyfit(x, monthly_counts, 1)[0]
            temp_trend = np.polyfit(x, monthly_temps, 1)[0]
        else:
            count_trend = 0
            temp_trend = 0
        
        return {
            'monthly_count_trend': round(float(count_trend), 2),
            'monthly_temperature_trend': round(float(temp_trend), 2),
            'temporal_data': temporal_data
        }

def calculate_real_time_stats(db: Session) -> Dict[str, Any]:
    """Lightweight stats computation for real-time broadcasting.

    Returns a compact payload with total profiles and quick aggregates.
    Designed to be fast and called on an interval by realtime.data_streamer.
    """
    # Total profiles and quick aggregates
    stats_row = db.query(
        func.count(Profile.id).label('total'),
        func.avg(Profile.temperature).label('avg_temp'),
        func.avg(Profile.salinity).label('avg_salinity'),
        func.min(Profile.depth).label('min_depth'),
        func.max(Profile.depth).label('max_depth')
    ).first()

    # Build response
    payload: Dict[str, Any] = {
        'total_profiles': int(stats_row.total or 0),
        'avg_temperature': round(float(stats_row.avg_temp or 0.0), 2),
        'avg_salinity': round(float(stats_row.avg_salinity or 0.0), 3),
        'depth_range': {
            'min': float(stats_row.min_depth or 0.0),
            'max': float(stats_row.max_depth or 0.0)
        },
        'generated_at': datetime.utcnow().isoformat() + 'Z'
    }

    return payload
