import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import AnalysisRun, AthleteIdentification, MatchAnalysis

load_dotenv()

# Config - adjust these to experiment
MODEL = "gemini-2.5-pro"
MEDIA_RESOLUTION = "MEDIA_RESOLUTION_HIGH"
THINKING_LEVEL = "HIGH"  # or "HIGH", "LOW"

MATCHES_DIR = Path("matches")
RULEBOOK_FILE_ID = "files/dp6aqz2vzmq3"  # Global rulebook

ATHLETE_ID_PROMPT = """Look at the scoreboard overlay in this BJJ match video.

The scoreboard shows two athletes' names and scores. Identify which athlete is on which side:

**CRITICAL: Scoreboard Layout**
- The LEFT side of the scoreboard (as you view the screen) = Athlete 1
- The RIGHT side of the scoreboard (as you view the screen) = Athlete 2

For each athlete, record:
1. Their name exactly as shown on the scoreboard
2. Their gi (uniform) color: white, blue, or other
3. If both wear the same color gi, note their belt tip color (coral belts have yellow or green tips)
4. A brief physical description (build, hair, distinguishing features)

Also identify the single most reliable way to tell them apart during action (usually gi color)."""

PROMPT_TEMPLATE = """You are analyzing a BJJ (Brazilian Jiu-Jitsu) competition match video. You have been provided:
1. The match video
2. The official IBJJF Rules Book PDF

Your task is to identify and record every scoring change (points, advantages, or penalties) throughout the match.

## Athlete Identification (use this throughout the match)

**Athlete 1 (LEFT side of scoreboard):**
- Name: {athlete_1_name}
- Gi color: {athlete_1_gi}
- Appearance: {athlete_1_description}

**Athlete 2 (RIGHT side of scoreboard):**
- Name: {athlete_2_name}
- Gi color: {athlete_2_gi}
- Appearance: {athlete_2_description}

**How to tell them apart:** {distinguishing_feature}

## How to Identify Scoring Events

1. **Watch the referee** - The referee signals scoring with hand gestures and the scoreboard updates shortly after.

2. **Monitor the scoreboard overlay** - It shows current points, advantages, and penalties for each athlete.

3. **Reference the IBJJF rulebook** for correct point values.

## Scoring Reference (IBJJF Rules)

**Point Values:**
- 2 points: Takedown, Sweep, Knee on belly
- 3 points: Guard pass
- 4 points: Mount, Back control (back mount with hooks)

**Common Scoring Sequences:**

When positions flow continuously, points accumulate. Watch for these patterns:

1. **Guard Pass → Mount (7 points total)**
   - Athlete passes guard: +3 points (score becomes X-3 or 3-X)
   - Same athlete achieves mount 2-5 seconds later: +4 points (score becomes X-7 or 7-X)
   - These are TWO separate events to record

2. **Takedown → Guard Pass → Mount (9 points total)**
   - Takedown: +2, then Pass: +3, then Mount: +4
   - Three separate events

3. **Sweep → Guard Pass (5 points total)**
   - Sweep from guard: +2 points
   - Same athlete passes guard: +3 points

**Advantages (1 at a time):**
- Near-completion of any scoring position (almost passed guard, almost swept, etc.)
- Near-submission attempts

**Key Rule:** Each scoring position is a SEPARATE event. A guard pass at 2:00 and mount at 2:03 should be recorded as two events, not one "7 point" event.

## For each scoring event, record:
- timestamp_seconds: Exact time in the video (seconds from start)
- match_clock: Time shown on the match clock (e.g., "8:45")
- athlete: 1 or 2 (who scored or received penalty)
- points_change: Points gained/lost (use 0 if only advantage/penalty)
- advantages_change: Advantages gained/lost (use 0 if only points/penalty)
- penalties_change: Penalties received (use 0 if only points/advantage)
- action: Brief description (e.g., "Takedown", "Sweep", "Guard pass", "Mount")
- ibjjf_rule: Rule reference from the rulebook (e.g., "Art. 4.1 - Takedown")
- running_score: Current score as "athlete1-athlete2"
- running_advantages: Current advantages as "athlete1-athlete2"
- running_penalties: Current penalties as "athlete1-athlete2"

Record events when the referee signals or the scoreboard updates, not when the action begins."""

client = genai.Client()


