import os
import numpy as np
import pandas as pd

_SERIES = [
    ("velocity",        1, "{base}-velocity.csv"),
    ("smooth_velocity", 1, "{base}-velocity--smooth.csv"),
    ("displacement",    1, "{base}-displacement.csv"),
    ("noise",           1, "{base}-noisefrac.csv"),
    ("vel_uncert",      1, "{base}-veluncert.csv"),
]


def _interp_to_reference(ref_time, probe_time, probe_values):
    """Linearly interpolate probe_values (sampled at probe_time) onto ref_time.
    NaN outside [probe_time.min(), probe_time.max()]."""
    return np.interp(ref_time, probe_time, probe_values, left=np.nan, right=np.nan)


def save_combined_series(results, probe_numbers, filepath, out_files_dir):
    """Merge per-probe arrays into wide-format CSVs on a single shared time axis.

    One CSV per data type; columns are [time, probe_N, probe_M, ...]. The
    time axis is the first successful probe's own time array; every other
    probe's series is linearly interpolated onto it (NaN outside that
    probe's own time range).
    """
    base = os.path.splitext(os.path.basename(filepath))[0]
    base_path = os.path.join(out_files_dir, base)

    for items_key, col_idx, path_template in _SERIES:
        ref_time = None
        columns = {}
        for probe_num, result in zip(probe_numbers, results):
            if result is None:
                continue
            _, items = result
            arr = items[items_key][0]
            if ref_time is None:
                ref_time = arr[:, 0]
                columns[f"probe_{probe_num}"] = arr[:, col_idx]
            else:
                columns[f"probe_{probe_num}"] = _interp_to_reference(
                    ref_time, arr[:, 0], arr[:, col_idx]
                )
        if ref_time is None:
            continue
        merged = pd.DataFrame({"time": ref_time, **columns})
        merged.to_csv(path_template.format(base=base_path), index=False)

    # voltage has two data columns per probe (real and imaginary)
    ref_time = None
    volt_columns = {}
    for probe_num, result in zip(probe_numbers, results):
        if result is None:
            continue
        _, items = result
        arr = items["voltage"][0]
        if ref_time is None:
            ref_time = arr[:, 0]
            volt_columns[f"probe_{probe_num}_real"] = arr[:, 1]
            volt_columns[f"probe_{probe_num}_imag"] = arr[:, 2]
        else:
            volt_columns[f"probe_{probe_num}_real"] = _interp_to_reference(
                ref_time, arr[:, 0], arr[:, 1]
            )
            volt_columns[f"probe_{probe_num}_imag"] = _interp_to_reference(
                ref_time, arr[:, 0], arr[:, 2]
            )
    if ref_time is not None:
        merged_volt = pd.DataFrame({"time": ref_time, **volt_columns})
        merged_volt.to_csv(f"{base_path}-voltage.csv", index=False)

    # inputs: one row per probe, probe_number as first column
    inputs_frames = []
    for probe_num, result in zip(probe_numbers, results):
        if result is None:
            continue
        _, items = result
        df = items["inputs"][0].copy()
        df.insert(0, "probe_number", probe_num)
        inputs_frames.append(df)
    if inputs_frames:
        pd.concat(inputs_frames, ignore_index=True).to_csv(
            f"{base_path}-inputs.csv", index=False
        )

    # results: one row per probe, probe_number as first column
    results_frames = []
    for probe_num, result in zip(probe_numbers, results):
        if result is None:
            continue
        _, items = result
        df = pd.DataFrame([items["results"][0]])
        df.insert(0, "probe_number", probe_num)
        results_frames.append(df)
    if results_frames:
        pd.concat(results_frames, ignore_index=True).to_csv(
            f"{base_path}-results.csv", index=False
        )
