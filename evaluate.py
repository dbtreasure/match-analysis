import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

MATCHES_DIR = Path("matches")


@dataclass
class MatchResult:
    gt_index: int | None
    pred_index: int | None
    gt_event: dict | None
    pred_event: dict | None


def load_ground_truth(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def load_result(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def normalize_athlete(athlete, athlete_1_name: str, athlete_2_name: str) -> str:
    """Convert athlete field to string '1' or '2'."""
    # Already a string "1" or "2"
    if athlete in ("1", "2"):
        return athlete
    # Integer 1 or 2
    if athlete in (1, 2):
        return str(athlete)
    # Match by name
    if athlete == athlete_1_name:
        return "1"
    if athlete == athlete_2_name:
        return "2"
    # Fallback: check if name contains athlete first name
    if athlete_1_name and athlete_1_name.split()[0] in str(athlete):
        return "1"
    if athlete_2_name and athlete_2_name.split()[0] in str(athlete):
        return "2"
    return "1"  # Default


def normalize_events(events: list[dict], athlete_1_name: str, athlete_2_name: str) -> list[dict]:
    """Normalize athlete fields in events to strings."""
    return [
        {**e, "athlete": normalize_athlete(e.get("athlete"), athlete_1_name, athlete_2_name)}
        for e in events
    ]


def match_events(
    gt_events: list[dict],
    pred_events: list[dict],
    clock_tolerance: int = 10,
) -> list[MatchResult]:
    """
    Match predicted events to ground truth events using greedy matching.

    Matching criteria: match_clock within tolerance AND same athlete.
    Uses greedy approach: for each GT event in order, find closest unmatched prediction.
    """
    matches = []
    used_pred_indices = set()

    # For each ground truth event, find best matching prediction
    for gt_idx, gt_event in enumerate(gt_events):
        best_pred_idx = None
        best_time_diff = float('inf')

        gt_clock = parse_clock(gt_event.get("match_clock", ""))

        for pred_idx, pred_event in enumerate(pred_events):
            if pred_idx in used_pred_indices:
                continue

            # Check athlete match
            if gt_event.get("athlete") != pred_event.get("athlete"):
                continue

            # Check match_clock tolerance
            pred_clock = parse_clock(pred_event.get("match_clock", ""))

            if gt_clock is None or pred_clock is None:
                # Fall back to timestamp_seconds if no clock
                gt_time = gt_event.get("timestamp_seconds", 0)
                pred_time = pred_event.get("timestamp_seconds", 0)
                time_diff = abs(gt_time - pred_time)
            else:
                time_diff = abs(gt_clock - pred_clock)

            if time_diff <= clock_tolerance and time_diff < best_time_diff:
                best_time_diff = time_diff
                best_pred_idx = pred_idx

        if best_pred_idx is not None:
            used_pred_indices.add(best_pred_idx)
            matches.append(MatchResult(
                gt_index=gt_idx,
                pred_index=best_pred_idx,
                gt_event=gt_event,
                pred_event=pred_events[best_pred_idx],
            ))
        else:
            # False negative - GT event with no match
            matches.append(MatchResult(
                gt_index=gt_idx,
                pred_index=None,
                gt_event=gt_event,
                pred_event=None,
            ))

    # Add false positives - predictions with no GT match
    for pred_idx, pred_event in enumerate(pred_events):
        if pred_idx not in used_pred_indices:
            matches.append(MatchResult(
                gt_index=None,
                pred_index=pred_idx,
                gt_event=None,
                pred_event=pred_event,
            ))

    return matches


def compute_detection_metrics(matches: list[MatchResult]) -> dict:
    """Compute precision, recall, F1 for event detection."""
    tp = sum(1 for m in matches if m.gt_event and m.pred_event)
    fn = sum(1 for m in matches if m.gt_event and not m.pred_event)
    fp = sum(1 for m in matches if not m.gt_event and m.pred_event)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def compute_field_accuracy(matches: list[MatchResult]) -> dict:
    """Compute field-level accuracy for matched events."""
    matched = [m for m in matches if m.gt_event and m.pred_event]

    if not matched:
        return {}

    fields = [
        "points_change",
        "advantages_change",
        "penalties_change",
        "action",
        "running_score",
        "running_advantages",
        "running_penalties",
        "match_clock",
    ]

    field_stats = {}

    for field in fields:
        correct = 0
        total = 0

        for m in matched:
            gt_val = m.gt_event.get(field)
            pred_val = m.pred_event.get(field)

            # Skip if ground truth doesn't have this field
            if gt_val is None or gt_val == "":
                continue

            total += 1

            # For match_clock, use tolerance
            if field == "match_clock":
                gt_seconds = parse_clock(gt_val)
                pred_seconds = parse_clock(pred_val) if pred_val else None
                if pred_seconds is not None and abs(gt_seconds - pred_seconds) <= 5:
                    correct += 1
            else:
                if gt_val == pred_val:
                    correct += 1

        if total > 0:
            field_stats[field] = {
                "correct": correct,
                "total": total,
                "accuracy": correct / total,
            }

    return field_stats


def parse_clock(clock_str: str) -> int | None:
    """Parse clock string like '8:45' to seconds."""
    if not clock_str:
        return None
    try:
        parts = clock_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(clock_str)
    except (ValueError, AttributeError):
        return None


def compute_clock_accuracy(matches: list[MatchResult]) -> dict:
    """Compute match clock accuracy metrics for matched events."""
    matched = [m for m in matches if m.gt_event and m.pred_event]

    if not matched:
        return {}

    errors = []
    for m in matched:
        gt_clock = parse_clock(m.gt_event.get("match_clock", ""))
        pred_clock = parse_clock(m.pred_event.get("match_clock", ""))

        if gt_clock is not None and pred_clock is not None:
            errors.append(abs(gt_clock - pred_clock))

    if not errors:
        return {}

    return {
        "mean_absolute_error": sum(errors) / len(errors),
        "max_error": max(errors),
        "min_error": min(errors),
        "matched_with_clock": len(errors),
    }


def compute_sequence_metrics(matches: list[MatchResult]) -> dict:
    """
    Compute sequence ordering metrics.

    For matched events, check if relative ordering is preserved.
    Uses Kendall tau-like metric: % of pairs in correct order.
    """
    # Get matched events sorted by GT index
    matched = sorted(
        [m for m in matches if m.gt_event and m.pred_event],
        key=lambda m: m.gt_index
    )

    if len(matched) < 2:
        return {"pairs_in_order": 1.0, "total_pairs": 0, "inversions": 0}

    # Count inversions (pairs where pred order differs from GT order)
    inversions = 0
    total_pairs = 0

    for i in range(len(matched)):
        for j in range(i + 1, len(matched)):
            total_pairs += 1
            # GT order: i < j (by construction)
            # Check if pred order agrees
            if matched[i].pred_index > matched[j].pred_index:
                inversions += 1

    pairs_in_order = (total_pairs - inversions) / total_pairs if total_pairs > 0 else 1.0

    return {
        "pairs_in_order": pairs_in_order,
        "total_pairs": total_pairs,
        "inversions": inversions,
    }


def compute_match_level_metrics(gt_data: dict, pred_data: dict) -> dict:
    """Compute match-level metrics (final score, winner, athlete names)."""
    gt_analysis = gt_data
    pred_analysis = pred_data.get("analysis", pred_data)

    metrics = {}

    # Final score
    gt_final = gt_analysis.get("final_score", "")
    pred_final = pred_analysis.get("final_score", "")
    metrics["final_score_correct"] = gt_final == pred_final
    metrics["gt_final_score"] = gt_final
    metrics["pred_final_score"] = pred_final

    # Winner
    gt_winner = gt_analysis.get("winner", "")
    pred_winner = pred_analysis.get("winner", "")
    metrics["winner_correct"] = gt_winner == pred_winner
    metrics["gt_winner"] = gt_winner
    metrics["pred_winner"] = pred_winner

    # Athlete names
    for i in [1, 2]:
        gt_name = gt_analysis.get(f"athlete_{i}_name", "")
        pred_name = pred_analysis.get(f"athlete_{i}_name", "")
        metrics[f"athlete_{i}_name_correct"] = gt_name == pred_name

    return metrics


def evaluate(gt_path: Path, result_path: Path, clock_tolerance: int = 10) -> dict:
    """Run full evaluation and return metrics."""
    gt_data = load_ground_truth(gt_path)
    result_data = load_result(result_path)

    # Get athlete names from ground truth (canonical source)
    gt_athlete_1 = gt_data.get("athlete_1_name", "")
    gt_athlete_2 = gt_data.get("athlete_2_name", "")
    pred_analysis = result_data.get("analysis", {})

    # Normalize ALL events using GT athlete names for consistent comparison
    # This ensures we compare the same actual athletes regardless of how they're labeled
    gt_events = normalize_events(gt_data.get("events", []), gt_athlete_1, gt_athlete_2)
    pred_events = normalize_events(pred_analysis.get("events", []), gt_athlete_1, gt_athlete_2)

    matches = match_events(gt_events, pred_events, clock_tolerance)

    return {
        "result_file": result_path.name,
        "model": result_data.get("model", "unknown"),
        "media_resolution": result_data.get("media_resolution", "unknown"),
        "gt_event_count": len(gt_events),
        "pred_event_count": len(pred_events),
        "clock_tolerance": clock_tolerance,
        "gt_athlete_1": gt_athlete_1,
        "gt_athlete_2": gt_athlete_2,
        "detection": compute_detection_metrics(matches),
        "field_accuracy": compute_field_accuracy(matches),
        "clock_accuracy": compute_clock_accuracy(matches),
        "sequence": compute_sequence_metrics(matches),
        "match_level": compute_match_level_metrics(gt_data, result_data),
        "matches": [
            {
                "gt_index": m.gt_index,
                "pred_index": m.pred_index,
                "gt_event": m.gt_event,
                "pred_event": m.pred_event,
                "matched": m.gt_event is not None and m.pred_event is not None,
            }
            for m in matches
        ],
    }


def print_report(metrics: dict):
    """Print a human-readable evaluation report."""
    print("=" * 70)
    print(f"EVALUATION REPORT: {metrics['result_file']}")
    print(f"Model: {metrics['model']} | Resolution: {metrics['media_resolution']}")
    print("=" * 70)

    print(f"\nEvents: {metrics['pred_event_count']} predicted vs {metrics['gt_event_count']} ground truth")
    print(f"Clock tolerance: ±{metrics['clock_tolerance']}s (matching by match_clock)")

    # Detection metrics
    det = metrics["detection"]
    print(f"\n--- Event Detection ---")
    print(f"  True Positives:  {det['true_positives']}")
    print(f"  False Negatives: {det['false_negatives']} (missed events)")
    print(f"  False Positives: {det['false_positives']} (hallucinated events)")
    print(f"  Precision: {det['precision']:.1%}")
    print(f"  Recall:    {det['recall']:.1%}")
    print(f"  F1 Score:  {det['f1']:.1%}")

    # Field accuracy
    if metrics["field_accuracy"]:
        print(f"\n--- Field Accuracy (matched events only) ---")
        for field, stats in metrics["field_accuracy"].items():
            print(f"  {field}: {stats['correct']}/{stats['total']} ({stats['accuracy']:.1%})")

    # Clock accuracy
    if metrics["clock_accuracy"]:
        ca = metrics["clock_accuracy"]
        print(f"\n--- Match Clock Accuracy ---")
        print(f"  Mean Absolute Error: {ca['mean_absolute_error']:.1f}s")
        print(f"  Range: {ca['min_error']:.0f}s - {ca['max_error']:.0f}s")
        print(f"  Events with clock: {ca['matched_with_clock']}")

    # Sequence metrics
    seq = metrics["sequence"]
    print(f"\n--- Sequence Ordering ---")
    print(f"  Pairs in correct order: {seq['pairs_in_order']:.1%}")
    print(f"  Inversions: {seq['inversions']}/{seq['total_pairs']}")

    # Match-level metrics
    ml = metrics["match_level"]
    print(f"\n--- Match-Level ---")
    print(f"  Final Score: {'✓' if ml['final_score_correct'] else '✗'} (GT: {ml['gt_final_score']}, Pred: {ml['pred_final_score']})")
    print(f"  Winner: {'✓' if ml['winner_correct'] else '✗'} (GT: {ml['gt_winner']}, Pred: {ml['pred_winner']})")

    # Detailed event matching
    print(f"\n--- Event Matching Detail ---")
    gt_names = {"1": metrics.get("gt_athlete_1", "A1"), "2": metrics.get("gt_athlete_2", "A2")}

    def athlete_label(athlete_num):
        name = gt_names.get(str(athlete_num), f"A{athlete_num}")
        return name.split()[0] if name else f"A{athlete_num}"

    for m in metrics["matches"]:
        if m["matched"]:
            gt = m["gt_event"]
            pred = m["pred_event"]
            gt_clock = gt.get("match_clock", "?")
            pred_clock = pred.get("match_clock", "?")
            print(f"  ✓ GT[{m['gt_index']}] ↔ Pred[{m['pred_index']}]: {athlete_label(gt['athlete'])} @ {gt_clock} → {pred_clock} | {gt['action']}")
        elif m["gt_event"]:
            gt = m["gt_event"]
            gt_clock = gt.get("match_clock", "?")
            print(f"  ✗ MISSED GT[{m['gt_index']}]: {athlete_label(gt['athlete'])} @ {gt_clock} | {gt['action']}")
        else:
            pred = m["pred_event"]
            pred_clock = pred.get("match_clock", "?")
            print(f"  ✗ EXTRA Pred[{m['pred_index']}]: A{pred['athlete']} @ {pred_clock} | {pred['action']}")

    print()


def list_matches():
    """List all available matches."""
    if not MATCHES_DIR.exists():
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


def main():
    parser = argparse.ArgumentParser(description="Evaluate BJJ match analysis results")
    parser.add_argument("--match", "-m", help="Match video ID to evaluate")
    parser.add_argument("--result", "-r", help="Specific result file to evaluate")
    parser.add_argument("--list", "-l", action="store_true", help="List available matches")
    args = parser.parse_args()

    if args.list:
        matches = list_matches()
        if matches:
            print("Available matches:")
            for m in matches:
                print(f"  {m['video_id']}: {m['title']}")
        else:
            print("No matches found.")
        return

    # Determine match directory
    if args.match:
        match_dir = MATCHES_DIR / args.match
    else:
        # Default to first match
        matches = list_matches()
        if not matches:
            print("No matches found. Use --match to specify a match ID.")
            sys.exit(1)
        match_dir = MATCHES_DIR / matches[0]["video_id"]
        print(f"Using match: {matches[0]['video_id']}")

    gt_path = match_dir / "ground_truth.json"
    results_dir = match_dir / "results"

    if not gt_path.exists():
        print(f"Error: Ground truth file not found: {gt_path}")
        sys.exit(1)

    # Get result files to evaluate
    if args.result:
        result_files = [results_dir / args.result]
    else:
        result_files = sorted(results_dir.glob("*.json"), reverse=True)

    if not result_files:
        print("No result files found")
        sys.exit(1)

    all_metrics = []
    for result_path in result_files:
        metrics = evaluate(gt_path, result_path)
        all_metrics.append(metrics)
        print_report(metrics)

    # Summary comparison if multiple files
    if len(all_metrics) > 1:
        print("=" * 70)
        print("SUMMARY COMPARISON")
        print("=" * 70)
        print(f"{'Model':<30} {'Res':<10} {'F1':<8} {'Prec':<8} {'Recall':<8}")
        print("-" * 70)
        for m in all_metrics:
            det = m["detection"]
            print(f"{m['model']:<30} {m['media_resolution'].replace('MEDIA_RESOLUTION_', ''):<10} {det['f1']:.1%}    {det['precision']:.1%}    {det['recall']:.1%}")


if __name__ == "__main__":
    main()
