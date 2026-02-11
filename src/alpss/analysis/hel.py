from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter1d
from dataclasses import dataclass
import logging

logger = logging.getLogger("alpss")


@dataclass
class HELResult:
    """Result of Hugoniot Elastic Limit detection."""

    ok: bool
    strength_gpa: float = np.nan
    uncertainty_gpa: float = np.nan
    free_surface_velocity: float = np.nan
    time_detection_ns: float = np.nan
    consecutive_points: int = 0
    segment_duration_ns: float = np.nan
    strain_rate: float = np.nan
    # Internal data for plotting
    segment_start_idx: int | None = None
    segment_end_idx: int | None = None
    time_window: np.ndarray | None = None
    velocity_window: np.ndarray | None = None
    gradient_smooth: np.ndarray | None = None
    angles_deg: np.ndarray | None = None


def elastic_shock_strain_rate(C_L, U_hel, U_0, t_hel, t_0):
    """
    Compute elastic shock strain rate.

    Parameters
    ----------
    C_L : float
        Longitudinal wave velocity of the material (m/s).
    U_hel : float
        Free surface velocity at HEL (m/s).
    U_0 : float
        Free surface velocity at t=0 (m/s).
    t_hel : float
        Time at which U_hel is measured (s or ns — units must match t_0).
    t_0 : float
        Initial time (same units as t_hel).

    Returns
    -------
    float
        Elastic shock strain rate (1/s if times are in seconds, 1/ns if in ns).
    """
    dt = t_hel - t_0
    if dt <= 0:
        return np.nan
    return (1 / (2 * C_L)) * ((U_hel - U_0) / dt)


