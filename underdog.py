import tkinter as tk
from tkinter import scrolledtext
from googleapiclient.discovery import build
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import os

# Load API Key
load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build('youtube', 'v3', developerKey=API_KEY)

# === Logic ===
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
            part='snippet',
            type='video',
            maxResults=max_results_per_page,
            order='date',
            pageToken=next_page_token,
            publishedAfter=published_after
        )
        response = request.execute()
        items = response.get('items', [])
        all_results.extend(items)
        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return all_results

def get_video_stats_bulk(video_ids):
    stats = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        request = youtube.videos().list(part='statistics', id=','.join(batch))
        items = request.execute().get('items', [])
        for item in items:
            vid = item['id']
            stats[vid] = int(item['statistics'].get('viewCount', 0))
    return stats

def get_channel_subs_bulk(channel_ids):
    subs = {}
    unique_ids = list(set(channel_ids))
    for i in range(0, len(unique_ids), 50):
        batch = unique_ids[i:i+50]
        request = youtube.channels().list(part='statistics', id=','.join(batch))
        items = request.execute().get('items', [])
        for item in items:
            cid = item['id']
            count = item['statistics'].get('subscriberCount')
            subs[cid] = int(count) if count is not None else 0
    return subs

# === GUI Logic ===
def run_search():
    query = entry_query.get()
    max_results = int(entry_max_results.get())
    max_views = int(entry_max_views.get())
    max_subs = int(entry_max_subs.get())
    days_ago = int(entry_days.get())

    output.delete("1.0", tk.END)
    output.insert(tk.END, f"🔍 Searching '{query}'...\n")

    published_after = get_published_after(days_ago)
    videos = search_videos(query, max_total_results=max_results, published_after=published_after)

    video_ids = [v['id']['videoId'] for v in videos]
    channel_ids = [v['snippet']['channelId'] for v in videos]

    output.insert(tk.END, "📊 Fetching stats...\n")
    views = get_video_stats_bulk(video_ids)
    subs = get_channel_subs_bulk(channel_ids)

    found = 0
    for v in videos:
        vid = v['id']['videoId']
        title = v['snippet']['title']
        url = f"https://www.youtube.com/watch?v={vid}"
        vc = views.get(vid, 0)
        sc = subs.get(v['snippet']['channelId'], 0)

        if vc < max_views and sc < max_subs:
            found += 1
            output.insert(tk.END, f"\n✅ {title} ({vc} views, {sc} subs)\n{url}\n")

    output.insert(tk.END, f"\n✅ Done. Found {found} qualifying videos.\n")

# === GUI Setup ===
root = tk.Tk()
root.title("Underdog YouTube Finder")

tk.Label(root, text="Search Query:").grid(row=0, column=0)
entry_query = tk.Entry(root, width=30)
entry_query.insert(0, "day trading")
entry_query.grid(row=0, column=1)

tk.Label(root, text="Max Results:").grid(row=1, column=0)
entry_max_results = tk.Entry(root, width=10)
entry_max_results.insert(0, "150")
entry_max_results.grid(row=1, column=1)

tk.Label(root, text="Max Views:").grid(row=2, column=0)
entry_max_views = tk.Entry(root, width=10)
entry_max_views.insert(0, "100")
entry_max_views.grid(row=2, column=1)

tk.Label(root, text="Max Subscribers:").grid(row=3, column=0)
entry_max_subs = tk.Entry(root, width=10)
entry_max_subs.insert(0, "1000")
entry_max_subs.grid(row=3, column=1)

tk.Label(root, text="Posted in last (days):").grid(row=4, column=0)
entry_days = tk.Entry(root, width=10)
entry_days.insert(0, "7")
entry_days.grid(row=4, column=1)

tk.Button(root, text="Search", command=run_search).grid(row=5, column=0, columnspan=2, pady=5)

output = scrolledtext.ScrolledText(root, width=100, height=30)
output.grid(row=6, column=0, columnspan=2)

root.mainloop()
