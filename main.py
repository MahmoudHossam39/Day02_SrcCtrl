import os
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI(title="YouTube Playlist API", version="1.0.0")


def extract_playlist_id(playlist_id: Optional[str], playlist_url: Optional[str]) -> str:
	if playlist_id:
		return playlist_id.strip()
	if not playlist_url:
		raise HTTPException(status_code=400, detail="Either 'playlist_id' or 'playlist_url' must be provided")

	parsed = urlparse(playlist_url)
	query_params = parse_qs(parsed.query)
	if "list" in query_params and query_params["list"]:
		return query_params["list"][0]

	# Support youtu.be or youtube.com/playlist/<id> patterns if present (rare)
	path_parts = [p for p in parsed.path.split("/") if p]
	if path_parts:
		candidate = path_parts[-1]
		if re.match(r"^[A-Za-z0-9_-]{10,}$", candidate):
			return candidate

	raise HTTPException(status_code=400, detail="Unable to extract playlist ID from URL. Provide a valid YouTube playlist URL or playlist ID.")


def get_env_api_key_or_param(api_key_param: Optional[str]) -> str:
	api_key = api_key_param or os.getenv("YOUTUBE_API_KEY")
	if not api_key:
		raise HTTPException(status_code=500, detail="YouTube API key not configured. Set YOUTUBE_API_KEY env var or pass 'api_key' query parameter.")
	return api_key


def fetch_all_playlist_videos(playlist_id: str, api_key: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
	base_url = "https://www.googleapis.com/youtube/v3/playlistItems"
	videos: List[Dict[str, Any]] = []
	next_page_token: Optional[str] = None
	page_count = 0

	while True:
		params = {
			"part": "snippet,contentDetails",
			"playlistId": playlist_id,
			"maxResults": 50,
			"key": api_key,
		}
		if next_page_token:
			params["pageToken"] = next_page_token

		response = requests.get(base_url, params=params, timeout=30)
		if response.status_code != 200:
			raise HTTPException(status_code=response.status_code, detail=f"YouTube API error: {response.text}")

		data = response.json()
		items = data.get("items", [])

		for item in items:
			# Prefer contentDetails.videoId when available
			video_id = (
				item.get("contentDetails", {}).get("videoId")
				or item.get("snippet", {}).get("resourceId", {}).get("videoId")
			)
			if not video_id:
				# Skip malformed entries
				continue

			snippet = item.get("snippet", {})
			videos.append(
				{
					"videoId": video_id,
					"title": snippet.get("title"),
					"description": snippet.get("description"),
					"publishedAt": snippet.get("publishedAt"),
					"position": snippet.get("position"),
					"thumbnails": snippet.get("thumbnails"),
				}
			)

		next_page_token = data.get("nextPageToken")
		page_count += 1

		if max_pages is not None and page_count >= max_pages:
			break
		if not next_page_token:
			break

	return videos


@app.get("/healthz")
async def healthz():
	return {"status": "ok"}


@app.get("/api/playlist-videos")
async def api_playlist_videos(
	playlist_id: Optional[str] = Query(None, description="YouTube playlist ID (e.g. PLxxxxxxxx)."),
	playlist_url: Optional[str] = Query(None, description="YouTube playlist URL; the 'list' parameter will be extracted."),
	limit: Optional[int] = Query(None, ge=1, description="Optional max number of videos to return; if omitted returns all."),
	api_key: Optional[str] = Query(None, description="Optional API key override; otherwise uses YOUTUBE_API_KEY env var."),
	max_pages: Optional[int] = Query(None, ge=1, description="Internal: limit number of page fetches (each up to 50). Not needed for normal use."),
):
	resolved_playlist_id = extract_playlist_id(playlist_id, playlist_url)
	resolved_api_key = get_env_api_key_or_param(api_key)

	videos = fetch_all_playlist_videos(resolved_playlist_id, resolved_api_key, max_pages=max_pages)

	if limit is not None and len(videos) > limit:
		videos = videos[:limit]

	return JSONResponse(
		status_code=200,
		content={
			"playlistId": resolved_playlist_id,
			"count": len(videos),
			"items": videos,
		},
	)


if __name__ == "__main__":
	import uvicorn
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)