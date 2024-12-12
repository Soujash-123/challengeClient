import requests
from bs4 import BeautifulSoup

def get_first_youtube_video(search_query):
    # Construct the YouTube search URL
    base_url = "https://www.youtube.com/results"
    params = {"search_query": search_query}

    # Send the GET request
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        # Parse the HTML content
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the first video link
        video_tag = soup.find("a", {"href": True, "aria-label": True})
        if video_tag and video_tag["href"].startswith("/watch"):
            video_url = f"https://www.youtube.com{video_tag['href']}"
            return video_url
    return "No video found"

if __name__ == "__main__":
    search_query = "Water cycle"
    first_video_url = get_first_youtube_video(search_query)
    print(f"First video URL: {first_video_url}")
