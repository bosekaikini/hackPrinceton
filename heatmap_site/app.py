from flask import Flask, jsonify, send_from_directory, request
from location import process_mobile_location, get_traffic_data_for_intensity, TrafficGrid
import os
import requests
import json
from datetime import datetime
from bs4 import BeautifulSoup
import time
from heatmap import get_points, load_raw_points, CATEGORY_WEIGHTS

app = Flask(__name__)

# API Keys
XAI_API_KEY = "xai-5SUGe1pS0PoDzwBcEpkYU7DPAwkUxde1e3aHhYC0ovKIoF17X0Tkuy06K5zskAURmMq8eQeD0vaEDAW6"
GROQ_API_KEY = "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"
NEWS_API_KEY = "6598d8f53b3a4016be355c58de47e206"

# File to store incidents
INCIDENTS_FILE = 'incidents.json'

# Web scraping configuration
def get_news_about_issue(issue, location=None, max_articles=3):
    """
    Get news articles about specific issues with better search terms
    """
    try:
        # Map incident types to better search terms
        search_terms_map = {
            "power_out": "power outage electricity",
            "pothole": "pothole road repair infrastructure", 
            "road_closed": "road closure traffic detour",
            "noise_complaint": "noise complaint disturbance"
        }
        
        # Use mapped terms or fallback to original
        search_query = search_terms_map.get(issue, issue)
        
        print(f"=== NEWS SEARCH ===")
        print(f"Original issue: {issue}")
        print(f"Search query: {search_query}")
        print(f"Location: {location}")
        print(f"News API Key: {'Exists' if NEWS_API_KEY else 'Missing'}")
        
        # Try NewsAPI first if key is available
        if NEWS_API_KEY:
            articles = get_news_from_api(search_query, location, max_articles)
            if articles:
                print(f"Found {len(articles)} articles via NewsAPI")
                return articles
            else:
                print("No articles found via NewsAPI")
        
        # Fallback to simple web scraping
        print("Trying fallback web scraping...")
        articles = simple_news_scrape(search_query, location, max_articles)
        print(f"Found {len(articles)} articles via web scraping")
        return articles
        
    except Exception as e:
        print(f"News scraping error: {e}")
        return []

def get_news_from_api(issue, location, max_articles):
    """
    Use NewsAPI for reliable news data
    """
    try:
        url = f"https://newsapi.org/v2/everything?q={issue}&language=en&pageSize={max_articles}&apiKey={NEWS_API_KEY}"
        if location:
            url += f"&qInTitle={location}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            articles_data = response.json().get('articles', [])
            return [{
                'title': article.get('title', ''),
                'description': article.get('description', ''),
                'url': article.get('url', ''),
                'source': article.get('source', {}).get('name', ''),
                'published_at': article.get('publishedAt', '')
            } for article in articles_data[:max_articles]]
    except Exception as e:
        print(f"NewsAPI error: {e}")
    
    return []

def get_mock_news_fallback(issue, location):
    """Provide mock news data when real news isn't available"""
    mock_news = {
        "power_out": [
            {
                "title": "Local Power Grid Maintenance Scheduled",
                "description": "Utility company announces planned maintenance that may cause temporary outages.",
                "source": "Local News",
                "url": "#"
            }
        ],
        "pothole": [
            {
                "title": "City Announces Road Repair Initiative", 
                "description": "Municipal government launches new program to address pothole complaints.",
                "source": "City Updates",
                "url": "#"
            }
        ]
    }
    return mock_news.get(issue, [])

def simple_news_scrape(issue, location, max_articles):
    """
    Simple web scraping fallback (use with caution)
    """
    try:
        # This is a basic example - consider using a proper API instead
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Example search (be respectful of terms of service)
        search_url = f"https://news.google.com/search?q={issue}%20{location if location else ''}"
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        articles = []
        for article in soup.find_all('article')[:max_articles]:
            title_elem = article.find('h3') or article.find('h4')
            if title_elem:
                title = title_elem.get_text().strip()
                link = title_elem.find_parent('a')
                url = "https://news.google.com" + link.get('href')[1:] if link and link.get('href') else ""
                
                articles.append({
                    'title': title,
                    'url': url,
                    'source': 'Google News',
                    'description': 'Click to read full article'
                })
        
        return articles
    except Exception as e:
        print(f"Web scraping error: {e}")
        return []

def call_ai_api(prompt, api_type="xai"):
    """Unified function to call AI APIs"""
    if api_type == "xai" and XAI_API_KEY:
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are Grok, a helpful AI assistant analyzing city incident data."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "grok-beta",
            "temperature": 0.7
        }
    elif api_type == "groq" and GROQ_API_KEY:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a helpful AI assistant analyzing city incident data."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "max_tokens": 1000
        }
    else:
        return None
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"{api_type.upper()} API error: {e}")
        return None

