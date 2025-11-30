# BJJ Match Video Analysis System

## Project Goal

Build a system that uses Google Gemini's multimodal capabilities to automatically analyze BJJ (Brazilian Jiu-Jitsu) competition match videos and extract all scoring events (points, advantages, penalties) with high accuracy.

## What We're Trying to Accomplish

1. **Accurate event detection** - Identify every scoring change in a match
2. **Precise timestamps** - Record when events occur (both video timestamp and match clock)
3. **Correct attribution** - Assign events to the correct athlete
4. **Running score tracking** - Maintain accurate cumulative scores throughout the match

## Current Architecture

```
Video + Rulebook PDF → Gemini API → Structured JSON → Evaluation vs Ground Truth
```

### Key Files

- `main.py` - Runs Gemini analysis with video + rulebook, outputs structured JSON
- `models.py` - Pydantic schemas for structured output (MatchAnalysis, ScoringEvent)
- `evaluate.py` - Scores predictions against ground truth (precision/recall/F1)
- `ground_truth.json` - Human-annotated correct events for the test match
- `file_ids.json` - Cached Gemini Files API IDs for video and rulebook PDF
- `gemini_models.txt` - Reference for available Gemini model names
- `editor.html` - Web UI for creating/editing ground truth annotations
- `server.py` - Flask server for the editor UI

### Schema (models.py)

Each ScoringEvent has:
- `timestamp_seconds` - Video time in seconds
- `match_clock` - Match clock display (e.g., "8:45")
- `athlete` - "1" (left side of scoreboard) or "2" (right side)
- `points_change`, `advantages_change`, `penalties_change`
- `action` - Brief description
- `ibjjf_rule` - Rule reference
- `running_score`, `running_advantages`, `running_penalties` - Cumulative as "X-Y"

### Evaluation Metrics

- **Precision** - Of predicted events, how many were real?
- **Recall** - Of real events, how many were found?
- **F1 Score** - Harmonic mean of precision and recall
- **Field accuracy** - Per-field correctness on matched events
- Matching uses ±5 second timestamp tolerance + same athlete

## Current Results

| Model | Resolution | Thinking | F1 | Precision | Recall |
|-------|------------|----------|-----|-----------|--------|
| gemini-2.5-flash | HIGH | OFF | 38.7% | 40.0% | 37.5% |
| gemini-3-pro-preview | HIGH | HIGH | 50.0% | 58.3% | 43.8% |

## Known Issues

1. **Missed mid-match sequences** - Guard pass + mount pairs often missed
2. **Score corrections** - Model struggles with referee/table score adjustments
3. **Late-match events** - Final events near match end often missed
4. **Advantage attribution** - Some advantages hallucinated or missed

## Test Video

`Adam Wardzinski vs Roberto Jimenez - 2025 IBJJF Pan Championship`
- 16 ground truth events
- 10-minute match
- Contains a mid-match score correction (complex edge case)

## Running the System

```bash
# Run analysis
uv run python main.py

# Evaluate latest result
uv run python evaluate.py

# Evaluate specific result
uv run python evaluate.py results/<filename>.json

# Run ground truth editor
uv run python server.py
```

## Configuration (main.py)

```python
MODEL = "gemini-3-pro-preview"      # Model to use
MEDIA_RESOLUTION = "MEDIA_RESOLUTION_HIGH"  # Video quality
THINKING_LEVEL = "HIGH"             # Reasoning depth (OFF/LOW/HIGH)
```
