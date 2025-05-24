import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
import os

# Load API key from Streamlit secrets
API_KEY = st.secrets["YOUTUBE_API_KEY"]
youtube = build("youtube", "v3", developerKey=API_KEY)


# === Core Functions ===
def get_published_after(days_ago):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat().replace("+00:00", "Z")

def search_videos(query, max_total_results, published_after):
    all_results = []
    next_page_token = None
    while len(all_results) < max_total_results:
        max_results_per_page = min(50, max_total_results - len(all_results))
        request = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=max_results_per_page,
            order="date",
            pageToken=next_page_token,
            publishedAfter=published_after
        )
        response = request.execute()
        items = response.get("items", [])
        all_results.extend(items)
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
    return all_results

def get_video_stats_bulk(video_ids):
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        request = youtube.videos().list(part="statistics", id=",".join(batch))
        items = request.execute().get("items", [])
        for item in items:
            vid = item["id"]
            stats[vid] = int(item["statistics"].get("viewCount", 0))
    return stats

def get_channel_subs_bulk(channel_ids):
    subs = {}
    unique_ids = list(set(channel_ids))
    for i in range(0, len(unique_ids), 50):
        batch = unique_ids[i:i+50]
        request = youtube.channels().list(part="statistics", id=",".join(batch))
        items = request.execute().get("items", [])
        for item in items:
            cid = item["id"]
            count = item["statistics"].get("subscriberCount")
            subs[cid] = int(count) if count is not None else 0
    return subs

# === Streamlit UI ===
st.set_page_config(page_title="Underdog YouTube Finder", layout="wide")
st.title("🎯 Underdog YouTube Video Finder")

with st.sidebar:
    st.header("Search Parameters")
    query = st.text_input("Search Query", "day trading")
    max_results = st.number_input("Max Results", min_value=10, max_value=500, value=150, step=10)
    max_views = st.number_input("Max Views", min_value=0, value=100)
    max_subs = st.number_input("Max Subscribers", min_value=0, value=1000)
    days_ago = st.number_input("Posted in Last X Days", min_value=1, value=7)
    start = st.button("Search")

if start:
    st.info(f"Searching for '{query}' from the last {days_ago} days...")

    published_after = get_published_after(days_ago)
    videos = search_videos(query, max_total_results=max_results, published_after=published_after)

    video_ids = [v["id"]["videoId"] for v in videos]
    channel_ids = [v["snippet"]["channelId"] for v in videos]

    with st.spinner("Fetching video view counts..."):
        views = get_video_stats_bulk(video_ids)

    with st.spinner("Fetching channel subscriber counts..."):
        subs = get_channel_subs_bulk(channel_ids)

    results = []
    for v in videos:
        vid = v["id"]["videoId"]
        title = v["snippet"]["title"]
        url = f"https://www.youtube.com/watch?v={vid}"
        vc = views.get(vid, 0)
        sc = subs.get(v["snippet"]["channelId"], 0)

        if vc < max_views and sc < max_subs:
            results.append((title, url, vc, sc, vid))

    if results:
        st.success(f"Found {len(results)} qualifying videos.")
        for title, url, vc, sc, vid in results:
            col1, col2 = st.columns([1, 5])
            with col1:
                thumbnail_url = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                st.image(thumbnail_url, use_container_width=True)
            with col2:
                st.markdown(f"**{title}**")
                st.markdown(f"📺 {vc} views | 👤 {sc} subs")
                st.markdown(f"[🔗 Watch on YouTube]({url})\n")
    else:
        st.warning("No results found with the given filters.")
