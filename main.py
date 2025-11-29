import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import AnalysisRun, MatchAnalysis

load_dotenv()

# Config - adjust these to experiment
MODEL = "gemini-2.0-flash"  # or "gemini-2.5-flash", "gemini-3-pro-preview"
MEDIA_RESOLUTION = "MEDIA_RESOLUTION_LOW"  # or "MEDIA_RESOLUTION_MEDIUM", "MEDIA_RESOLUTION_HIGH"
THINKING_LEVEL = "OFF"  # or "HIGH", "LOW"

VIDEO_FILE = "Adam Wardzinski vs Roberto Jimenez - 2025 IBJJF Pan Championship [oWVUjZm-ZUc].webm"
PROMPT = """Analyze this BJJ match video. For every scoring change (points or advantages), record:
- The exact timestamp in seconds from the start of the video
- Which athlete scored
- Points and/or advantages gained or lost
- The action that caused the score
- The applicable IBJJF rule

Be precise with timestamps - watch for when the referee signals the score."""

client = genai.Client()


# Set this to reuse an already-uploaded file (skip slow file listing)
CACHED_FILE_ID = "files/7lyyyyeb0cje"  # Set to None to upload fresh


def get_or_upload_video(filename: str):
    """Check for cached file ID, or upload new one."""
    # Use cached file if available
    if CACHED_FILE_ID:
        print(f"Using cached file: {CACHED_FILE_ID}")
        video = client.files.get(name=CACHED_FILE_ID)
        if video.state.name == "ACTIVE":
            return video
        print(f"Cached file not active ({video.state.name}), uploading fresh...")

    # Upload new file
    print(f"Uploading {filename}...")
    video = client.files.upload(file=filename)
    print(f"Uploaded: {video.name}")

    # Wait for processing
    print("Waiting for file to be processed...")
    while video.state.name == "PROCESSING":
        time.sleep(5)
        video = client.files.get(name=video.name)
        print(f"  State: {video.state.name}")

    if video.state.name != "ACTIVE":
        raise RuntimeError(f"File processing failed: {video.state.name}")

    return video


video = get_or_upload_video(VIDEO_FILE)
print("File ready!")

# Analyze with structured output
print(f"Analyzing with {MODEL} at {MEDIA_RESOLUTION} resolution...")
response = client.models.generate_content(
    model=MODEL,
    contents=[video, PROMPT],
    config=types.GenerateContentConfig(
        media_resolution=MEDIA_RESOLUTION,
        thinking_config=types.ThinkingConfig(thinking_budget=10000) if THINKING_LEVEL == "HIGH" else (types.ThinkingConfig(thinking_budget=1000) if THINKING_LEVEL == "LOW" else None),
        response_mime_type="application/json",
        response_schema=MatchAnalysis,
    ),
)

# Parse and validate response
analysis = MatchAnalysis.model_validate_json(response.text)

# Create run record
run = AnalysisRun(
    model=MODEL,
    media_resolution=MEDIA_RESOLUTION,
    video_file=VIDEO_FILE,
    prompt=PROMPT,
    analysis=analysis,
)

# Save to results directory
results_dir = Path("results")
results_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"{timestamp}_{MODEL}_{MEDIA_RESOLUTION}_thinking-{THINKING_LEVEL}.json"
output_path = results_dir / filename

with open(output_path, "w") as f:
    f.write(run.model_dump_json(indent=2))

print(f"\nSaved to {output_path}")
print(f"\nFound {len(analysis.events)} scoring events")
print(f"Final score: {analysis.final_score}")
print(f"Winner: {analysis.winner}")

# Print events summary
print("\nEvents:")
for event in analysis.events:
    change = f"+{event.points_change} pts" if event.points_change else f"+{event.advantages_change} adv"
    print(f"  {event.timestamp_seconds:>4}s | {event.athlete:<20} | {change:<10} | {event.action}")

print(f"\nTokens used: {response.usage_metadata}")
