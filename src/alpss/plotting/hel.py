import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def plot_hel_detection(
    time_full,
    velocity_full,
    hel_result,
    *,
    hel_start_ns,
    hel_end_ns,
    angle_threshold_deg=45.0,
    sample_name="",
    sample_material="",
    U_0=None,
    t_0=None,
):
    """
    Generate a 3-panel HEL detection diagnostic plot.

    Parameters
    ----------
    time_full : array_like
        Full time trace in nanoseconds.
    velocity_full : array_like
        Full velocity trace in m/s.
    hel_result : HELResult
        Result from hel_detection().
    hel_start_ns : float
        Start of HEL search window in ns.
    hel_end_ns : float
        End of HEL search window in ns.
    angle_threshold_deg : float
        Angle threshold used for detection.
    sample_name : str
        Name of the sample/file for the title.
    sample_material : str
        Material name for the title.
    U_0 : float or None
        Reference velocity for strain rate slope line.
    t_0 : float or None
        Reference time for strain rate slope line.

    Returns
    -------
    matplotlib.figure.Figure
        The diagnostic figure.
    """
    t_win = hel_result.time_window
    v_win = hel_result.velocity_window
    gradient = hel_result.gradient_smooth
    seg_start = hel_result.segment_start_idx
    seg_end = hel_result.segment_end_idx
    fsv = hel_result.free_surface_velocity

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 14))

    # --- Top: Full velocity trace with HEL window highlighted ---
    ax1.plot(time_full, velocity_full, "b-", linewidth=1.5, alpha=0.7, label="Velocity")
    ax1.axvspan(hel_start_ns, hel_end_ns, alpha=0.2, color="yellow", label="HEL Window")
    ax1.axvline(hel_start_ns, color="orange", linestyle="--", linewidth=1, alpha=0.7)
    ax1.axvline(hel_end_ns, color="orange", linestyle="--", linewidth=1, alpha=0.7)
    ax1.set_xlabel("Time (ns)", fontsize=12)
    ax1.set_ylabel("Velocity (m/s)", fontsize=12)
    ax1.set_title(
        f"HEL Detection - {sample_name}\nMaterial: {sample_material}",
        fontsize=14,
        fontweight="bold",
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left")

    # --- Middle: Zoomed HEL window with plateau overlay ---
    if t_win is not None:
        ax2.plot(t_win, v_win, "b-", linewidth=2, label="Velocity in HEL window")

    if seg_start is not None and seg_end is not None and fsv is not None and np.isfinite(fsv):
        plateau_t0 = t_win[seg_start]
        plateau_t1 = t_win[seg_end]
        ax2.axvspan(
            plateau_t0, plateau_t1, alpha=0.3, color="orange",
            label=f"HEL Plateau ({fsv:.1f} m/s)",
        )
        ax2.axhline(
            fsv, color="orange", linestyle="--", linewidth=2, alpha=0.8,
            label=f"Mean Plateau Velocity: {fsv:.1f} m/s",
        )
        ax2.axvline(plateau_t0, color="orange", linestyle=":", linewidth=1.5, alpha=0.7)
        ax2.axvline(plateau_t1, color="orange", linestyle=":", linewidth=1.5, alpha=0.7)

    ax2.set_xlabel("Time (ns)", fontsize=12)
    ax2.set_ylabel("Velocity (m/s)", fontsize=12)
    ax2.set_title("HEL Window Detail - Velocity", fontsize=13, fontweight="bold")
    ax2.grid(True, alpha=0.3)

    # Strain rate slope line
    t_hel = hel_result.time_detection_ns
    if (
        U_0 is not None
        and t_0 is not None
        and np.isfinite(U_0)
        and np.isfinite(t_0)
        and np.isfinite(t_hel)
        and np.isfinite(fsv)
    ):
        dt = t_hel - t_0
        if dt > 0:
            slope = (fsv - U_0) / dt
            ax2.plot(
                [t_0, t_hel], [U_0, fsv], "r--", linewidth=2, alpha=0.8,
                label=f"Strain Rate Slope: {slope:.2e} m/s/ns",
            )
            ax2.plot(t_0, U_0, "go", markersize=8, label=f"U\u2080: {U_0:.1f} m/s @ {t_0:.1f} ns", zorder=5)
            ax2.plot(t_hel, fsv, "ro", markersize=8, label=f"U_HEL: {fsv:.1f} m/s @ {t_hel:.1f} ns", zorder=5)

    # HEL stress annotation
    if hel_result.ok:
        result_text = f"HEL Strength: {hel_result.strength_gpa:.3f} \u00b1 {hel_result.uncertainty_gpa:.3f} GPa"
        ax2.text(
            0.02, 0.98, result_text, transform=ax2.transAxes, fontsize=12,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.8),
        )

    ax2.legend(loc="best", fontsize=10)

    # --- Bottom: Gradient vs time ---
    if gradient is not None and t_win is not None:
        ax3.plot(t_win, gradient, "g-", linewidth=1.5, alpha=0.6, label="Gradient (dv/dt)")
        ax3.axhline(0, color="black", linestyle="-", linewidth=0.8, alpha=0.5)

        if seg_start is not None and seg_end is not None:
            ax3.axvspan(
                t_win[seg_start], t_win[seg_end], alpha=0.3, color="orange",
                label="HEL Plateau Region",
            )

        # Angle threshold as gradient
        angle_thresh_rad = np.radians(angle_threshold_deg)
        gradient_thresh = np.tan(angle_thresh_rad)
        ax3.axhline(
            gradient_thresh, color="red", linestyle="--", linewidth=1, alpha=0.7,
            label=f"Angle Threshold ({angle_threshold_deg}\u00b0)",
        )
        ax3.axhline(-gradient_thresh, color="red", linestyle="--", linewidth=1, alpha=0.7)

    ax3.set_xlabel("Time (ns)", fontsize=12)
    ax3.set_ylabel("Gradient (m/s per ns)", fontsize=12)
    ax3.set_title("Gradient vs Time - HEL Detection", fontsize=13, fontweight="bold")
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="best", fontsize=10)

    plt.tight_layout()
    return fig
