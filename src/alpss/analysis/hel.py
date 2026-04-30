"""HEL (Hugoniot Elastic Limit) detection for PDV velocity traces.

Two detection methods are available:

* **Gradient / angle-based** (original, :func:`hel_detection`):
    Smoothed gradient converted to angles; first consecutive low-slope
    segment is taken as the HEL plateau.  Selected by ``method="gradient"``.

* **RDP + Linear Hybrid** (new, matches HELIX Toolbox v2):
    Ramer–Douglas–Peucker simplification to find candidate "knee" points,
    followed by linear regression on the *raw* data for the rise segment
    and the plateau segment.  Physics gating (slope-drop ratio, minimum
    plateau duration, minimum velocity) filters false positives.
    Selected by ``method="rdp_linear"`` or as the default when
    ``hel_slope_drop_ratio`` is provided.
    Documented in ``HEL_DETECTION_ALGORITHM.md`` of HELIX Toolbox.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.stats import linregress
from dataclasses import dataclass, field
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
    error_message: str | None = None
    # Internal data for plotting (gradient method)
    segment_start_idx: int | None = None
    segment_end_idx: int | None = None
    time_window: np.ndarray | None = None
    velocity_window: np.ndarray | None = None
    gradient_smooth: np.ndarray | None = None
    angles_deg: np.ndarray | None = None
    # Extra fields populated by the RDP + Linear Hybrid method
    method: str = "gradient"
    rise_slope: float = np.nan       # [m/s per ns] slope of the rise segment
    plateau_slope: float = np.nan    # [m/s per ns] slope of the plateau segment
    rdp_knee_time_ns: float = np.nan # time of the RDP knee point [ns]
    rdp_points: np.ndarray | None = None  # simplified vertices for visualisation


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
    hel_start_ns,
    hel_end_ns,
    angle_threshold_deg,
    min_points,
    min_velocity,
    density,
    acoustic_velocity,
    C_L,
    # RDP + Linear Hybrid parameters (ignored when method="gradient")
    method: str,
    hel_rdp_epsilon: float,
    hel_slope_drop_ratio: float,
    hel_min_plateau_duration: float,
):
    """
    Detect the Hugoniot Elastic Limit (HEL) from a velocity trace.

    Parameters
    ----------
    method : str
        ``"gradient"`` (default, original) or ``"rdp_linear"`` (RDP + Linear
        Hybrid from HELIX Toolbox v2).  When ``"rdp_linear"`` is requested
        the gradient-based fall-back is attempted automatically if the hybrid
        method fails.

    .. rubric:: Gradient method parameters

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
    # Delegate to RDP + Linear Hybrid when requested
    if method == "rdp_linear":
        return hel_detection_rdp_hybrid(
            time_ns, velocity, uncertainty,
            hel_start_ns=hel_start_ns,
            hel_end_ns=hel_end_ns,
            min_velocity=min_velocity,
            density=density,
            acoustic_velocity=acoustic_velocity,
            C_L=C_L,
            rdp_epsilon=hel_rdp_epsilon,
            slope_drop_ratio=hel_slope_drop_ratio,
            min_plateau_duration_ns=hel_min_plateau_duration,
            min_points=min_points,
        )

    time_ns = np.asarray(time_ns, dtype=float)
    velocity = np.asarray(velocity, dtype=float)
    uncertainty = np.asarray(uncertainty, dtype=float)

    # Step 1: Filter out NaN and high-uncertainty points
    valid_mask = ~np.isnan(velocity)
    if np.sum(valid_mask) <= 5:
        raise ValueError("insufficient valid data points for HEL")

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
        raise ValueError("insufficient data points in HEL search window")

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
        msg = "no qualifying HEL plateau found"
        logger.info(msg)
        return HELResult(
            ok=False,
            error_message=msg,
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
        msg = f"rejected - HEL detected velocity < threshold {min_velocity:.1f} m/s"
        logger.info(msg)
        return HELResult(
            ok=False,
            error_message=msg,
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
        method="gradient",
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


# ---------------------------------------------------------------------------
# RDP + Linear Hybrid HEL detection (HELIX Toolbox v2 algorithm)
# ---------------------------------------------------------------------------

def _rdp_hel(points: np.ndarray, epsilon: float) -> np.ndarray:
    """RDP simplification returning kept indices (shared with spall module)."""
    if len(points) < 3:
        return np.arange(len(points))

    def _perp(pt, s, e):
        if np.allclose(s, e):
            return np.linalg.norm(pt - s)
        d = e - s
        proj = s + np.dot(pt - s, d) / np.dot(d, d) * d
        return np.linalg.norm(pt - proj)

    def _rec(pts, eps, off=0):
        if len(pts) < 3:
            return list(range(off, off + len(pts)))
        dists = [_perp(pts[i], pts[0], pts[-1]) for i in range(1, len(pts) - 1)]
        mx = max(dists)
        mi = dists.index(mx) + 1
        if mx > eps:
            L = _rec(pts[: mi + 1], eps, off)
            R = _rec(pts[mi:], eps, off + mi)
            return L[:-1] + R
        return [off, off + len(pts) - 1]

    return np.array(sorted(set(_rec(points, epsilon))))


def hel_detection_rdp_hybrid(
    time_ns,
    velocity,
    uncertainty,
    *,
    hel_start_ns: float,
    hel_end_ns: float | None,
    min_velocity: float,
    density: float | None,
    acoustic_velocity: float | None,
    C_L: float | None,
    rdp_epsilon: float,
    slope_drop_ratio: float,
    min_plateau_duration_ns: float,
    min_points: int,
) -> HELResult:
    """RDP + Linear Hybrid HEL detection (HELIX Toolbox v2 algorithm).

    This method is more robust than the gradient approach because it fits
    linear regressions on the *raw* data rather than on a smoothed gradient,
    and applies explicit physics gating criteria.

    Algorithm
    ---------
    1. **Time-zero alignment**: clip data to ``[hel_start_ns, hel_end_ns]``.
    2. **Uncertainty filtering**: discard points where ``|unc|/max|vel| ≥ 1``.
    3. **RDP simplification**: obtain candidate knee points.
    4. For each candidate knee point:

       a. Fit a line to the *rise* segment (raw data before the knee).
       b. Fit a line to the *plateau* segment (raw data after the knee).
       c. Physics validation:

          * Rise slope must be positive.
          * ``plateau_slope < (1 − slope_drop_ratio) × rise_slope``
            (default: plateau slope < 10 % of rise slope).
          * Plateau must last ≥ ``min_plateau_duration_ns`` ns.
          * Plateau mean velocity must exceed ``min_velocity``.
          * Elastic strain rate must be positive.

    5. Accept the first knee that passes all checks.

    Parameters
    ----------
    time_ns:
        Time array in **nanoseconds**.
    velocity:
        Smoothed velocity array  [m/s].
    uncertainty:
        Velocity uncertainty array  [m/s].
    hel_start_ns, hel_end_ns:
        Search window  [ns].
    min_velocity:
        Minimum accepted HEL plateau velocity  [m/s].
    density:
        Material density  [kg/m³] — needed for stress output.
    acoustic_velocity:
        Bulk wave speed  [m/s] — needed for stress output.
    C_L:
        Longitudinal wave speed  [m/s] — used for strain rate;
        falls back to ``acoustic_velocity``.
    rdp_epsilon:
        RDP tolerance  [m/s].
    slope_drop_ratio:
        Fraction of rise slope that the plateau slope must fall below.
        E.g. 0.9 means ``|plateau_slope| < 10 %`` of ``|rise_slope|``.
    min_plateau_duration_ns:
        Minimum plateau duration  [ns].
    min_points:
        Minimum number of raw data points in the plateau segment.

    Returns
    -------
    HELResult
        Falls back to ``hel_detection(..., method="gradient")`` if no knee
        passes the physics checks.
    """
    time_ns = np.asarray(time_ns, dtype=float)
    velocity = np.asarray(velocity, dtype=float)
    uncertainty = np.asarray(uncertainty, dtype=float)

    # ------------------------------------------------------------------ #
    # 1–2  Filter + window                                                  #
    # ------------------------------------------------------------------ #
    valid = ~np.isnan(velocity)
    if valid.sum() <= 5:
        return HELResult(ok=False, error_message="insufficient valid data for HEL (RDP method)")

    t_c = time_ns[valid]
    v_c = velocity[valid]
    u_c = uncertainty[valid]

    max_v = np.max(np.abs(v_c))
    rel_unc = np.abs(u_c) / max(max_v, 1e-9)
    good = rel_unc < 1.0
    if good.sum() >= 10:
        t_c, v_c, u_c = t_c[good], v_c[good], u_c[good]

    win = t_c >= hel_start_ns
    if hel_end_ns is not None and hel_end_ns > hel_start_ns:
        win &= t_c <= hel_end_ns
    if win.sum() < 10:
        win = np.ones(len(t_c), dtype=bool)

    t_w, v_w, u_w = t_c[win], v_c[win], u_c[win]
    if len(t_w) < 10:
        return HELResult(ok=False, method="rdp_linear",
                         error_message="insufficient data in HEL window (RDP method)")

    # ------------------------------------------------------------------ #
    # 3  RDP simplification                                                 #
    # ------------------------------------------------------------------ #
    pts = np.column_stack((t_w, v_w))
    rdp_idx = _rdp_hel(pts, rdp_epsilon)
    rdp_pts = pts[rdp_idx]

    if len(rdp_pts) < 3:
        return HELResult(ok=False, method="rdp_linear",
                         error_message="RDP produced fewer than 3 vertices — trace too smooth")

    # ------------------------------------------------------------------ #
    # 4  Candidate knee scan                                                #
    # ------------------------------------------------------------------ #
    if C_L is None:
        C_L = acoustic_velocity

    best: HELResult | None = None

    for ki in range(1, len(rdp_pts) - 1):
        knee_t = float(rdp_pts[ki, 0])

        # Rise segment: raw points up to and including the knee
        rise_mask = t_w <= knee_t
        plat_mask = t_w >= knee_t
        if rise_mask.sum() < 3 or plat_mask.sum() < min_points:
            continue

        # Linear fit on raw data
        try:
            r_slope, _, _, _, _ = linregress(t_w[rise_mask], v_w[rise_mask])
            p_slope, _, _, _, _ = linregress(t_w[plat_mask], v_w[plat_mask])
        except Exception:
            continue

        # Physics gate: positive rise, flat/negative plateau
        if r_slope <= 0:
            continue
        if abs(p_slope) >= (1.0 - slope_drop_ratio) * abs(r_slope):
            continue

        # Plateau duration
        plat_duration = float(t_w[plat_mask][-1] - t_w[plat_mask][0])
        if plat_duration < min_plateau_duration_ns:
            continue

        # HEL velocity (mean of plateau raw data)
        fsv = float(np.mean(v_w[plat_mask]))
        if abs(fsv) < min_velocity:
            continue

        # Strain rate (must be positive)
        if C_L is not None:
            # reference point: first window sample
            U_0 = float(v_w[0])
            t_0 = float(t_w[0])
            sr = elastic_shock_strain_rate(C_L, fsv, U_0, knee_t, t_0)
            if sr <= 0:
                continue
        else:
            sr = np.nan

        # Uncertainty: mean uncertainty of plateau raw points
        u_unc = float(np.mean(np.abs(u_w[plat_mask])))

        # Stress
        strength_gpa = np.nan
        unc_gpa = np.nan
        if density is not None and acoustic_velocity is not None:
            strength_gpa = 0.5 * density * acoustic_velocity * abs(fsv) / 1e9
            unc_gpa = 0.5 * density * acoustic_velocity * u_unc / 1e9

        best = HELResult(
            ok=True,
            method="rdp_linear",
            strength_gpa=strength_gpa,
            uncertainty_gpa=unc_gpa,
            free_surface_velocity=fsv,
            time_detection_ns=knee_t,
            consecutive_points=int(plat_mask.sum()),
            segment_duration_ns=plat_duration,
            strain_rate=sr,
            rise_slope=float(r_slope),
            plateau_slope=float(p_slope),
            rdp_knee_time_ns=knee_t,
            rdp_points=rdp_pts,
            time_window=t_w,
            velocity_window=v_w,
        )
        break  # accept first valid knee

    if best is not None:
        logger.info(
            "[RDP-Linear] HEL %.3f GPa at %.1f ns (rise=%.2f, plateau=%.2f m/s/ns)",
            best.strength_gpa,
            best.time_detection_ns,
            best.rise_slope,
            best.plateau_slope,
        )
        return best

    # ------------------------------------------------------------------ #
    # 5  Fall back to gradient method                                       #
    # ------------------------------------------------------------------ #
    logger.info("[RDP-Linear] No valid HEL knee found — falling back to gradient method")
    result = hel_detection(
        time_ns, velocity, uncertainty,
        hel_start_ns=hel_start_ns,
        hel_end_ns=hel_end_ns,
        min_velocity=min_velocity,
        density=density,
        acoustic_velocity=acoustic_velocity,
        C_L=C_L,
        method="gradient",
    )
    if not result.ok and result.error_message and "rdp" not in result.error_message.lower():
        result.error_message = "RDP+Linear: no valid knee; gradient fallback: " + (result.error_message or "no plateau")
    result.method = "gradient_fallback"
    return result
