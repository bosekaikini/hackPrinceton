from intensity import calculate_all_intensities, load_traffic_data
from location import get_traffic_data_for_intensity

CATEGORY_WEIGHTS = {
    "pothole": 5,
    "power_out": 12,
    "road_closed": 8,
    "noise_complaint": 4,
}

def load_raw_points():
    """
    Returns a list of incident reports with latitudes and longitudes
    clustered around Princeton, NJ (approx. 40.34 N, 74.66 W).
    """
    return [
        # Center of Campus Area
        {"lat": 40.343, "lng": -74.660, "category": "pothole",      "time": "2025-01-01 12:00"},
        # Slightly north/west of campus
        {"lat": 40.350, "lng": -74.665, "category": "power_out",    "time": "2025-01-01 13:00"},
        # Near Nassau Street/downtown
        {"lat": 40.340, "lng": -74.655, "category": "road_closed",  "time": "2025-01-01 14:00"},
        # East side of campus
        {"lat": 40.335, "lng": -74.650, "category": "noise_complaint", "time": "2025-01-01 15:00"},
    ]


def category_to_intensity(category):
    # Default size if category unknown
    return CATEGORY_WEIGHTS.get(category, 6)


def get_points():
    raw = load_raw_points()

    features = []

    for entry in raw:
        intensity = category_to_intensity(entry["category"])

        features.append({
            "type": "Feature",
            "properties": {
                "category": entry["category"],
                "time": entry["time"],
                "intensity": intensity
            },
            "geometry": {
                "type": "Point",
                "coordinates": [entry["lng"], entry["lat"]]
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
