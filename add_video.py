"""
Add a new video to the match analysis system.

Usage: uv run python add_video.py <youtube-url>

This script:
1. Downloads the video using yt-dlp
2. Extracts metadata from YouTube
3. Uploads the video to Gemini Files API
4. Creates the match directory structure with metadata.json
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

MATCHES_DIR = Path("matches")


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_video_metadata(url: str) -> dict:
    """Get video metadata using yt-dlp without downloading."""
    result = subprocess.run(
        [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error getting metadata: {result.stderr}")
        sys.exit(1)

    return json.loads(result.stdout)


def download_video(url: str, output_path: Path) -> None:
    """Download video using yt-dlp."""
    print(f"Downloading video to {output_path}...")
    result = subprocess.run(
        [
            "yt-dlp",
            "-f", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/bestvideo+bestaudio/best",
            "--merge-output-format", "webm",
            "-o", str(output_path),
            url,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error downloading: {result.stderr}")
        sys.exit(1)
    print("Download complete!")


def upload_to_gemini(video_path: Path) -> str:
    """Upload video to Gemini Files API and return file ID."""
    print(f"Uploading to Gemini Files API...")
    client = genai.Client()

    # Upload file
    file = client.files.upload(file=video_path)
    print(f"Uploaded! File ID: {file.name}")

    # Wait for processing
    print("Waiting for video processing...")
    while file.state.name == "PROCESSING":
        import time
        time.sleep(5)
        file = client.files.get(name=file.name)

    if file.state.name != "ACTIVE":
        print(f"Error: File state is {file.state.name}")
        sys.exit(1)

    print("Video ready!")
    return file.name


def add_video(url: str, skip_upload: bool = False):
    """Add a new video to the system."""
    video_id = extract_video_id(url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {url}")
        sys.exit(1)

    print(f"Video ID: {video_id}")

    # Check if match already exists
    match_dir = MATCHES_DIR / video_id
    if match_dir.exists():
        print(f"Match directory already exists: {match_dir}")
        response = input("Overwrite? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)

    # Get metadata
    print("Fetching video metadata...")
    yt_meta = get_video_metadata(url)

    # Create match directory
    match_dir.mkdir(parents=True, exist_ok=True)
    (match_dir / "results").mkdir(exist_ok=True)

    # Download video
    video_path = match_dir / "video.webm"
    if not video_path.exists():
        download_video(url, video_path)
    else:
        print(f"Video already exists: {video_path}")

    # Upload to Gemini
    gemini_file_id = None
    if not skip_upload:
        gemini_file_id = upload_to_gemini(video_path)
    else:
        print("Skipping Gemini upload (--skip-upload flag)")

    # Create metadata.json
    metadata = {
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": yt_meta.get("title", ""),
        "description": yt_meta.get("description", "")[:500],  # Truncate long descriptions
        "channel": yt_meta.get("channel", "") or yt_meta.get("uploader", ""),
        "duration_seconds": yt_meta.get("duration", 0),
        "upload_date": yt_meta.get("upload_date", ""),
        "thumbnail_url": yt_meta.get("thumbnail", f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"),
        "video_filename": "video.webm",
        "gemini_file_id": gemini_file_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path = match_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nMatch added successfully!")
    print(f"  Directory: {match_dir}")
    print(f"  Title: {metadata['title']}")
    print(f"  Duration: {metadata['duration_seconds']}s")
    print(f"  Gemini File ID: {gemini_file_id or 'Not uploaded'}")
    print(f"\nTo analyze this match:")
    print(f"  uv run python main.py --match {video_id}")


def main():
    parser = argparse.ArgumentParser(description="Add a new video to the match analysis system")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--skip-upload", action="store_true", help="Skip uploading to Gemini (for testing)")
    args = parser.parse_args()

    add_video(args.url, skip_upload=args.skip_upload)


if __name__ == "__main__":
    main()
