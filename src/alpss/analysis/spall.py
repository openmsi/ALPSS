"""Spall analysis for PDV velocity traces.

This module contains two levels of analysis:

* :func:`spall_analysis` — original peak/valley finder (unchanged, backward-compatible).
* :func:`spall_analysis_with_dns` — extended version that adds:
    - RDP topology check ("checkmark" Plateau→Pullback→Rebound scanner)
    - DNS (Did Not Spall) qualification
    - :class:`SpallResult` return type with structured fields

The RDP topology approach is ported from HELIX Toolbox v2 (Wanchoo, 2026) and
mirrors the algorithm documented in ``SPALL_DETECTION_ALGORITHM.md``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from scipy import signal

logger = logging.getLogger("alpss")


# ---------------------------------------------------------------------------
# SpallResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class SpallResult:
    """Structured return type for :func:`spall_analysis_with_dns`.

    Attributes
    ----------
    ok : bool
        ``True`` if a valid spall event was detected.
    dns_classification : str
        ``"Valid Spall"`` or a string explaining why the event is DNS.
    spall_strength_pa : float
        Spall strength in **Pa** (divide by 1e9 for GPa).
    spall_strength_unc_pa : float
        1-σ uncertainty in Pa.
    strain_rate : float
        Spall strain rate  [s⁻¹].
    peak_velocity : float
        Peak (plateau) free-surface velocity  [m/s].
    pullback_velocity : float
        |v_peak − v_min|  [m/s].
    t_peak : float
        Time of peak velocity  [s].
    t_pullback : float
        Time of minimum (pullback) velocity  [s].
    t_recompression : float
        Time of first recompression maximum  [s].
    v_peak : float
        Peak velocity  [m/s].
    v_pullback : float
        Pullback (minimum) velocity  [m/s].
    v_recompression : float
        Recompression velocity  [m/s].
    rdp_points : np.ndarray or None
        RDP-simplified (time, velocity) vertices used for topology check.
    error_message : str or None
        Human-readable failure reason (``None`` on success).
    """

    ok: bool = False
    dns_classification: str = "Unknown"
    spall_strength_pa: float = np.nan
    spall_strength_unc_pa: float = np.nan
    strain_rate: float = np.nan
    peak_velocity: float = np.nan
    pullback_velocity: float = np.nan
    t_peak: float = np.nan
    t_pullback: float = np.nan
    t_recompression: float = np.nan
    v_peak: float = np.nan
    v_pullback: float = np.nan
    v_recompression: float = np.nan
    rdp_points: np.ndarray | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# RDP helper
# ---------------------------------------------------------------------------

def _rdp_simplify(
    points: np.ndarray,
    epsilon: float,
) -> np.ndarray:
    """Ramer–Douglas–Peucker polyline simplification.

    Parameters
    ----------
    points:
        (N, 2) array of (x, y) vertices.
    epsilon:
        Perpendicular-distance tolerance.

    Returns
    -------
    np.ndarray
        Indices (into *points*) of the retained vertices.
    """
    if len(points) < 3:
        return np.arange(len(points))

    def _perp_distance(point, start, end):
        if np.allclose(start, end):
            return np.linalg.norm(point - start)
        d = end - start
        t = np.dot(point - start, d) / np.dot(d, d)
        proj = start + t * d
        return np.linalg.norm(point - proj)

    def _rdp_recursive(pts, eps, idx_offset=0):
        if len(pts) < 3:
            return list(range(idx_offset, idx_offset + len(pts)))
        start, end = pts[0], pts[-1]
        dists = [_perp_distance(pts[i], start, end) for i in range(1, len(pts) - 1)]
        max_d = max(dists)
        max_i = dists.index(max_d) + 1
        if max_d > eps:
            left = _rdp_recursive(pts[: max_i + 1], eps, idx_offset)
            right = _rdp_recursive(pts[max_i:], eps, idx_offset + max_i)
            return left[:-1] + right
        return [idx_offset, idx_offset + len(pts) - 1]

    indices = _rdp_recursive(points, epsilon)
    return np.array(sorted(set(indices)))


# ---------------------------------------------------------------------------
# Spall topology ("checkmark") detector
# ---------------------------------------------------------------------------

def _detect_spall_topology(
    time_ns: np.ndarray,
    velocity: np.ndarray,
    rdp_epsilon: float = 5.0,
    min_pullback_velocity: float = 10.0,
    min_recomp_ratio: float = 0.03,
    min_recomp_velocity_ratio: float = 1.10,
    min_recomp_time_ns: float = 2.5,
) -> tuple[bool, str, dict | None, np.ndarray | None]:
    """Scan a velocity trace for the spall "checkmark" topology.

    The expected shape is:  plateau  →  pullback  →  rebound.

    Algorithm
    ---------
    1. Apply RDP simplification to the trace.
    2. Find the global peak in the simplified vertices.
    3. Find the first subsequent minimum (pullback).
    4. Find the first subsequent maximum (rebound).
    5. Validate physical gating criteria.

    Parameters
    ----------
    time_ns:
        Time array in **nanoseconds**.
    velocity:
        Smoothed velocity array  [m/s].
    rdp_epsilon:
        RDP tolerance  [m/s].
    min_pullback_velocity:
        Minimum pullback depth to accept  [m/s].
    min_recomp_ratio:
        Rebound must reach ≥ this fraction of the pullback depth.
    min_recomp_velocity_ratio:
        Rebound velocity must exceed the valley velocity by this ratio.
    min_recomp_time_ns:
        Minimum sustained duration of the rebound  [ns].

    Returns
    -------
    (is_spall, reason, keys, rdp_points)
        * ``is_spall`` – ``True`` if the topology matches.
        * ``reason``   – description string.
        * ``keys``     – dict with detected indices/velocities, or ``None``.
        * ``rdp_points`` – (M, 2) simplified vertices for visualisation.
    """
    time_ns = np.asarray(time_ns, dtype=float)
    velocity = np.asarray(velocity, dtype=float)

    pts = np.column_stack((time_ns, velocity))
    rdp_idx = _rdp_simplify(pts, rdp_epsilon)
    rdp_pts = pts[rdp_idx]

    if len(rdp_pts) < 4:
        return False, "RDP produced fewer than 4 vertices — trace too flat", None, rdp_pts

    rdp_vel = rdp_pts[:, 1]

    # Global peak in RDP vertices
    peak_rdp = int(np.argmax(rdp_vel))
    v_peak = float(rdp_vel[peak_rdp])
    t_peak = float(rdp_pts[peak_rdp, 0])

    if peak_rdp >= len(rdp_pts) - 2:
        return False, "Peak is at or near the end of the trace — no room for pullback", None, rdp_pts

    # Minimum after peak (pullback)
    seg_after_peak = rdp_vel[peak_rdp + 1:]
    if len(seg_after_peak) == 0:
        return False, "No RDP vertices after peak", None, rdp_pts
    min_rel = int(np.argmin(seg_after_peak))
    pullback_rdp = peak_rdp + 1 + min_rel
    v_pullback = float(rdp_vel[pullback_rdp])
    t_pullback = float(rdp_pts[pullback_rdp, 0])

    pullback_depth = v_peak - v_pullback
    if pullback_depth < min_pullback_velocity:
        return (
            False,
            f"Pullback depth {pullback_depth:.2f} m/s < minimum {min_pullback_velocity:.2f} m/s",
            None,
            rdp_pts,
        )

    # Maximum after pullback (rebound / recompression)
    seg_after_pullback = rdp_vel[pullback_rdp + 1:]
    if len(seg_after_pullback) == 0:
        return False, "No RDP vertices after pullback — no rebound detected", None, rdp_pts
    max_rel = int(np.argmax(seg_after_pullback))
    rebound_rdp = pullback_rdp + 1 + max_rel
    v_rebound = float(rdp_vel[rebound_rdp])
    t_rebound = float(rdp_pts[rebound_rdp, 0])

    # Gating: recompression must be meaningful
    recomp_rise = v_rebound - v_pullback
    if recomp_rise < min_recomp_ratio * pullback_depth:
        return (
            False,
            f"Rebound rise {recomp_rise:.2f} m/s is < {min_recomp_ratio*100:.0f}% of pullback — no re-acceleration",
            None,
            rdp_pts,
        )
    if v_rebound < min_recomp_velocity_ratio * v_pullback:
        return (
            False,
            f"Rebound velocity {v_rebound:.2f} m/s ≤ {min_recomp_velocity_ratio}× valley velocity {v_pullback:.2f} m/s",
            None,
            rdp_pts,
        )
    if (t_rebound - t_pullback) < min_recomp_time_ns:
        return (
            False,
            f"Rebound lasts only {t_rebound - t_pullback:.2f} ns (< {min_recomp_time_ns} ns minimum)",
            None,
            rdp_pts,
        )

    keys = {
        "shock_peak_idx": int(rdp_idx[peak_rdp]),
        "pullback_idx": int(rdp_idx[pullback_rdp]),
        "rebound_idx": int(rdp_idx[rebound_rdp]),
        "peak_velocity": v_peak,
        "pullback_velocity": v_pullback,
        "rebound_velocity": v_rebound,
        "t_peak_ns": t_peak,
        "t_pullback_ns": t_pullback,
        "t_rebound_ns": t_rebound,
        "pullback_depth": pullback_depth,
    }
    return True, "Valid spall topology detected", keys, rdp_pts


# ---------------------------------------------------------------------------
# Extended spall analysis with DNS qualifier
# ---------------------------------------------------------------------------

def spall_analysis_with_dns(
    vc_out: dict,
    iua_out: dict,
    *,
    spall_detection_method: str = "rdp",
    rdp_epsilon: float = 5.0,
    min_pullback_velocity: float = 10.0,
    min_recomp_ratio: float = 0.03,
    min_recomp_velocity_ratio: float = 1.10,
    min_recomp_time_ns: float = 2.5,
    **inputs,
) -> SpallResult:
    """Spall analysis with DNS (Did Not Spall) qualification.

    Wraps :func:`spall_analysis` and adds an RDP topology check to classify
    whether the event genuinely spalled.

    Parameters
    ----------
    vc_out:
        Velocity output dict from ``velocity_calculation``
        (keys: ``time_f`` [s], ``velocity_f_smooth`` [m/s]).
    iua_out:
        Uncertainty output dict (keys: ``freq_uncert``, ``vel_uncert``).
    spall_detection_method:
        ``"rdp"`` (default) — use RDP topology check before peak/valley;
        ``"max_min"``       — skip topology check, use peak/valley only.
    rdp_epsilon:
        RDP tolerance  [m/s].
    min_pullback_velocity, min_recomp_ratio, min_recomp_velocity_ratio, min_recomp_time_ns:
        Physical gating thresholds (see :func:`_detect_spall_topology`).
    **inputs:
        Same keyword arguments accepted by :func:`spall_analysis`
        (``spall_calculation``, ``pb_neighbors``, ``pb_idx_correction``,
        ``C0``, ``density``, …).

    Returns
    -------
    SpallResult
    """
    result = SpallResult()

    if inputs.get("spall_calculation", "yes") != "yes":
        result.dns_classification = "Spall calculation disabled"
        return result

    time_s = vc_out["time_f"]
    vel = vc_out["velocity_f_smooth"]
    vel_unc = iua_out["vel_uncert"]
    C0 = inputs["C0"]
    density = inputs["density"]

    # ------------------------------------------------------------------ #
    # Step 1: RDP topology check (optional)                                #
    # ------------------------------------------------------------------ #
    rdp_points = None
    if spall_detection_method.lower() == "rdp":
        time_ns = time_s * 1e9
        is_spall, reason, rdp_keys, rdp_points = _detect_spall_topology(
            time_ns, vel,
            rdp_epsilon=rdp_epsilon,
            min_pullback_velocity=min_pullback_velocity,
            min_recomp_ratio=min_recomp_ratio,
            min_recomp_velocity_ratio=min_recomp_velocity_ratio,
            min_recomp_time_ns=min_recomp_time_ns,
        )
        result.rdp_points = rdp_points
        if not is_spall:
            result.ok = False
            result.dns_classification = reason
            result.error_message = reason
            logger.info("DNS: %s", reason)
            # Still try to extract peak velocity for shock stress
            try:
                result.v_peak = float(np.max(vel))
                result.peak_velocity = result.v_peak
            except Exception:
                pass
            return result

    # ------------------------------------------------------------------ #
    # Step 2: Peak / valley analysis (existing logic)                      #
    # ------------------------------------------------------------------ #
    try:
        sa = spall_analysis(vc_out, iua_out, **inputs)
    except Exception as exc:
        result.ok = False
        result.dns_classification = str(exc)
        result.error_message = str(exc)
        logger.warning("spall_analysis failed: %s", exc)
        return result

    # ------------------------------------------------------------------ #
    # Step 3: Post-analysis DNS checks                                     #
    # ------------------------------------------------------------------ #
    v_peak = sa["v_max_comp"]
    v_pullback_min = sa["v_max_ten"]
    pullback_depth = v_peak - v_pullback_min

    if np.isnan(v_peak) or np.isnan(v_pullback_min):
        result.ok = False
        result.dns_classification = "Peak or pullback velocity could not be determined"
        result.error_message = result.dns_classification
        return result

    if pullback_depth < min_pullback_velocity:
        result.ok = False
        result.dns_classification = (
            f"Pullback depth {pullback_depth:.2f} m/s < minimum "
            f"{min_pullback_velocity:.2f} m/s"
        )
        result.error_message = result.dns_classification
        logger.info("DNS (post-analysis): %s", result.dns_classification)
    else:
        result.ok = True
        result.dns_classification = "Valid Spall"

    # ------------------------------------------------------------------ #
    # Step 4: Propagate results                                            #
    # ------------------------------------------------------------------ #
    result.v_peak = float(v_peak)
    result.peak_velocity = float(v_peak)
    result.v_pullback = float(v_pullback_min)
    result.v_recompression = float(sa["v_rc"]) if not np.isnan(sa["v_rc"]) else np.nan
    result.t_peak = float(sa["t_max_comp"])
    result.t_pullback = float(sa["t_max_ten"])
    result.t_recompression = float(sa["t_rc"]) if not np.isnan(sa["t_rc"]) else np.nan
    result.pullback_velocity = float(pullback_depth)
    result.spall_strength_pa = float(sa["spall_strength_est"])

    # Uncertainty: propagate peak + pullback velocity uncertainties
    peak_unc = float(vel_unc[int(np.argmax(vel))]) if not np.isnan(v_peak) else 0.0
    pullback_idx = np.argmin(np.abs(time_s - sa["t_max_ten"]))
    pullback_unc = float(vel_unc[pullback_idx])
    result.spall_strength_unc_pa = (
        0.5 * density * C0 * np.sqrt(peak_unc**2 + pullback_unc**2)
    )

    result.strain_rate = float(sa["strain_rate_est"])

    return result


# ---------------------------------------------------------------------------
# Original spall analysis (unchanged — backward-compatible)
# ---------------------------------------------------------------------------

# function to pull out important points on the spall signal
def spall_analysis(vc_out, iua_out, **inputs):
    # if user wants to pull out the spall points
    if inputs["spall_calculation"] == "yes":
        # unpack dictionary values in to individual variables
        time_f = vc_out["time_f"]
        velocity_f_smooth = vc_out["velocity_f_smooth"]
        pb_neighbors = inputs["pb_neighbors"]
        pb_idx_correction = inputs["pb_idx_correction"]
        rc_neighbors = inputs["pb_neighbors"]
        rc_idx_correction = inputs["pb_idx_correction"]
        C0 = inputs["C0"]
        density = inputs["density"]
        freq_uncert = iua_out["freq_uncert"]
        vel_uncert = iua_out["vel_uncert"]

        # get the global peak velocity
        peak_velocity_idx = np.argmax(velocity_f_smooth)
        peak_velocity = velocity_f_smooth[peak_velocity_idx]

        # get the uncertainities associated with the peak velocity
        peak_velocity_freq_uncert = freq_uncert[peak_velocity_idx]
        peak_velocity_vel_uncert = vel_uncert[peak_velocity_idx]

        # attempt to get the fist local minimum after the peak velocity to get the pullback
        # velocity. 'order' is the number of points on each side to compare to.
        # get all the indices for relative minima in the domain, order them, and take the first one that occurs
        # after the peak velocity
        rel_min_idx = signal.argrelmin(velocity_f_smooth, order=pb_neighbors)[0]
        extrema_min = np.append(rel_min_idx, np.argmax(velocity_f_smooth))
        extrema_min.sort()
        _max_ten_pos = np.where(extrema_min == np.argmax(velocity_f_smooth))[0][0] + 1 + pb_idx_correction
        if _max_ten_pos >= len(extrema_min):
            raise ValueError("no local minimum found after peak velocity (no spall pullback detected)")
        max_ten_idx = extrema_min[_max_ten_pos]

        # get the uncertainities associated with the max tension velocity
        max_ten_freq_uncert = freq_uncert[max_ten_idx]
        max_ten_vel_uncert = vel_uncert[max_ten_idx]

        # get the velocity at max tension
        max_tension_velocity = velocity_f_smooth[max_ten_idx]

        # calculate the pullback velocity
        pullback_velocity = peak_velocity - max_tension_velocity

        # calculate the estimated strain rate and spall strength
        strain_rate_est = (
            (0.5 / C0)
            * pullback_velocity
            / (time_f[max_ten_idx] - time_f[np.argmax(velocity_f_smooth)])
        )
        spall_strength_est = 0.5 * density * C0 * pullback_velocity

        # set final variables for the function return
        t_max_comp = time_f[np.argmax(velocity_f_smooth)]
        t_max_ten = time_f[max_ten_idx]
        v_max_comp = peak_velocity
        v_max_ten = max_tension_velocity

        # get first local maximum after pullback (recompression)
        rel_max_idx = signal.argrelmax(velocity_f_smooth, order=rc_neighbors)[0]
        extrema_max = np.append(rel_max_idx, np.argmax(velocity_f_smooth))
        extrema_max.sort()
        _rc_pos = np.where(extrema_max == np.argmax(velocity_f_smooth))[0][0] + 2 + rc_idx_correction
        if _rc_pos >= len(extrema_max):
            raise ValueError("no local maximum found after pullback (no recompression detected)")
        rc_idx = extrema_max[_rc_pos]
        t_rc = time_f[rc_idx]
        v_rc = velocity_f_smooth[rc_idx]

    # if user does not want to pull out the spall points just set everything to nan
    else:
        t_max_comp = np.nan
        t_max_ten = np.nan
        t_rc = np.nan
        v_max_comp = np.nan
        v_max_ten = np.nan
        v_rc = np.nan
        spall_strength_est = np.nan
        strain_rate_est = np.nan
        peak_velocity_freq_uncert = np.nan
        peak_velocity_vel_uncert = np.nan
        max_ten_freq_uncert = np.nan
        max_ten_vel_uncert = np.nan

    # return a dictionary of the results
    sa_out = {
        "t_max_comp": t_max_comp,
        "t_max_ten": t_max_ten,
        "t_rc": t_rc,
        "v_max_comp": v_max_comp,
        "v_max_ten": v_max_ten,
        "v_rc": v_rc,
        "spall_strength_est": spall_strength_est,
        "strain_rate_est": strain_rate_est,
        "peak_velocity_freq_uncert": peak_velocity_freq_uncert,
        "peak_velocity_vel_uncert": peak_velocity_vel_uncert,
        "max_ten_freq_uncert": max_ten_freq_uncert,
        "max_ten_vel_uncert": max_ten_vel_uncert,
    }

    return sa_out
