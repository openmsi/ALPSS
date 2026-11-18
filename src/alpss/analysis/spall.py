import numpy as np
from scipy import signal


# function to pull out important points on the spall signal
def spall_analysis(vc_out, iua_out, **inputs):
    # unpack dictionary values in to individual variables
    time_f = vc_out["time_f"]
    velocity_f_smooth = vc_out["velocity_f_smooth"]
    # the neighbor windows are given in seconds so they mean the same thing at
    # any sample rate; argrelmin/argrelmax need them in samples
    fs = 1 / np.mean(np.diff(time_f))
    pb_neighbors = max(1, round(inputs["pb_neighbors_time"] * fs))
    pb_idx_correction = inputs["pb_idx_correction"]
    rc_neighbors = max(1, round(inputs["rc_neighbors_time"] * fs))
    rc_idx_correction = inputs["rc_idx_correction"]
    C0 = inputs["C0"]
    density = inputs["density"]
    freq_uncert = iua_out["freq_uncert"]
    vel_uncert = iua_out["vel_uncert"]

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
    pullback_velocity = vc_out["v_max_comp"] - max_tension_velocity

    # calculate the estimated strain rate and spall strength
    strain_rate_est = (
        (0.5 / C0)
        * pullback_velocity
        / (time_f[max_ten_idx] - vc_out["t_max_comp"])
    )
    spall_strength_est = 0.5 * density * C0 * pullback_velocity

    # set final variables for the function return
    t_max_ten = time_f[max_ten_idx]
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

    # return a dictionary of the results
    sa_out = {
        "t_max_ten": t_max_ten,
        "t_rc": t_rc,
        "v_max_ten": v_max_ten,
        "v_rc": v_rc,
        "spall_strength_est": spall_strength_est,
        "strain_rate_est": strain_rate_est,
        "max_ten_freq_uncert": max_ten_freq_uncert,
        "max_ten_vel_uncert": max_ten_vel_uncert,
    }

    return sa_out
