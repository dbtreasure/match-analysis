import json
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

RESULTS_DIR = Path("results")
GROUND_TRUTH_FILE = Path("ground_truth.json")


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/editor")
def editor():
    return send_from_directory(".", "editor.html")


@app.route("/video/<path:filename>")
def video(filename):
    return send_from_directory(".", filename)


@app.route("/api/results")
def list_results():
    files = sorted(RESULTS_DIR.glob("*.json"), reverse=True)
    return jsonify([f.name for f in files])


@app.route("/api/results/<filename>")
def get_result(filename):
    return send_from_directory(RESULTS_DIR, filename)


@app.route("/api/ground-truth", methods=["GET"])
def get_ground_truth():
    if GROUND_TRUTH_FILE.exists():
        return send_from_directory(".", GROUND_TRUTH_FILE.name)
    return jsonify(None)


@app.route("/api/ground-truth", methods=["POST"])
def save_ground_truth():
    data = request.get_json()
    with open(GROUND_TRUTH_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "saved"})


if __name__ == "__main__":
    app.run(port=8000, debug=True)