def get_ai_analysis(prompt):
    """Get analysis from available AI APIs with fallback"""
    analysis = call_ai_api(prompt, "xai")
    api_used = "xAI (Grok)"
    
    if not analysis:
        analysis = call_ai_api(prompt, "groq")
        api_used = "Groq"
    
    return analysis, api_used

def get_incident_statistics(features=None):
    """Calculate statistics from incident data"""
    if features is None:
        all_data = get_points()
        features = all_data.get('features', [])
    
    category_counts = {}
    time_distribution = {}
    total_intensity = 0
    
    for feature in features:
        props = feature['properties']
        cat = props.get('category', 'unknown')
        time = props.get('time', 'unknown')
        intensity = props.get('intensity', 0)
        
        category_counts[cat] = category_counts.get(cat, 0) + 1
        total_intensity += intensity
        
        if time and ':' in time:
            hour = time.split()[1].split(':')[0] if ' ' in time else time.split(':')[0]
            time_distribution[hour] = time_distribution.get(hour, 0) + 1
    
    return {
        'total_incidents': len(features),
        'by_category': category_counts,
        'average_intensity': total_intensity / len(features) if features else 0,
        'time_distribution': time_distribution
    }

def create_incident_prompt(incident, category_counts, news_articles=None):
    """Create prompt for single incident analysis with news context"""
    
    news_context = ""
    if news_articles:
        news_context = "\n\nRecent News Context:\n"
        for i, article in enumerate(news_articles, 1):
            news_context += f"{i}. {article['title']}\n"
            if article.get('description'):
                news_context += f"   Summary: {article['description'][:200]}...\n"
            if article.get('source'):
                news_context += f"   Source: {article['source']}\n"
            news_context += "\n"

    return f"""You are analyzing incident data for a city monitoring system. 

Current Incident:
- Type: {incident.get('category', 'Unknown')}
- Time: {incident.get('time', 'Unknown')}
- Location: Lat {incident.get('lat')}, Lng {incident.get('lng')} ({incident.get('area', 'Princeton, NJ area')})
- Intensity: {incident.get('intensity', 'Unknown')}

Context - Total incidents in the area:
{category_counts}
{news_context}

Please provide:
1. A brief explanation of what this incident means
2. Its potential impact on the local area
3. Any patterns or concerns based on the frequency of this type of incident
4. Recent news context about similar issues (if available)
5. Recommended actions or precautions for residents

Keep your response concise (1-2 paragraphs) and focused on practical information."""

def create_area_analysis_prompt(statistics):
    """Create prompt for area analysis"""
    return f"""You are analyzing city incident data for an area monitoring system.

Dataset Overview:
- Total incidents: {statistics['total_incidents']}
- Incident types and counts: {statistics['by_category']}
- Average intensity: {statistics['average_intensity']:.2f}
- Time distribution (by hour): {statistics['time_distribution']}

Please provide:
1. An overview of the most significant patterns or concerns
2. Assessment of the area's safety and infrastructure status
3. Comparisons between different incident types
4. Time-based patterns (if any)
5. Recommendations for city officials or residents

Keep your response informative but concise (3-4 paragraphs)."""

