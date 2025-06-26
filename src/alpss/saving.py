import os
import pandas as pd
import numpy as np
from IPython.display import display


# function for saving all the final outputs
def save(
    sdf_out, cen, vc_out, sa_out, iua_out, fua_out, start_time, end_time, fig, **inputs
):
    filename = os.path.splitext(os.path.basename(inputs["filepath"]))[0]
    fname = os.path.join(inputs["out_files_dir"], filename)

    # save the plots
    fig_assets = [fig]
    if inputs["save_data"]:
        fig_path = fname + "--plots.png"
        fig.savefig(
            fname=fig_path,
            dpi="figure",
            format="png",
            facecolor="w",
            )
        fig_assets.append(fig_path)

    # save the function inputs used for this run
    inputs.pop("bytestring", None)
    inputs_df = pd.DataFrame.from_dict(inputs, orient="index", columns=["Input"])
    inputs_assets = [inputs_df]
    if inputs["save_data"]:
        inputs_path = fname + "--inputs" + ".csv"
        inputs_df.to_csv(inputs_path, index=True, header=False)
        inputs_assets.append(inputs_path)

    # save the noisy velocity trace
    velocity_data = np.stack((vc_out["time_f"], vc_out["velocity_f"]), axis=1)
    velocity_assets = [velocity_data]
    if inputs["save_data"]:
        velocity_path = fname + "--velocity" + ".csv"
        np.savetxt(velocity_path, velocity_data, delimiter=",")
        velocity_assets.append(velocity_path)

    # save the smoothed velocity trace
    velocity_data_smooth = np.stack(
        (vc_out["time_f"], vc_out["velocity_f_smooth"]), axis=1
    )
    smooth_velocity_assets = [velocity_data_smooth]
    if inputs["save_data"]:
        smooth_velocity_path = fname + "--velocity--smooth" + ".csv"
        np.savetxt(
            smooth_velocity_path,
            velocity_data_smooth,
            delimiter=",",
        )
        smooth_velocity_assets.append(smooth_velocity_path)
    
    # save the filtered voltage data
    voltage_data = np.stack(
        (
            sdf_out["time"],
            np.real(vc_out["voltage_filt"]),
            np.imag(vc_out["voltage_filt"]),
        ),
        axis=1,
    )
    voltage_assets = [voltage_data]
    if inputs["save_data"]:
        voltage_path = fname + "--voltage" + ".csv"
        np.savetxt(voltage_path, voltage_data, delimiter=",")
        voltage_assets.append(voltage_path)

    # save the noise fraction
    noise_data = np.stack((vc_out["time_f"], iua_out["inst_noise"]), axis=1)
    noise_assets = [noise_data]
    if inputs["save_data"]:
        noise_path = fname + "--noisefrac" + ".csv"
        np.savetxt(noise_path, noise_data, delimiter=",")
        noise_assets.append(noise_path)

    # save the velocity uncertainty
    vel_uncert_data = np.stack((vc_out["time_f"], iua_out["vel_uncert"]), axis=1)
    vel_uncert_assets = [vel_uncert_data]
    if inputs["save_data"]:
        vel_uncert_path = fname + "--veluncert" + ".csv"
        np.savetxt(
            vel_uncert_path,
            vel_uncert_data,
            delimiter=",",
        )
        vel_uncert_assets.append(vel_uncert_path)

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
    # results_df.loc[0, "Velocity at Max Compression"] /= 1e-9
    # results_df.loc[0, "Velocity at Max Tension"] /= 1e-9
    # results_df.loc[0, "Velocity at Recompression"] /= 1e-9
    # results_df.loc[0, "Spect Time Res"] /= 1e-9
    # results_df.loc[0, "Spect Velocity Res"] /= 1e-9
    # results_df.loc[0, "Signal Start Time"] /= 1e-9

    results_dict = results_df.iloc[0].to_dict()

    display(results_dict)
    return {"figure": fig_assets, "inputs": inputs_assets, "velocity": velocity_assets, "smooth_velocity": smooth_velocity_assets,"voltage":voltage_assets, "noise":noise_assets, "vel_uncert":vel_uncert_assets,  "results" : results_dict}