def hel_detection(
    time_ns,
    velocity,
    uncertainty,
    *,
    hel_start_ns=0.0,
    hel_end_ns=None,
    angle_threshold_deg=45.0,
    min_points=3,
    min_velocity=10.0,
    density=None,
    acoustic_velocity=None,
    C_L=None,
):
    """
    Detect the Hugoniot Elastic Limit (HEL) from a velocity trace.

    Uses a gradient-based method to find the earliest low-slope plateau
    in the velocity signal within a specified time window.

    Parameters
    ----------
    time_ns : array_like
        Time array in nanoseconds.
    velocity : array_like
        Velocity array in m/s (smoothed recommended).
    uncertainty : array_like
        Velocity uncertainty array in m/s.
    hel_start_ns : float
        Start of the HEL search window in ns. Default 0.0.
    hel_end_ns : float or None
        End of the HEL search window in ns. None uses full range.
    angle_threshold_deg : float
        Maximum angle (degrees) for a segment to be considered a plateau.
        Default 45.0.
    min_points : int
        Minimum consecutive low-slope points to qualify as a plateau.
        Default 3.
    min_velocity : float
        Minimum HEL velocity (m/s) to accept the detection. Default 10.0.
    density : float or None
        Material density in kg/m³. Required for HEL stress calculation.
    acoustic_velocity : float or None
        Bulk wave speed in m/s. Required for HEL stress calculation.
    C_L : float or None
        Longitudinal wave velocity in m/s. Used for strain rate.
        Falls back to acoustic_velocity if not provided.

    Returns
    -------
    HELResult
        Dataclass with detection results and internal data for plotting.
    """
    time_ns = np.asarray(time_ns, dtype=float)
    velocity = np.asarray(velocity, dtype=float)
    uncertainty = np.asarray(uncertainty, dtype=float)

    # Step 1: Filter out NaN and high-uncertainty points
    valid_mask = ~np.isnan(velocity)
    if np.sum(valid_mask) <= 5:
        logger.warning("HEL: insufficient valid data points")
        return HELResult(ok=False)

    time_clean = time_ns[valid_mask]
    vel_clean = velocity[valid_mask]
    unc_clean = uncertainty[valid_mask]

    # Filter by relative uncertainty (|unc| / max|vel|) >= 1.0 → noise
    max_vel = np.max(np.abs(vel_clean))
    rel_unc = np.abs(unc_clean) / max(max_vel, 1e-9)
    noise_mask = rel_unc < 1.0
    if np.sum(noise_mask) < 10:
        noise_mask = np.ones(len(vel_clean), dtype=bool)

    time_clean = time_clean[noise_mask]
    vel_clean = vel_clean[noise_mask]
    unc_clean = unc_clean[noise_mask]

    # Step 2: Apply HEL time window
    search_mask = time_clean >= hel_start_ns
    if hel_end_ns is not None and hel_end_ns > hel_start_ns:
        search_mask &= time_clean <= hel_end_ns
    if np.sum(search_mask) < 10:
        search_mask = np.ones(len(time_clean), dtype=bool)

    t_win = time_clean[search_mask]
    v_win = vel_clean[search_mask]
    u_win = unc_clean[search_mask]

    if len(t_win) < 10:
        logger.warning("HEL: insufficient data points in search window")
        return HELResult(ok=False)

    # Step 3: Compute smoothed gradient and convert to angles
    gradient = np.gradient(v_win, t_win)
    window_size = max(3, min(5, len(gradient) // 3))
    if window_size % 2 == 0:
        window_size += 1
    gradient_smooth = uniform_filter1d(gradient, size=window_size, mode="nearest")
    angles_deg = np.degrees(np.arctan(np.abs(gradient_smooth)))

    # Step 4: Find consecutive low-slope segments
    low_slope = angles_deg < angle_threshold_deg
    seg_start = None
    seg_end = None

    in_segment = False
    current_start = None
    for i, is_low in enumerate(low_slope):
        if is_low and not in_segment:
            current_start = i
            in_segment = True
        elif not is_low and in_segment:
            if (i - current_start) >= min_points and seg_start is None:
                seg_start = current_start
                seg_end = i - 1
            in_segment = False
            current_start = None

    # Handle segment extending to end of array
    if in_segment and current_start is not None:
        length = len(low_slope) - current_start
        if length >= min_points and seg_start is None:
            seg_start = current_start
            seg_end = len(low_slope) - 1

    # Step 5: Extract HEL properties from earliest plateau
    if seg_start is None or seg_end is None:
        logger.info("HEL: no qualifying plateau found")
        return HELResult(
            ok=False,
            time_window=t_win,
            velocity_window=v_win,
            gradient_smooth=gradient_smooth,
            angles_deg=angles_deg,
        )

    seg_indices = np.arange(seg_start, seg_end + 1)
    fsv = np.mean(v_win[seg_indices])  # free surface velocity
    hel_time = t_win[seg_start]
    n_points = len(seg_indices)
    seg_duration = t_win[seg_end] - t_win[seg_start]

    # Uncertainty at the point closest to the mean velocity in the segment
    closest_idx = seg_indices[np.argmin(np.abs(v_win[seg_indices] - fsv))]
    u_unc = abs(u_win[closest_idx])

    # Step 6: Validate minimum velocity
    if abs(fsv) < min_velocity:
        logger.info(
            "HEL rejected: detected velocity %.2f m/s below threshold %.1f m/s",
            abs(fsv),
            min_velocity,
        )
        return HELResult(
            ok=False,
            free_surface_velocity=fsv,
            time_detection_ns=hel_time,
            consecutive_points=n_points,
            segment_duration_ns=seg_duration,
            segment_start_idx=seg_start,
            segment_end_idx=seg_end,
            time_window=t_win,
            velocity_window=v_win,
            gradient_smooth=gradient_smooth,
            angles_deg=angles_deg,
        )

    # Compute HEL stress if material properties are provided
    strength_gpa = np.nan
    uncertainty_gpa = np.nan
    if density is not None and acoustic_velocity is not None:
        strength_gpa = 0.5 * density * acoustic_velocity * abs(fsv) / 1e9
        uncertainty_gpa = 0.5 * density * acoustic_velocity * u_unc / 1e9

    # Compute strain rate if C_L is available
    strain_rate = np.nan
    if C_L is None:
        C_L = acoustic_velocity
    if C_L is not None:
        # Use the point just before the segment as reference, or the first
        # window point if the segment starts at index 0
        if seg_start > 0:
            U_0 = v_win[seg_start - 1]
            t_0 = t_win[seg_start - 1]
        else:
            U_0 = v_win[0]
            t_0 = t_win[0]
        strain_rate = elastic_shock_strain_rate(C_L, fsv, U_0, hel_time, t_0)

    logger.info(
        "HEL detected: %.3f GPa at %.1f ns (%d points, %.3f ns duration)",
        strength_gpa,
        hel_time,
        n_points,
        seg_duration,
    )

    return HELResult(
        ok=True,
        strength_gpa=strength_gpa,
        uncertainty_gpa=uncertainty_gpa,
        free_surface_velocity=fsv,
        time_detection_ns=hel_time,
        consecutive_points=n_points,
        segment_duration_ns=seg_duration,
        strain_rate=strain_rate,
        segment_start_idx=seg_start,
        segment_end_idx=seg_end,
        time_window=t_win,
        velocity_window=v_win,
        gradient_smooth=gradient_smooth,
        angles_deg=angles_deg,
    )
