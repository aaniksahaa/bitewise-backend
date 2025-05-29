import os
import requests
from app.core.config import settings

# Test the YouTube search functionality
def test_youtube_search():
    """Test YouTube API search functionality."""
    
    # Check if API key is available
    if not settings.YOUTUBE_V3_API_KEY:
        print("❌ YOUTUBE_V3_API_KEY not found in environment variables")
        return False
    
    # Test search parameters
    query = "cooking sorshe ilish"
    url = "https://youtube-v311.p.rapidapi.com/search/"
    
    querystring = {
        "part": "snippet",
        "maxResults": "5",
        "order": "relevance",
        "q": query,
        "safeSearch": "moderate",
        "type": "video",
        "videoDuration": "medium",
        "videoEmbeddable": "true"
    }
    
    headers = {
        "x-rapidapi-key": settings.YOUTUBE_V3_API_KEY,
        "x-rapidapi-host": "youtube-v311.p.rapidapi.com"
    }
    
    try:
        print(f"🔍 Testing YouTube search for: '{query}'")
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API call successful! Status: {response.status_code}")
            
            if "items" in data and len(data["items"]) > 0:
                print(f"📹 Found {len(data['items'])} videos:")
                for i, item in enumerate(data["items"][:3], 1):  # Show first 3
                    snippet = item.get("snippet", {})
                    title = snippet.get("title", "No title")
                    channel = snippet.get("channelTitle", "Unknown channel")
                    video_id = item.get("id", {}).get("videoId", "")
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    print(f"  {i}. {title}")
                    print(f"     Channel: {channel}")
                    print(f"     URL: {video_url}")
                    print()
                
                return True
            else:
                print("⚠️ No videos found in response")
                return False
        else:
            print(f"❌ API call failed! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timeout - API took too long to respond")
        return False
    except Exception as e:
        print(f"❌ Error during API call: {str(e)}")
        return False

if __name__ == "__main__":
    test_youtube_search() 