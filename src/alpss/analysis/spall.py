import numpy as np


# function to pull out important points on the spall signal
def spall_analysis(vc_out, **inputs):
    C0 = inputs["C0"]
    density = inputs["density"]

    v_max_ten = vc_out["v_max_ten"]
    t_max_ten = vc_out["t_max_ten"]

    pullback_velocity = vc_out["v_max_comp"] - v_max_ten

    strain_rate_est = (
        (0.5 / C0)
        * pullback_velocity
        / (t_max_ten - vc_out["t_max_comp"])
    )
    spall_strength_est = 0.5 * density * C0 * pullback_velocity

    return {
        "spall_strength_est": spall_strength_est,
        "strain_rate_est": strain_rate_est,
    }
