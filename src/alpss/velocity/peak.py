import numpy as np
from scipy import signal


def compute_velocity_peaks(velocity_f_smooth, time_f, pb_neighbors, pb_idx_correction, rc_neighbors, rc_idx_correction):
    """Compute velocity peak metrics from the smoothed velocity signal.

    Returns a dict with:
    - peak_velocity_idx: index of maximum velocity
    - v_max_comp: maximum compression velocity
    - t_max_comp: time at maximum compression
    - max_ten_idx: index of maximum tension (first local min after peak)
    - v_max_ten: maximum tension velocity
    - t_max_ten: time at maximum tension
    - rc_idx: index of recompression (first local max after tension)
    - v_rc: recompression velocity
    - t_rc: time at recompression
    """
    peak_velocity_idx = int(np.argmax(velocity_f_smooth))
    v_max_comp = velocity_f_smooth[peak_velocity_idx]
    t_max_comp = time_f[peak_velocity_idx]

    # Find max tension: first local minimum after the peak velocity
    rel_min_idx = signal.argrelmin(velocity_f_smooth, order=pb_neighbors)[0]
    extrema_min = np.append(rel_min_idx, peak_velocity_idx)
    extrema_min.sort()
    _max_ten_pos = np.where(extrema_min == peak_velocity_idx)[0][0] + 1 + pb_idx_correction

    if _max_ten_pos >= len(extrema_min):
        raise ValueError("no local minimum found after peak velocity (no spall pullback detected)")
    max_ten_idx = extrema_min[_max_ten_pos]

    # Find recompression: first local maximum after tension
    rel_max_idx = signal.argrelmax(velocity_f_smooth, order=rc_neighbors)[0]
    extrema_max = np.append(rel_max_idx, peak_velocity_idx)
    extrema_max.sort()
    _rc_pos = np.where(extrema_max == peak_velocity_idx)[0][0] + 2 + rc_idx_correction

    if _rc_pos >= len(extrema_max):
        raise ValueError("no local maximum found after pullback (no recompression detected)")
    rc_idx = extrema_max[_rc_pos]

    return {
        "peak_velocity_idx": peak_velocity_idx,
        "v_max_comp": v_max_comp,
        "t_max_comp": t_max_comp,
        "max_ten_idx": max_ten_idx,
        "v_max_ten": velocity_f_smooth[max_ten_idx],
        "t_max_ten": time_f[max_ten_idx],
        "rc_idx": rc_idx,
        "v_rc": velocity_f_smooth[rc_idx],
        "t_rc": time_f[rc_idx],
    }
