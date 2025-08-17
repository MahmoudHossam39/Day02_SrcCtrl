# YouTube Playlist API (FastAPI)

A minimal FastAPI service that returns all videos in a YouTube playlist, handling pagination with the YouTube Data API v3.

## Setup

1. Create a YouTube Data API v3 API key from Google Cloud Console.
2. Set the environment variable `YOUTUBE_API_KEY` to your key, or pass `api_key` as a query parameter when calling the endpoint.

```bash
export YOUTUBE_API_KEY=YOUR_API_KEY
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- GET `/api/playlist-videos`
  - Query params:
    - `playlist_id` (optional): YouTube playlist ID (e.g. `PL...`).
    - `playlist_url` (optional): YouTube playlist URL; service extracts the `list` parameter.
    - `limit` (optional): Limit total number of returned videos (for convenience).
    - `api_key` (optional): Override the API key via query param; otherwise uses `YOUTUBE_API_KEY`.

Exactly one of `playlist_id` or `playlist_url` must be provided.

## Examples

- By playlist ID:

```bash
curl "http://localhost:8000/api/playlist-videos?playlist_id=PLBCF2DAC6FFB574DE"
```

- By playlist URL:

```bash
curl --get "http://localhost:8000/api/playlist-videos" \
  --data-urlencode "playlist_url=https://www.youtube.com/playlist?list=PLBCF2DAC6FFB574DE"
```

Response format:

```json
{
  "playlistId": "PLBCF2DAC6FFB574DE",
  "count": 123,
  "items": [
    {
      "videoId": "dQw4w9WgXcQ",
      "title": "Example Video",
      "description": "...",
      "publishedAt": "2020-01-01T00:00:00Z",
      "position": 0,
      "thumbnails": {"default": {"url": "..."}}
    }
  ]
}
```

## Notes

- The API fetches up to 50 items per request and continues until the playlist is fully traversed.
- If a playlist item is private or deleted, it may still appear with limited metadata.
- Rate limits and quotas are enforced by YouTube; ensure your API key has sufficient quota.
