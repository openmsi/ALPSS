import os
import pandas as pd
import numpy as np
from IPython.display import display


# function for saving all the final outputs
def save(
    sdf_out, cen, vc_out, sa_out, iua_out, fua_out, start_time, end_time, fig, **inputs
):
    fname = os.path.join(inputs["out_files_dir"], os.path.basename(inputs["filepath"]))

    # save the plots
    if inputs["save_data"]:
        fig.savefig(
            fname=fname + "--plots.png",
            dpi="figure",
            format="png",
            facecolor="w",
        )

    # save the function inputs used for this run
    inputs_df = pd.DataFrame.from_dict(inputs, orient="index", columns=["Input"])
    if inputs["save_data"]:
        inputs_df.to_csv(fname + "--inputs" + ".csv", index=True, header=False)

    # save the noisy velocity trace
    velocity_data = np.stack((vc_out["time_f"], vc_out["velocity_f"]), axis=1)
    if inputs["save_data"]:
        np.savetxt(fname + "--velocity" + ".csv", velocity_data, delimiter=",")

    # save the smoothed velocity trace
    velocity_data_smooth = np.stack(
        (vc_out["time_f"], vc_out["velocity_f_smooth"]), axis=1
    )

    if inputs["save_data"]:
        np.savetxt(
            fname + "--velocity--smooth" + ".csv",
            velocity_data_smooth,
            delimiter=",",
        )

    # save the filtered voltage data

    voltage_data = np.stack(
        (
            sdf_out["time"],
            np.real(vc_out["voltage_filt"]),
            np.imag(vc_out["voltage_filt"]),
        ),
        axis=1,
    )
    if inputs["save_data"]:
        np.savetxt(fname + "--voltage" + ".csv", voltage_data, delimiter=",")

    # save the noise fraction
    noise_data = np.stack((vc_out["time_f"], iua_out["inst_noise"]), axis=1)
    if inputs["save_data"]:
        np.savetxt(fname + "--noisefrac" + ".csv", noise_data, delimiter=",")

    # save the velocity uncertainty
    vel_uncert_data = np.stack((vc_out["time_f"], iua_out["vel_uncert"]), axis=1)
    if inputs["save_data"]:
        np.savetxt(
            fname + "--veluncert" + ".csv",
            vel_uncert_data,
            delimiter=",",
        )

    results_to_save = {
        "Date": start_time.strftime("%b %d %Y"),
        "Time": start_time.strftime("%I:%M %p"),
        "File Name": os.path.basename(inputs["filepath"]),
        "Run Time": (end_time - start_time),
        "Velocity at Max Compression": sa_out["v_max_comp"],
        "Time at Max Compression": sa_out["t_max_comp"],
        "Velocity at Max Tension": sa_out["v_max_ten"],
        "Time at Max Tension": sa_out["t_max_ten"],
        "Velocity at Recompression": sa_out["v_rc"],
        "Time at Recompression": sa_out["t_rc"],
        "Carrier Frequency": cen,
        "Spall Strength": sa_out["spall_strength_est"],
        "Spall Strength Uncertainty": fua_out["spall_uncert"],
        "Strain Rate": sa_out["strain_rate_est"],
        "Strain Rate Uncertainty": fua_out["strain_rate_uncert"],
        "Peak Shock Stress": (
            0.5 * inputs["density"] * inputs["C0"] * sa_out["v_max_comp"]
        ),
        "Spect Time Res": sdf_out["t_res"],
        "Spect Freq Res": sdf_out["f_res"],
        "Spect Velocity Res": 0.5 * (inputs["lam"] * sdf_out["f_res"]),
        "Signal Start Time": sdf_out["t_start_corrected"],
        "Smoothing Characteristic Time": iua_out["tau"],
    }

    # Convert the dictionary to a DataFrame
    results_df = pd.DataFrame([results_to_save])

    # Optional: Convert units to nanoseconds for certain fields
    results_df.loc[0, "Velocity at Max Compression"] /= 1e-9
    results_df.loc[0, "Velocity at Max Tension"] /= 1e-9
    results_df.loc[0, "Velocity at Recompression"] /= 1e-9
    results_df.loc[0, "Spect Time Res"] /= 1e-9
    results_df.loc[0, "Spect Velocity Res"] /= 1e-9
    results_df.loc[0, "Signal Start Time"] /= 1e-9

    display(results_df)
    return {"--results" : results_to_save, "--voltage": voltage_data, "noisefrac": noise_data}