def load_incidents():
    """Load incidents from JSON file"""
    try:
        with open(INCIDENTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_incident(incident):
    """Save a new incident to the JSON file"""
    incidents = load_incidents()
    incidents.append(incident)
    
    with open(INCIDENTS_FILE, 'w') as f:
        json.dump(incidents, f, indent=2)
    
    return True

def get_all_incidents_as_features():
    """Get all incidents in the heatmap format"""
    incidents = load_incidents()
    features = []
    
    for incident in incidents:
        intensity = CATEGORY_WEIGHTS.get(incident.get('category', 'unknown'), 6)
        
        features.append({
            "type": "Feature",
            "properties": {
                "category": incident.get('category', 'unknown'),
                "time": incident.get('time', ''),
                "intensity": intensity
            },
            "geometry": {
                "type": "Point",
                "coordinates": [incident.get('lng', 0), incident.get('lat', 0)]
            }
        })
    
    return features

# === ADD THESE BASIC ROUTES ===

@app.route("/")
def index():
    """Serve the main HTML page"""
    return send_from_directory(".", "index.html")

@app.route("/index.css")
def css():
    """Serve the CSS file"""
    return send_from_directory(".", "index.css")

@app.route("/data")
def data():
    """Serve heatmap data - combine static and Android incidents"""
    static_data = get_points()
    android_incidents = get_all_incidents_as_features()
    
    # Merge both data sources
    all_features = static_data['features'] + android_incidents
    
    return jsonify({
        "type": "FeatureCollection",
        "features": all_features
    })

@app.route('/analyze-area', methods=['POST'])
def analyze_area():
    """
    Analyze all incidents in a specific area or overall trends
    """
    try:
        bounds = request.json.get('bounds') if request.json else None
        all_data = get_points()
        features = all_data.get('features', [])
        
        # Include Android incidents
        android_features = get_all_incidents_as_features()
        all_features = features + android_features
        
        # Filter by bounds if provided
        if bounds:
            all_features = [
                f for f in all_features 
                if (bounds['south'] <= f['geometry']['coordinates'][1] <= bounds['north'] and 
                    bounds['west'] <= f['geometry']['coordinates'][0] <= bounds['east'])
            ]
        
        stats = get_incident_statistics(all_features)
        prompt = create_area_analysis_prompt(stats)
        analysis, api_used = get_ai_analysis(prompt)
        
        if not analysis:
            return jsonify({
                "success": False,
                "error": "No API keys configured or both APIs failed"
            }), 500
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "statistics": stats,
            "api_used": api_used
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/android/traffic-data", methods=["GET"])
def get_traffic_data_for_android():
    """
    Get current traffic data for Android app visualization
    Query parameters: user_center_lat, user_center_lng
    """
    try:
        user_center_lat = float(request.args.get('user_center_lat', 40.343))
        user_center_lng = float(request.args.get('user_center_lng', -74.660))
        
        traffic_data = get_traffic_data_for_intensity(user_center_lat, user_center_lng)
        
        return jsonify({
            "success": True,
            "traffic_data": traffic_data,
            "center": {"lat": user_center_lat, "lng": user_center_lng}
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# === END OF ADDED ROUTES ===

# Android App Integration Routes
@app.route("/android/location", methods=["POST"])
def receive_android_location():
    """Receive location data from Android app for traffic grid"""
    try:
        data = request.json
        
        required_fields = ['lat', 'lng', 'user_center_lat', 'user_center_lng']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        success = process_mobile_location(
            lat=data['lat'],
            lng=data['lng'],
            user_center_lat=data['user_center_lat'],
            user_center_lng=data['user_center_lng'],
            timestamp=data.get('timestamp')
        )
        
        return jsonify({
            "success": success,
            "message": "Location data processed successfully",
            "received_data": data
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/android/incident", methods=["POST"])
def receive_android_incident():
    """Receive incident report from Android app"""
    try:
        data = request.json
        
        required_fields = ['lat', 'lng', 'category', 'user_center_lat', 'user_center_lng']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "error": f"Missing required field: {field}"
                }), 400
        
        incident = {
            "lat": data['lat'],
            "lng": data['lng'],
            "category": data['category'],
            "description": data.get('description', ''),
            "time": data.get('timestamp') or datetime.now().isoformat(),
            "area": "User Reported Area",
            "intensity": CATEGORY_WEIGHTS.get(data['category'], 6),
            "source": "android_app"
        }
        
        save_incident(incident)
        
        process_mobile_location(
            lat=data['lat'],
            lng=data['lng'],
            user_center_lat=data['user_center_lat'],
            user_center_lng=data['user_center_lng'],
            timestamp=data.get('timestamp')
        )
        
        return jsonify({
            "success": True,
            "message": "Incident reported successfully",
            "incident_id": len(load_incidents()),
            "received_data": incident
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Updated analysis route with web scraping
@app.route('/analyze', methods=['POST'])
def analyze_data():
    """
    Analyze incident data using AI APIs with news context
    """
    try:
        incident = request.json
        stats = get_incident_statistics()
        
        # Get relevant news articles
        news_articles = get_news_about_issue(
            issue=incident.get('category', ''),
            location=incident.get('area', 'Princeton, NJ'),
            max_articles=3
        )
        
        prompt = create_incident_prompt(incident, stats['by_category'], news_articles)
        analysis, api_used = get_ai_analysis(prompt)
        
        if not analysis:
            return jsonify({
                "success": False,
                "error": "No API keys configured or both APIs failed"
            }), 500
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "incident": incident,
            "context": stats['by_category'],
            "news_articles": news_articles,  # Include in response
            "api_used": api_used
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ... (keep all the other routes the same)

if __name__ == "__main__":
    if not os.path.exists(INCIDENTS_FILE):
        with open(INCIDENTS_FILE, 'w') as f:
            json.dump([], f)
    
    app.run(debug=True, host='0.0.0.0', port=5000)  # Allow external connections