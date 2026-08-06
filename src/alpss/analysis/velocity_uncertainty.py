def velocity_uncertainty_analysis(vc_out, iua_out):
    """Compute peak velocity uncertainties from velocity and instantaneous uncertainty analysis.

    Returns dict with peak velocity freq and velocity uncertainties.
    """
    peak_velocity_idx = vc_out["peak_velocity_idx"]
    peak_velocity_freq_uncert = iua_out["freq_uncert"][peak_velocity_idx]
    peak_velocity_vel_uncert = iua_out["vel_uncert"][peak_velocity_idx]

    vu_out = {
        "peak_velocity_freq_uncert": peak_velocity_freq_uncert,
        "peak_velocity_vel_uncert": peak_velocity_vel_uncert,
    }

    return vu_out
