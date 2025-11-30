"""
Migration script to move existing data to the new matches/ folder structure.

This is a one-time migration script that:
1. Extracts video ID from the existing video filename
2. Creates matches/<video_id>/ directory
3. Moves video file, ground truth files
4. Moves results
5. Creates metadata.json from existing file_ids.json
"""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
MATCHES_DIR = PROJECT_ROOT / "matches"


def extract_video_id(filename: str) -> str | None:
    """Extract YouTube video ID from filename like 'Title [videoId].webm'"""
    match = re.search(r"\[([a-zA-Z0-9_-]{11})\]", filename)
    return match.group(1) if match else None


def migrate():
    # Find the existing video file
    video_files = list(PROJECT_ROOT.glob("*.webm"))
    if not video_files:
        print("No .webm files found in project root")
        return

    video_file = video_files[0]
    video_id = extract_video_id(video_file.name)

    if not video_id:
        print(f"Could not extract video ID from: {video_file.name}")
        return

    print(f"Migrating video: {video_file.name}")
    print(f"Video ID: {video_id}")

    # Create match directory
    match_dir = MATCHES_DIR / video_id
    match_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created: {match_dir}")

    # Create results subdirectory
    results_dir = match_dir / "results"
    results_dir.mkdir(exist_ok=True)

    # Load existing file_ids.json for Gemini file ID
    file_ids_path = PROJECT_ROOT / "file_ids.json"
    gemini_file_id = None
    if file_ids_path.exists():
        with open(file_ids_path) as f:
            file_ids = json.load(f)
            gemini_file_id = file_ids.get("video", {}).get("file_id")

    # Create metadata.json
    # Extract title from filename (remove extension and video ID bracket)
    title = re.sub(r"\s*\[[^\]]+\]\s*$", "", video_file.stem)

    metadata = {
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "description": "",
        "channel": "",
        "duration_seconds": 0,
        "upload_date": "",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        "video_filename": "video.webm",
        "gemini_file_id": gemini_file_id,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }

    metadata_path = match_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Created: {metadata_path}")

    # Move video file
    dest_video = match_dir / "video.webm"
    if not dest_video.exists():
        shutil.copy2(video_file, dest_video)
        print(f"Copied video to: {dest_video}")
    else:
        print(f"Video already exists: {dest_video}")

    # Move ground_truth.json
    gt_path = PROJECT_ROOT / "ground_truth.json"
    if gt_path.exists():
        dest_gt = match_dir / "ground_truth.json"
        shutil.copy2(gt_path, dest_gt)
        print(f"Copied: {gt_path.name} -> {dest_gt}")

    # Move athlete_id_ground_truth.json
    athlete_gt_path = PROJECT_ROOT / "athlete_id_ground_truth.json"
    if athlete_gt_path.exists():
        dest_athlete_gt = match_dir / "athlete_id_ground_truth.json"
        shutil.copy2(athlete_gt_path, dest_athlete_gt)
        print(f"Copied: {athlete_gt_path.name} -> {dest_athlete_gt}")

    # Move results
    old_results_dir = PROJECT_ROOT / "results"
    if old_results_dir.exists():
        for result_file in old_results_dir.glob("*.json"):
            dest_result = results_dir / result_file.name
            shutil.copy2(result_file, dest_result)
            print(f"Copied result: {result_file.name}")

    print("\nMigration complete!")
    print(f"\nNew structure:")
    print(f"  {match_dir}/")
    print(f"    metadata.json")
    print(f"    video.webm")
    print(f"    ground_truth.json")
    print(f"    athlete_id_ground_truth.json")
    print(f"    results/")

    # List what can be cleaned up
    print("\nYou can now delete the old files:")
    print(f"  - {video_file}")
    print(f"  - {gt_path}")
    print(f"  - {athlete_gt_path}")
    print(f"  - {file_ids_path}")
    print(f"  - {old_results_dir}/")


if __name__ == "__main__":
    migrate()
