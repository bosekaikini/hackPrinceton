import math
from collections import defaultdict

# Base severity weights for different incident types (scale: 1-10)
SEVERITY_WEIGHTS = {
    "Road Issues": 7,
    "Damaged Road issues (Road cracks)": 7,
    "Pothole Issues": 7,
    "Illegal Parking Issues": 4,
    "Broken Road Sign Issues": 3,
    "Fallen trees": 7,
    "Littering/Garbage on Public Places": 3,
    "Graffiti": 4,
    "Dead Animal Pollution": 7,
    "Damaged concrete structures": 6,
    "Damaged Electric wires and poles": 6,
    "unknown": 5
}

FREQUENCY_BASE_BOOST = 0.5
FREQUENCY_MAX_BOOST = 2.0
FREQUENCY_DECAY = 0.3

TRAFFIC_MIN_MULTIPLIER = 1.0  # Low traffic areas
TRAFFIC_MAX_MULTIPLIER = 1.5  # High traffic areas

# Location proximity threshold (in decimal degrees, ~100 meters)
LOCATION_PROXIMITY_THRESHOLD = 0.001


def get_base_severity(category):
    """
    Get the base severity weight for an incident category.
    
    Args:
        category (str): The incident category
        
    Returns:
        float: Base severity weight (1-10)
    """
    return SEVERITY_WEIGHTS.get(category.lower(), SEVERITY_WEIGHTS["unknown"])


def get_pedestrian_traffic_multiplier(lat, lng, traffic_data=None):
    """
    Get the pedestrian traffic multiplier for a location.
    
    Args:
        lat (float): Latitude
        lng (float): Longitude
        traffic_data (dict): Dictionary mapping locations to traffic levels
                            Format: {(lat, lng): traffic_level}
                            traffic_level should be 0.0 to 1.0
                            
    Returns:
        float: Traffic multiplier (1.0 to 1.5)
    """
    if traffic_data is None:
        return 1.0  # No traffic data, use neutral multiplier
    
    # Find the closest traffic data point
    min_distance = float('inf')
    closest_traffic = 0.5  # Default medium traffic
    
    for (traffic_lat, traffic_lng), traffic_level in traffic_data.items():
        distance = math.sqrt((lat - traffic_lat)**2 + (lng - traffic_lng)**2)
        if distance < min_distance:
            min_distance = distance
            closest_traffic = traffic_level
    
    # Convert traffic level (0-1) to multiplier (1.0-1.5)
    multiplier = TRAFFIC_MIN_MULTIPLIER + (closest_traffic * (TRAFFIC_MAX_MULTIPLIER - TRAFFIC_MIN_MULTIPLIER))
    return multiplier


def calculate_frequency_boost(incidents, current_lat, current_lng, current_category):
    """
    Calculate frequency boost based on duplicate reports at similar locations.
    
    Args:
        incidents (list): List of all incident dictionaries
        current_lat (float): Current incident latitude
        current_lng (float): Current incident longitude
        current_category (str): Current incident category
        
    Returns:
        float: Frequency boost value (0 to FREQUENCY_MAX_BOOST)
    """
    duplicate_count = 0
    
    for incident in incidents:
        # Check if it's a different incident (not the current one)
        incident_lat = incident.get('lat')
        incident_lng = incident.get('lng')
        incident_category = incident.get('category')
        
        if incident_lat is None or incident_lng is None:
            continue
            
        # Calculate distance
        distance = math.sqrt((current_lat - incident_lat)**2 + (current_lng - incident_lng)**2)
        
        # Check if it's at the same location and same category
        if (distance < LOCATION_PROXIMITY_THRESHOLD and 
            incident_category == current_category and
            not (incident_lat == current_lat and incident_lng == current_lng)):
            duplicate_count += 1
    
    # Calculate boost with diminishing returns
    if duplicate_count == 0:
        return 0.0
    
    boost = 0.0
    for i in range(duplicate_count):
        boost += FREQUENCY_BASE_BOOST * (FREQUENCY_DECAY ** i)
    
    # Cap at maximum boost
    return min(boost, FREQUENCY_MAX_BOOST)


def calculate_intensity(category, lat, lng, all_incidents, traffic_data=None):
    """
    Calculate the final intensity for an incident based on severity, 
    pedestrian traffic, and frequency.
    
    Args:
        category (str): Incident category
        lat (float): Latitude
        lng (float): Longitude
        all_incidents (list): List of all incidents for frequency calculation
        traffic_data (dict): Optional pedestrian traffic data
        
    Returns:
        float: Final intensity value (typically 1-15)
    """
    # 1. Base severity
    base_severity = get_base_severity(category)
    
    # 2. Pedestrian traffic multiplier
    traffic_multiplier = get_pedestrian_traffic_multiplier(lat, lng, traffic_data)
    
    # 3. Frequency boost
    frequency_boost = calculate_frequency_boost(all_incidents, lat, lng, category)
    
    # Calculate final intensity
    intensity = (base_severity * traffic_multiplier) + frequency_boost
    
    # Round to 1 decimal place for cleaner display
    return round(intensity, 1)


def calculate_all_intensities(incidents, traffic_data=None):
    """
    Calculate intensity for all incidents in a list.
    This is the main function you'll call from heatmap.py
    
    Args:
        incidents (list): List of incident dictionaries with keys:
                         'category', 'lat', 'lng'
        traffic_data (dict): Optional pedestrian traffic data
                            Format: {(lat, lng): traffic_level (0.0-1.0)}
        
    Returns:
        dict: Dictionary mapping incident index to intensity
              Format: {0: 8.5, 1: 3.2, 2: 10.0, ...}
    """
    intensities = {}
    
    for idx, incident in enumerate(incidents):
        intensity = calculate_intensity(
            incident.get('category', 'unknown'),
            incident.get('lat'),
            incident.get('lng'),
            incidents,
            traffic_data
        )
        intensities[idx] = intensity
    
    return intensities


def load_traffic_data(filepath='traffic_data.json'):
    """
    Load pedestrian traffic data from a file.
    
    Args:
        filepath (str): Path to traffic data JSON file
        
    Returns:
        dict: Traffic data or None if file doesn't exist
    """
    try:
        import json
        with open(filepath, 'r') as f:
            raw_data = json.load(f)
        
        # Convert string keys back to tuples
        traffic_data = {}
        for key, value in raw_data.items():
            lat, lng = map(float, key.strip('()').split(','))
            traffic_data[(lat, lng)] = value
        
        return traffic_data
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading traffic data: {e}")
        return None