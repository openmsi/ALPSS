"""Compare a run's results against the ground truth.

    poetry run python benchmarks/summarize.py benchmarks/runs/main
    poetry run python benchmarks/summarize.py benchmarks/runs/feature --against benchmarks/runs/main

For each case and truth value: measured, error, relative error, the phase's OK
flag, ALPSS's reported uncertainty and whether it covers the error. Also the
RMS / max error of the smoothed velocity trace against the true history.
Writes summary.csv and summary.md into the run directory; with --against, also
writes comparison_vs_<other>.csv/.md there.
"""

import argparse
import json
import os

import numpy as np
import pandas as pd

from common import DATA_DIR, REPO_ROOT, truth_path, velocity_true_path

# truth key -> (results key of the reported uncertainty, OK flag of its phase)
UNCERTAINTY = {
    "Velocity at Max Compression": "Velocity at Max Compression Vel Uncertainty",
    "Velocity at Max Tension": "Velocity at Max Tension Vel Uncertainty",
    "Spall Strength": "Spall Strength Uncertainty",
    "Strain Rate": "Strain Rate Uncertainty",
    "HEL Strength (GPa)": "HEL Uncertainty (GPa)",
}
PHASE_FLAG = {
    "Velocity at Max Tension": "Spall OK",
    "Time at Max Tension": "Spall OK",
    "Spall Strength": "Spall OK",
    "Strain Rate": "Spall OK",
    "HEL Free Surface Velocity (m/s)": "HEL OK",
    "HEL Strength (GPa)": "HEL OK",
}
TRACE_METRICS = ("Velocity trace RMS (m/s)", "Velocity trace max (m/s)")


def trace_errors(run_case_dir, case_id, data_dir):
    smooth = os.path.join(run_case_dir, f"{case_id}-velocity--smooth.csv")
    if not os.path.exists(smooth):
        return {}
    measured = np.loadtxt(smooth, delimiter=",")
    true = np.loadtxt(velocity_true_path(data_dir, case_id), delimiter=",")
    err = measured[:, 1] - np.interp(measured[:, 0], true[:, 0], true[:, 1])
    err = err[np.isfinite(err)]
    if err.size == 0:
        return {}
    return {
        TRACE_METRICS[0]: float(np.sqrt(np.mean(err**2))),
        TRACE_METRICS[1]: float(np.max(np.abs(err))),
    }


def summarize_run(run_dir, data_dir):
    with open(os.path.join(run_dir, "run.json")) as f:
        run = json.load(f)

    rows = []
    for case_id, status in run["cases"].items():
        with open(truth_path(data_dir, case_id)) as f:
            truth = json.load(f)["truth"]
        case_dir = os.path.join(run_dir, case_id)
        results_csv = os.path.join(case_dir, f"{case_id}-results.csv")
        results = (
            pd.read_csv(results_csv).iloc[0].to_dict()
            if status["status"] == "ok" and os.path.exists(results_csv)
            else {}
        )

        for metric, expected in truth.items():
            measured = results.get(metric, np.nan)
            err = measured - expected
            unc = results.get(UNCERTAINTY.get(metric), np.nan)
            rows.append({
                "case": case_id,
                "metric": metric,
                "truth": expected,
                "measured": measured,
                "error": err,
                "rel_error": err / expected if expected else np.nan,
                "ok": results.get(PHASE_FLAG.get(metric, "Velocity OK"), np.nan),
                "uncertainty": unc,
                "covered": bool(abs(err) <= unc) if np.isfinite(err) and np.isfinite(unc) else np.nan,
            })

        for metric, value in trace_errors(case_dir, case_id, data_dir).items():
            rows.append({
                "case": case_id, "metric": metric, "truth": 0.0, "measured": value,
                "error": value, "rel_error": np.nan,
                "ok": results.get("Velocity OK", np.nan),
                "uncertainty": np.nan, "covered": np.nan,
            })

    return run, pd.DataFrame(rows)


def compare(current, baseline):
    """Per case/metric |error| in both runs and which one is closer to truth."""
    keys = ["case", "metric"]
    merged = baseline[keys + ["truth", "error"]].merge(
        current[keys + ["error"]], on=keys, how="outer", suffixes=("_baseline", "_current")
    )

    def score(row, column):
        # relative error where the truth is non-zero, absolute otherwise
        err = abs(row[column])
        return err / abs(row["truth"]) if row["truth"] else err

    verdicts = []
    for _, row in merged.iterrows():
        b, c = score(row, "error_baseline"), score(row, "error_current")
        if np.isnan(b) and np.isnan(c):
            verdicts.append("both missing")
        elif np.isnan(c):
            verdicts.append("lost")
        elif np.isnan(b):
            verdicts.append("gained")
        elif abs(c - b) <= 1e-3 * max(b, 1e-12) + 1e-12:
            verdicts.append("same")
        else:
            verdicts.append("better" if c < b else "worse")
    merged["verdict"] = verdicts
    return merged


def fmt(value):
    if isinstance(value, (bool, np.bool_)):
        return "yes" if value else "no"
    if isinstance(value, (float, np.floating)):
        if np.isnan(value):
            return "-"
        return f"{value:.4g}"
    return str(value)


def to_markdown(df, columns):
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[c]) for c in columns) + " |")
    return "\n".join(lines)


def run_header(run):
    git = run["git"]
    overrides = ", ".join(f"{k}={v}" for k, v in run["overrides"].items()) or "none"
    return (
        f"**{run['label']}**: alpss {run['alpss_version']}, "
        f"{git['branch']} @ {git['sha'][:8]}{' (dirty)' if git['dirty'] else ''}, "
        f"overrides: {overrides}, run {run['started']}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir")
    parser.add_argument("--against", help="baseline run directory to compare with")
    parser.add_argument("--data", default=DATA_DIR)
    args = parser.parse_args()

    run, summary = summarize_run(args.run_dir, args.data)
    columns = ["case", "metric", "truth", "measured", "error", "rel_error",
               "ok", "uncertainty", "covered"]
    summary.to_csv(os.path.join(args.run_dir, "summary.csv"), index=False)

    failed = {c: s["error"] for c, s in run["cases"].items() if s["status"] != "ok"}
    body = [f"# Benchmark summary\n\n{run_header(run)}\n"]
    if failed:
        body.append("Failed cases:\n" + "\n".join(f"- {c}: {e}" for c, e in failed.items()) + "\n")
    body.append(to_markdown(summary, columns))
    report = "\n".join(body) + "\n"

    if args.against:
        base_run, base_summary = summarize_run(args.against, args.data)
        comparison = compare(summary, base_summary)
        name = os.path.basename(os.path.normpath(args.against))
        comparison.to_csv(os.path.join(args.run_dir, f"comparison_vs_{name}.csv"), index=False)
        counts = comparison["verdict"].value_counts().to_dict()
        report += (
            f"\n# Comparison\n\ncurrent: {run_header(run)}\n\n"
            f"baseline: {run_header(base_run)}\n\n"
            + ", ".join(f"{k}: {v}" for k, v in counts.items()) + "\n\n"
            + to_markdown(comparison, ["case", "metric", "truth", "error_baseline",
                                       "error_current", "verdict"])
            + "\n"
        )

    with open(os.path.join(args.run_dir, "summary.md"), "w") as f:
        f.write(report)
    print(report)
    print(f"wrote {os.path.relpath(os.path.join(args.run_dir, 'summary.md'), REPO_ROOT)}")


if __name__ == "__main__":
    main()
