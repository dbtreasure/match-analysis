# BJJ Match Analysis

AI-powered scoring analysis for Brazilian Jiu-Jitsu match videos using Google Gemini.

## Overview

This tool analyzes BJJ match footage and automatically extracts scoring events (points and advantages) with timestamps. It uses Gemini's video understanding capabilities to identify when athletes score and what techniques they used.

## Features

- **Automated Video Analysis**: Upload a BJJ match video and get a timestamped breakdown of all scoring events
- **Structured Output**: Analysis results include athlete names, gi colors, timestamps, point/advantage changes, and IBJJF rule references
- **Result Viewer**: Web UI that syncs scoring events with video playback - events reveal as you watch
- **Ground Truth Editor**: Manual annotation tool for creating/correcting scoring data with video sync

## Setup

Requires Python 3.12+

```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
```

## Usage

### Analyze a Match

```bash
uv run python main.py
```

Configure analysis parameters in `main.py`:
- `MODEL`: Gemini model to use (e.g., `gemini-2.0-flash`)
- `MEDIA_RESOLUTION`: Video quality for analysis (`LOW`, `MEDIUM`, `HIGH`)
- `THINKING_LEVEL`: Enable Gemini's thinking mode (`OFF`, `LOW`, `HIGH`)

Results are saved to `results/` with timestamps.

### View Results

```bash
uv run python server.py
```

Open http://localhost:8000 to view analysis results synced with video playback.

### Edit Ground Truth

Open http://localhost:8000/editor to manually annotate scoring events for evaluation.

## Project Structure

```
main.py         # Video analysis script using Gemini API
models.py       # Pydantic models for structured output
server.py       # Flask server for web UI
index.html      # Result viewer with video sync
editor.html     # Ground truth annotation editor
results/        # Analysis output JSON files
```

## Dependencies

- `google-genai` - Google Gemini API client
- `flask` - Web server
- `yt-dlp` - Video downloading
- `python-dotenv` - Environment variable management