def list_matches():
    """List all available matches."""
    if not MATCHES_DIR.exists():
        print("No matches directory found.")
        return []

    matches = []
    for match_dir in sorted(MATCHES_DIR.iterdir()):
        if match_dir.is_dir():
            metadata_path = match_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path) as f:
                    metadata = json.load(f)
                matches.append({
                    "video_id": match_dir.name,
                    "title": metadata.get("title", match_dir.name),
                })

    return matches


def get_file(file_id: str, description: str):
    """Get a file by ID, verify it's active."""
    print(f"Loading {description}: {file_id}")
    file = client.files.get(name=file_id)
    if file.state.name != "ACTIVE":
        raise RuntimeError(f"{description} not active: {file.state.name}")
    return file


def identify_athletes(video_file) -> AthleteIdentification:
    """Identify athletes from the video before main analysis."""
    print("Step 1: Identifying athletes with gemini-2.5-pro...")
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[video_file, ATHLETE_ID_PROMPT],
        config=types.GenerateContentConfig(
            media_resolution="MEDIA_RESOLUTION_HIGH",
            thinking_config=types.ThinkingConfig(thinking_budget=10000),
            response_mime_type="application/json",
            response_schema=AthleteIdentification,
        ),
    )
    return AthleteIdentification.model_validate_json(response.text)


def analyze_match(match_id: str):
    """Analyze a match by its video ID."""
    match_dir = MATCHES_DIR / match_id
    metadata_path = match_dir / "metadata.json"

    if not metadata_path.exists():
        print(f"Match not found: {match_id}")
        sys.exit(1)

    with open(metadata_path) as f:
        metadata = json.load(f)

    video_file_id = metadata.get("gemini_file_id")
    video_filename = metadata.get("video_filename", "video.webm")

    if not video_file_id:
        print(f"No Gemini file ID for match: {match_id}")
        sys.exit(1)

    print(f"Analyzing match: {metadata.get('title', match_id)}")

    # Load video and rulebook
    video = get_file(video_file_id, "video")
    rulebook = get_file(RULEBOOK_FILE_ID, "rulebook")
    print("Files ready!")

    # Step 1: Identify athletes
    athletes = identify_athletes(video)
    print(f"  Athlete 1: {athletes.athlete_1.name} ({athletes.athlete_1.gi_color} gi)")
    print(f"  Athlete 2: {athletes.athlete_2.name} ({athletes.athlete_2.gi_color} gi)")
    print(f"  Distinguishing feature: {athletes.distinguishing_feature}")

    # Build prompt with athlete context
    prompt = PROMPT_TEMPLATE.format(
        athlete_1_name=athletes.athlete_1.name,
        athlete_1_gi=athletes.athlete_1.gi_color,
        athlete_1_description=athletes.athlete_1.physical_description,
        athlete_2_name=athletes.athlete_2.name,
        athlete_2_gi=athletes.athlete_2.gi_color,
        athlete_2_description=athletes.athlete_2.physical_description,
        distinguishing_feature=athletes.distinguishing_feature,
    )

    # Step 2: Analyze match with athlete context
    print(f"\nStep 2: Analyzing match with {MODEL} at {MEDIA_RESOLUTION} resolution...")
    print("Sending video + rulebook + prompt to Gemini...")
    response = client.models.generate_content(
        model=MODEL,
        contents=[video, rulebook, prompt],
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
        video_file=video_filename,
        prompt=prompt,
        analysis=analysis,
    )

    # Save to match's results directory
    results_dir = match_dir / "results"
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


def main():
    parser = argparse.ArgumentParser(description="Analyze BJJ match videos")
    parser.add_argument("--match", "-m", help="Match video ID to analyze")
    parser.add_argument("--list", "-l", action="store_true", help="List available matches")
    args = parser.parse_args()

    if args.list:
        matches = list_matches()
        if matches:
            print("Available matches:")
            for m in matches:
                print(f"  {m['video_id']}: {m['title']}")
        else:
            print("No matches found. Add videos using add_video.py")
        return

    if args.match:
        analyze_match(args.match)
    else:
        # Default: list matches
        matches = list_matches()
        if matches:
            print("Available matches (use --match <id> to analyze):")
            for m in matches:
                print(f"  {m['video_id']}: {m['title']}")
        else:
            print("No matches found. Add videos using add_video.py")


if __name__ == "__main__":
    main()
