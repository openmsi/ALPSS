import os

import numpy as np
import pandas as pd

# per-probe series that get merged into one wide CSV each. The tuple is
# (key in the items dict, column of the array holding the values, filename)
_SERIES = [
    ("velocity", 1, "{base}-velocity.csv"),
    ("smooth_velocity", 1, "{base}-velocity--smooth.csv"),
    ("noise", 1, "{base}-noisefrac.csv"),
    ("vel_uncert", 1, "{base}-veluncert.csv"),
]


def _interp_to_reference(ref_time, probe_time, probe_values):
    """Resample probe_values onto ref_time, NaN outside the probe's own range.

    Probes are clipped to their own domain of interest, so they do not share a
    time axis. Putting them on one axis is what makes probe-to-probe comparison
    possible.
    """
    return np.interp(ref_time, probe_time, probe_values, left=np.nan, right=np.nan)


def combine_probes(results, probe_numbers, filepath, out_files_dir):
    """Merge per-probe outputs into wide CSVs on a single shared time axis.

    One CSV per data type, columns [time, probe_N, probe_M, ...]. The time axis
    is the first successful probe's; every other probe is interpolated onto it.
    Failed probes (None) are skipped.
    """
    base = os.path.splitext(os.path.basename(filepath))[0]
    base_path = os.path.join(out_files_dir, base)
    os.makedirs(out_files_dir, exist_ok=True)
    written = []

    for items_key, col_idx, path_template in _SERIES:
        ref_time = None
        columns = {}
        for probe_num, result in zip(probe_numbers, results):
            if result is None:
                continue
            arr = result[1][items_key][0]
            if ref_time is None:
                ref_time = arr[:, 0]
                columns[f"probe_{probe_num}"] = arr[:, col_idx]
            else:
                columns[f"probe_{probe_num}"] = _interp_to_reference(
                    ref_time, arr[:, 0], arr[:, col_idx]
                )
        if ref_time is None:
            continue
        path = path_template.format(base=base_path)
        pd.DataFrame({"time": ref_time, **columns}).to_csv(path, index=False)
        written.append(path)

    # voltage carries two value columns per probe (real and imaginary)
    ref_time = None
    volt_columns = {}
    for probe_num, result in zip(probe_numbers, results):
        if result is None:
            continue
        arr = result[1]["voltage"][0]
        if ref_time is None:
            ref_time = arr[:, 0]
            volt_columns[f"probe_{probe_num}_real"] = arr[:, 1]
            volt_columns[f"probe_{probe_num}_imag"] = arr[:, 2]
        else:
            for suffix, col in (("real", 1), ("imag", 2)):
                volt_columns[f"probe_{probe_num}_{suffix}"] = _interp_to_reference(
                    ref_time, arr[:, 0], arr[:, col]
                )
    if ref_time is not None:
        path = f"{base_path}-voltage.csv"
        pd.DataFrame({"time": ref_time, **volt_columns}).to_csv(path, index=False)
        written.append(path)

    # results and inputs are one row per probe rather than one column
    for items_key, path_template in (
        ("results", "{base}-results.csv"),
        ("inputs", "{base}-inputs.csv"),
    ):
        frames = []
        for probe_num, result in zip(probe_numbers, results):
            if result is None:
                continue
            obj = result[1][items_key][0]
            df = pd.DataFrame([obj]) if isinstance(obj, dict) else obj.copy()
            df.insert(0, "probe_number", probe_num)
            frames.append(df)
        if frames:
            path = path_template.format(base=base_path)
            pd.concat(frames, ignore_index=True).to_csv(path, index=False)
            written.append(path)

    return written
