import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

MATCHES_DIR = Path("matches")


def get_match_dir(match_id: str) -> Path:
    return MATCHES_DIR / match_id


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/editor")
def editor():
    return send_from_directory(".", "editor.html")


# ========== MATCH ENDPOINTS ==========


@app.route("/api/matches")
def list_matches():
    """List all matches with basic info."""
    matches = []
    if MATCHES_DIR.exists():
        for match_dir in sorted(MATCHES_DIR.iterdir()):
            if match_dir.is_dir():
                metadata_path = match_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path) as f:
                        metadata = json.load(f)
                    matches.append({
                        "video_id": metadata.get("video_id", match_dir.name),
                        "title": metadata.get("title", match_dir.name),
                        "thumbnail_url": metadata.get("thumbnail_url", ""),
                    })
    return jsonify(matches)


@app.route("/api/matches/<match_id>")
def get_match(match_id: str):
    """Get full metadata for a match."""
    metadata_path = get_match_dir(match_id) / "metadata.json"
    if metadata_path.exists():
        return send_from_directory(get_match_dir(match_id), "metadata.json")
    return jsonify({"error": "Match not found"}), 404


@app.route("/api/matches/<match_id>/results")
def list_match_results(match_id: str):
    """List results for a specific match."""
    results_dir = get_match_dir(match_id) / "results"
    if results_dir.exists():
        files = sorted(results_dir.glob("*.json"), reverse=True)
        return jsonify([f.name for f in files])
    return jsonify([])


@app.route("/api/matches/<match_id>/results/<filename>")
def get_match_result(match_id: str, filename: str):
    """Get a specific result file for a match."""
    results_dir = get_match_dir(match_id) / "results"
    return send_from_directory(results_dir, filename)


@app.route("/api/matches/<match_id>/ground-truth", methods=["GET"])
def get_match_ground_truth(match_id: str):
    """Get ground truth for a match."""
    gt_path = get_match_dir(match_id) / "ground_truth.json"
    if gt_path.exists():
        return send_from_directory(get_match_dir(match_id), "ground_truth.json")
    return jsonify(None)


@app.route("/api/matches/<match_id>/ground-truth", methods=["POST"])
def save_match_ground_truth(match_id: str):
    """Save ground truth for a match."""
    match_dir = get_match_dir(match_id)
    match_dir.mkdir(parents=True, exist_ok=True)
    data = request.get_json()
    gt_path = match_dir / "ground_truth.json"
    with open(gt_path, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "saved"})


@app.route("/api/matches/<match_id>/athlete-id-ground-truth", methods=["GET"])
def get_match_athlete_id_gt(match_id: str):
    """Get athlete ID ground truth for a match."""
    gt_path = get_match_dir(match_id) / "athlete_id_ground_truth.json"
    if gt_path.exists():
        return send_from_directory(get_match_dir(match_id), "athlete_id_ground_truth.json")
    return jsonify(None)


@app.route("/api/matches/<match_id>/athlete-id-ground-truth", methods=["POST"])
def save_match_athlete_id_gt(match_id: str):
    """Save athlete ID ground truth for a match."""
    match_dir = get_match_dir(match_id)
    match_dir.mkdir(parents=True, exist_ok=True)
    data = request.get_json()
    gt_path = match_dir / "athlete_id_ground_truth.json"
    with open(gt_path, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "saved"})


@app.route("/video/<match_id>/<filename>")
def serve_match_video(match_id: str, filename: str):
    """Serve video file from match directory."""
    return send_from_directory(get_match_dir(match_id), filename)


if __name__ == "__main__":
    app.run(port=8000, debug=True)
