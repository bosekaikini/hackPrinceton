import json
import math
from collections import defaultdict
from datetime import datetime, timedelta

# Grid configuration
GRID_SPACING = 0.001  # ~111 meters at equator
MAP_RADIUS_KM = 5  # Default radius around user location in kilometers

# Traffic score parameters
MIN_VISITS_FOR_SCORE = 1  
MAX_TRAFFIC_SCORE = 1.0  
TRAFFIC_DECAY_HOURS = 24  


class TrafficGrid:
    """Manages a grid of traffic data points"""
    
    def __init__(self, center_lat, center_lng, radius_km=MAP_RADIUS_KM, grid_spacing=GRID_SPACING):
        """
        Initialize traffic grid around a center point.
        
        Args:
            center_lat (float): Center latitude
            center_lng (float): Center longitude
            radius_km (float): Radius in kilometers
            grid_spacing (float): Grid spacing in decimal degrees
        """
        self.center_lat = center_lat
        self.center_lng = center_lng
        self.radius_km = radius_km
        self.grid_spacing = grid_spacing
        
        # Storage for grid points and their visit counts
        self.grid_data = defaultdict(lambda: {"visits": 0, "last_updated": None})
        
        # Generate grid points
        self.grid_points = self._generate_grid()
    
    def _generate_grid(self):
        """Generate grid points within radius of center"""
        # Convert radius to approximate degrees
        # 1 degree latitude ≈ 111 km
        radius_deg = self.radius_km / 111.0
        
        grid_points = []
        
        # Calculate grid bounds
        lat_min = self.center_lat - radius_deg
        lat_max = self.center_lat + radius_deg
        lng_min = self.center_lng - radius_deg
        lng_max = self.center_lng + radius_deg
        
        # Generate grid
        lat = lat_min
        while lat <= lat_max:
            lng = lng_min
            while lng <= lng_max:
                # Check if point is within radius
                if self._is_within_radius(lat, lng):
                    grid_point = (round(lat, 6), round(lng, 6))
                    grid_points.append(grid_point)
                lng += self.grid_spacing
            lat += self.grid_spacing
        
        return grid_points
    
    def _is_within_radius(self, lat, lng):
        """Check if a point is within the map radius"""
        distance = self._calculate_distance(
            self.center_lat, self.center_lng, lat, lng
        )
        return distance <= self.radius_km
    
    def _calculate_distance(self, lat1, lng1, lat2, lng2):
        """Calculate distance between two points in kilometers (Haversine)"""
        R = 6371  # Earth's radius in km
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _find_nearest_grid_point(self, lat, lng):
        """Find the nearest grid point to a location"""
        # Snap to grid
        grid_lat = round(lat / self.grid_spacing) * self.grid_spacing
        grid_lng = round(lng / self.grid_spacing) * self.grid_spacing
        grid_point = (round(grid_lat, 6), round(grid_lng, 6))
        
        # Check if this point is in our grid
        if grid_point in self.grid_points:
            return grid_point
        
        # If not, find the closest actual grid point
        min_distance = float('inf')
        nearest_point = None
        
        for point in self.grid_points:
            distance = math.sqrt((lat - point[0])**2 + (lng - point[1])**2)
            if distance < min_distance:
                min_distance = distance
                nearest_point = point
        
        return nearest_point
    
    def add_location(self, lat, lng, timestamp=None):
        """
        Add a user location to the grid.
        
        Args:
            lat (float): User latitude
            lng (float): User longitude
            timestamp (str): ISO format timestamp (optional)
        """
        # Find nearest grid point
        grid_point = self._find_nearest_grid_point(lat, lng)
        
        if grid_point:
            self.grid_data[grid_point]["visits"] += 1
            self.grid_data[grid_point]["last_updated"] = timestamp or datetime.now().isoformat()
    
    def get_traffic_score(self, lat, lng):
        """
        Get normalized traffic score for a location (0.0 to 1.0).
        
        Args:
            lat (float): Location latitude
            lng (float): Location longitude
            
        Returns:
            float: Traffic score (0.0 = no traffic, 1.0 = max traffic)
        """
        # Find nearest grid point
        grid_point = self._find_nearest_grid_point(lat, lng)
        
        if not grid_point or grid_point not in self.grid_data:
            return 0.0
        
        visits = self.grid_data[grid_point]["visits"]
        
        if visits < MIN_VISITS_FOR_SCORE:
            return 0.0
        
        # Apply time decay
        last_updated = self.grid_data[grid_point].get("last_updated")
        decay_factor = self._calculate_time_decay(last_updated)
        
        # Normalize using logarithmic scale to prevent extreme values
        # log(visits + 1) gives smooth growth
        max_visits = max(data["visits"] for data in self.grid_data.values())
        if max_visits == 0:
            return 0.0
        
        normalized_score = math.log(visits + 1) / math.log(max_visits + 1)
        
        # Apply decay and cap at MAX_TRAFFIC_SCORE
        return min(normalized_score * decay_factor, MAX_TRAFFIC_SCORE)
    
    def _calculate_time_decay(self, timestamp_str):
        """Calculate decay factor based on time since last update"""
        if not timestamp_str:
            return 1.0
        
        try:
            last_updated = datetime.fromisoformat(timestamp_str)
            hours_ago = (datetime.now() - last_updated).total_seconds() / 3600
            
            if hours_ago < TRAFFIC_DECAY_HOURS:
                return 1.0
            else:
                # Exponential decay after threshold
                decay = math.exp(-(hours_ago - TRAFFIC_DECAY_HOURS) / TRAFFIC_DECAY_HOURS)
                return max(decay, 0.1)  # Minimum 10% retention
        except:
            return 1.0
    
    def get_all_traffic_data(self):
        """
        Get all traffic data as a dictionary.
        
        Returns:
            dict: {(lat, lng): traffic_score}
        """
        traffic_data = {}
        for point in self.grid_points:
            score = self.get_traffic_score(point[0], point[1])
            if score > 0:
                traffic_data[point] = score
        
        return traffic_data
    
    def save_to_file(self, filepath='traffic_data.json'):
        """Save grid data to JSON file"""
        # Convert tuples to strings for JSON
        data = {
            "center": {"lat": self.center_lat, "lng": self.center_lng},
            "radius_km": self.radius_km,
            "grid_spacing": self.grid_spacing,
            "grid_data": {
                f"({lat},{lng})": {
                    "visits": data["visits"],
                    "last_updated": data["last_updated"]
                }
                for (lat, lng), data in self.grid_data.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath='traffic_data.json'):
        """Load grid data from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            grid = cls(
                data["center"]["lat"],
                data["center"]["lng"],
                data.get("radius_km", MAP_RADIUS_KM),
                data.get("grid_spacing", GRID_SPACING)
            )
            
            # Load grid data
            for key, value in data.get("grid_data", {}).items():
                lat, lng = map(float, key.strip('()').split(','))
                grid.grid_data[(lat, lng)] = value
            
            return grid
        except FileNotFoundError:
            return None


# Flask-compatible functions for easy integration

def process_mobile_location(lat, lng, user_center_lat, user_center_lng, timestamp=None):
    """
    Process a location ping from mobile app.
    
    Args:
        lat (float): Mobile user's latitude
        lng (float): Mobile user's longitude
        user_center_lat (float): Map center latitude
        user_center_lng (float): Map center longitude
        timestamp (str): ISO timestamp (optional)
        
    Returns:
        bool: Success status
    """
    # Load or create grid
    grid = TrafficGrid.load_from_file() or TrafficGrid(user_center_lat, user_center_lng)
    
    # Add location
    grid.add_location(lat, lng, timestamp)
    
    # Save updated grid
    grid.save_to_file()
    
    return True


def get_traffic_data_for_intensity(user_center_lat, user_center_lng):
    """
    Get traffic data in the format needed by intensity.py
    
    Args:
        user_center_lat (float): Map center latitude
        user_center_lng (float): Map center longitude
        
    Returns:
        dict: {(lat, lng): traffic_score} or None
    """
    grid = TrafficGrid.load_from_file()
    
    if not grid:
        # Create empty grid if none exists
        grid = TrafficGrid(user_center_lat, user_center_lng)
    
    return grid.get_all_traffic_data()