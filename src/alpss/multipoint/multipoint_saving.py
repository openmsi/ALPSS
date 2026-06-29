import os
import pandas as pd

_SERIES = [
    ("velocity",        1, "{base}-velocity.csv"),
    ("smooth_velocity", 1, "{base}-velocity--smooth.csv"),
    ("displacement",    1, "{base}-displacement.csv"),
    ("noise",           1, "{base}-noisefrac.csv"),
    ("vel_uncert",      1, "{base}-veluncert.csv"),
]


def save_combined_series(results, probe_numbers, filepath, out_files_dir):
    """Merge per-probe arrays into wide-format CSVs.

    One CSV per data type; columns are [time, probe_N, probe_M, ...].
    Uses an outer join on the time column — no interpolation needed since all
    probes share the same underlying time grid.
    """
    base = os.path.splitext(os.path.basename(filepath))[0]
    base_path = os.path.join(out_files_dir, base)

    for items_key, col_idx, path_template in _SERIES:
        frames = []
        for probe_num, result in zip(probe_numbers, results):
            if result is None:
                continue
            _, items = result
            arr = items[items_key][0]
            frames.append(pd.DataFrame({
                "time": arr[:, 0],
                f"probe_{probe_num}": arr[:, col_idx],
            }))
        if not frames:
            continue
        merged = frames[0]
        for df in frames[1:]:
            merged = pd.merge(merged, df, on="time", how="outer")
        merged.to_csv(path_template.format(base=base_path), index=False)

    # voltage has two data columns per probe (real and imaginary)
    volt_frames = []
    for probe_num, result in zip(probe_numbers, results):
        if result is None:
            continue
        _, items = result
        arr = items["voltage"][0]
        volt_frames.append(pd.DataFrame({
            "time": arr[:, 0],
            f"probe_{probe_num}_real": arr[:, 1],
            f"probe_{probe_num}_imag": arr[:, 2],
        }))
    if volt_frames:
        merged_volt = volt_frames[0]
        for df in volt_frames[1:]:
            merged_volt = pd.merge(merged_volt, df, on="time", how="outer")
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
