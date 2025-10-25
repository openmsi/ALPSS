import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import os
from alpss.utils import stft
import numpy as np
import random
import string
from importlib.metadata import version, PackageNotFoundError

try:
    pkg_version = version("alpss")
    pkg_version = pkg_version.replace(".", "_")
    pkg_version = "v" + pkg_version
except PackageNotFoundError:
    pkg_version = "unknown"

# function to generate the final figure
def plot_results(
    sdf_out,
    cen,
    cf_out,
    vc_out,
    sa_out,
    iua_out,
    fua_out,
    start_time,
    end_time,
    **inputs,
):
    # Define font sizes for the entire plot (scaled for large figure size)
    title_fontsize = 10
    label_fontsize = 8
    tick_fontsize = 6
    legend_fontsize = 6
    table_fontsize = 6
    
    # create the figure and axes
    fig = plt.figure(
        num=1, figsize=inputs["plot_figsize"], dpi=inputs["plot_dpi"], clear=True
    )
    
    # ROW 1: Velocity with Uncertainty (16x1), gap(2), FFT Spectrum (6x1), gap(2), Voltage Data (6x1)
    ax12 = plt.subplot2grid((3, 32), (0, 0), colspan=16) # velocity trace and spall points
    ax_fft = plt.subplot2grid((3, 32), (0, 18), colspan=6)  # FFT spectrum
    ax1 = plt.subplot2grid((3, 32), (0, 24), colspan=8)   # voltage data
    
    # ROW 2: Spectrogram Original (6x1), gap(2), IQ Analysis (6x1), gap(2), Spectrogram ROI (6x1), gap(2), Noise Fraction (8x1)
    ax3 = plt.subplot2grid((3, 32), (1, 0), colspan=6)   # imported voltage spectrogram
    ax_iq = plt.subplot2grid((3, 32), (1, 8), colspan=6)   # IQ analysis
    ax5 = plt.subplot2grid((3, 32), (1, 16), colspan=6)  # spectrogram of the ROI
    ax10 = plt.subplot2grid((3, 32), (1, 24), colspan=8) # noise fraction
    ax11 = ax10.twinx()                                   # velocity uncertainty (twin of ax10)
    
    # ROW 3: Results Table (32x1 colspan)
    ax13 = plt.subplot2grid((3, 32), (2, 0), colspan=32) # results table

    # voltage data
    ax1.plot(
        sdf_out["time"] / 1e-9,
        sdf_out["voltage"] * 1e3,
        label="Original Signal",
        c="tab:blue",
    )
    ax1.plot(
        sdf_out["time"] / 1e-9,
        np.real(vc_out["voltage_filt"]) * 1e3,
        label="Filtered Signal",
        c="tab:orange",
    )
    ax1.plot(
        iua_out["time_cut"] / 1e-9,
        iua_out["volt_fit"] * 1e3,
        label="Sine Fit",
        c="tab:green",
    )
    ax1.axvspan(
        sdf_out["t_doi_start"] / 1e-9,
        sdf_out["t_doi_end"] / 1e-9,
        ymin=-1,
        ymax=1,
        color="tab:red",
        alpha=0.35,
        ec="none",
        label="ROI",
        zorder=4,
    )
    ax1.set_xlabel("Time (ns)")
    ax1.set_ylabel("Voltage (mV)")
    ax1.set_xlim([sdf_out["time"][0] / 1e-9, sdf_out["time"][-1] / 1e-9])
    ax1.legend(loc="upper right", fontsize=legend_fontsize)
    ax1.set_title("Voltage Data", fontsize=title_fontsize)
    ax1.tick_params(axis='both', which='major', labelsize=tick_fontsize)

    # FFT spectrum plot
    from scipy.fft import fft, fftfreq
    fs = sdf_out["fs"]
    time = sdf_out["time"]
    voltage = sdf_out["voltage"]
    
    fft_vals = np.abs(fft(voltage))
    freqs = fftfreq(len(voltage), 1/fs)
    
    # Only positive frequencies
    pos_mask = freqs > 0
    ax_fft.semilogy(freqs[pos_mask]/1e9, fft_vals[pos_mask], 'r-', linewidth=1)
    ax_fft.axvline(inputs['freq_min']/1e9, color='g', linestyle='--', linewidth=2, label='freq_min')
    ax_fft.axvline(inputs['freq_max']/1e9, color='b', linestyle='--', linewidth=2, label='freq_max')
    ax_fft.set_xlabel("Frequency (GHz)", fontsize=label_fontsize)
    ax_fft.set_ylabel("Magnitude", fontsize=label_fontsize)
    ax_fft.set_title("FFT Spectrum", fontsize=title_fontsize)
    ax_fft.set_xlim([0, 5])
    ax_fft.legend(fontsize=legend_fontsize)
    ax_fft.grid(True, alpha=0.3, which='both')
    ax_fft.tick_params(axis='both', which='major', labelsize=tick_fontsize)

    # imported voltage spectrogram and a rectangle to show the ROI
    plt3 = ax3.imshow(
        10 * np.log10(sdf_out["mag"] ** 2),
        aspect="auto",
        origin="lower",
        interpolation="none",
        extent=[
            sdf_out["t"][0] / 1e-9,
            sdf_out["t"][-1] / 1e-9,
            sdf_out["f"][0] / 1e9,
            sdf_out["f"][-1] / 1e9,
        ],
        cmap=inputs["cmap"],
    )
    fig.colorbar(plt3, ax=ax3, label="Power (dBm)")
    anchor = [sdf_out["t_doi_start"] / 1e-9, sdf_out["f_doi"][0] / 1e9]
    width = sdf_out["t_doi_end"] / 1e-9 - sdf_out["t_doi_start"] / 1e-9
    height = sdf_out["f_doi"][-1] / 1e9 - sdf_out["f_doi"][0] / 1e9
    win = Rectangle(
        anchor,
        width,
        height,
        edgecolor="r",
        facecolor="none",
        linewidth=0.75,
        linestyle="-",
    )
    ax3.add_patch(win)
    ax3.set_xlabel("Time (ns)")
    ax3.set_ylabel("Frequency (GHz)")
    ax3.set_ylim([0, 20])  # Limit y-axis to 20 GHz
    ax3.minorticks_on()
    ax3.set_title("Spectrogram Original Signal")

    # IQ Analysis plot - Load from saved file
    import os
    from PIL import Image
    import glob
    
    iq_plot_path = None
    out_dir = inputs.get("out_files_dir", "output_data/")
    
    # Try to find the IQ plot file - search in main directory and subdirectories
    if os.path.exists(out_dir):
        # Search for IQ plot in main directory
        iq_files = glob.glob(os.path.join(out_dir, "*IQ_start_time_detection*.png"))
        if iq_files:
            iq_plot_path = iq_files[0]  # Get the first match
        else:
            # Search in subdirectories
            iq_files = glob.glob(os.path.join(out_dir, "*", "*IQ_start_time_detection*.png"))
            if iq_files:
                iq_plot_path = iq_files[0]
    
    if iq_plot_path and os.path.exists(iq_plot_path):
        try:
            iq_img = Image.open(iq_plot_path)
            # Crop to square aspect ratio to match other plots
            width, height = iq_img.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            iq_img_cropped = iq_img.crop((left, top, left + size, top + size))
            
            # Resize image for better font visibility
            iq_img_resized = iq_img_cropped.resize((int(iq_img_cropped.width * 1.3), int(iq_img_cropped.height * 1.3)), Image.Resampling.LANCZOS)
            
            ax_iq.imshow(iq_img_resized)
            ax_iq.axis('off')
            ax_iq.set_title("IQ Start Time Detection", fontsize=title_fontsize, pad=10)
        except Exception as e:
            print(f"Error loading IQ plot: {e}")
            ax_iq.text(0.5, 0.5, 'IQ Plot\n(Unable to load)', 
                      ha='center', va='center', transform=ax_iq.transAxes,
                      fontsize=label_fontsize)
    else:
        ax_iq.text(0.5, 0.5, 'IQ Plot\n(Not found)', 
                  ha='center', va='center', transform=ax_iq.transAxes,
                  fontsize=label_fontsize)

    # plotting the spectrogram of the ROI with the start-time line to see how well it lines up
    plt5 = ax5.imshow(
        10 * np.log10(sdf_out["mag"] ** 2),
        aspect="auto",
        origin="lower",
        interpolation="none",
        extent=[
            sdf_out["t"][0] / 1e-9,
            sdf_out["t"][-1] / 1e-9,
            sdf_out["f"][0] / 1e9,
            sdf_out["f"][-1] / 1e9,
        ],
        cmap=inputs["cmap"],
    )
    fig.colorbar(plt5, ax=ax5, label="Power (dBm)")
    ax5.axvline(sdf_out["t_start_detected"] / 1e-9, ls="--", c="r")
    ax5.axvline(sdf_out["t_start_corrected"] / 1e-9, ls="-", c="r")
    if inputs["start_time_user"] == "otsu":
        ax5.axhline(sdf_out["f_doi"][sdf_out["f_doi_carr_top_idx"]] / 1e9, c="r")
    ax5.set_ylim([inputs["freq_min"] / 1e9, inputs["freq_max"] / 1e9])
    ax5.set_xlim([sdf_out["t_doi_start"] / 1e-9, sdf_out["t_doi_end"] / 1e-9])
    plt5.set_clim([np.min(sdf_out["power_doi"]), np.max(sdf_out["power_doi"])])
    ax5.set_xlabel("Time (ns)")
    ax5.set_ylabel("Frequency (GHz)")
    ax5.minorticks_on()
    ax5.set_title("Spectrogram ROI")

    # plot the noise fraction on the ROI
    ax10.plot(vc_out["time_f"] / 1e-9, iua_out["inst_noise"] * 100, "r", linewidth=2)
    ax10.set_xlabel("Time (ns)")
    ax10.set_ylabel("Noise Fraction (%)")
    ax10.set_xlim([vc_out["time_f"][0] / 1e-9, vc_out["time_f"][-1] / 1e-9])
    ax10.minorticks_on()
    ax10.grid(axis="both", which="both")
    ax10.set_title("Noise Fraction and Velocity Uncertainty")

    # plot the velocity uncertainty on the ROI
    ax11.plot(vc_out["time_f"] / 1e-9, iua_out["vel_uncert"], linewidth=2)
    ax11.set_ylabel("Velocity Uncertainty (m/s)")
    ax11.minorticks_on()

    # plotting the final smoothed velocity trace and uncertainty bounds with spall point markers (if they were found
    # on the signal)
    ax12.fill_between(
        (vc_out["time_f"] - sdf_out["t_start_corrected"]) / 1e-9,
        vc_out["velocity_f_smooth"] + 2 * iua_out["vel_uncert"] * inputs["uncert_mult"],
        vc_out["velocity_f_smooth"] - 2 * iua_out["vel_uncert"] * inputs["uncert_mult"],
        color="mistyrose",
        label=rf'$2\sigma$ Uncertainty (x{inputs["uncert_mult"]})',
    )

    ax12.fill_between(
        (vc_out["time_f"] - sdf_out["t_start_corrected"]) / 1e-9,
        vc_out["velocity_f_smooth"] + iua_out["vel_uncert"] * inputs["uncert_mult"],
        vc_out["velocity_f_smooth"] - iua_out["vel_uncert"] * inputs["uncert_mult"],
        color="lightcoral",
        alpha=0.5,
        ec="none",
        label=rf'$1\sigma$ Uncertainty (x{inputs["uncert_mult"]})',
    )

    ax12.plot(
        (vc_out["time_f"] - sdf_out["t_start_corrected"]) / 1e-9,
        vc_out["velocity_f_smooth"],
        "k-",
        linewidth=3,
        label="Smoothed Velocity",
    )
    ax12.set_xlabel("Time (ns)")
    ax12.set_ylabel("Velocity (m/s)")
    ax12.set_title("Velocity with Uncertainty Bounds")

    if not np.isnan(sa_out["t_max_comp"]):
        ax12.plot(
            (sa_out["t_max_comp"] - sdf_out["t_start_corrected"]) / 1e-9,
            sa_out["v_max_comp"],
            "bs",
            label=f'Velocity at Max Compression: {int(round(sa_out["v_max_comp"]))}',
        )
    if not np.isnan(sa_out["t_max_ten"]):
        ax12.plot(
            (sa_out["t_max_ten"] - sdf_out["t_start_corrected"]) / 1e-9,
            sa_out["v_max_ten"],
            "ro",
            label=f'Velocity at Max Tension: {int(round(sa_out["v_max_ten"]))}',
        )
    if not np.isnan(sa_out["t_rc"]):
        ax12.plot(
            (sa_out["t_rc"] - sdf_out["t_start_corrected"]) / 1e-9,
            sa_out["v_rc"],
            "gD",
            label=f'Velocity at Recompression: {int(round(sa_out["v_rc"]))}',
        )

    # if not np.isnan(sa_out['t_max_comp']) or not np.isnan(sa_out['t_max_ten']) or not np.isnan(sa_out['t_rc']):
    #    ax12.legend(loc='lower right', fontsize=9)
    ax12.legend(loc="lower right", fontsize=legend_fontsize)
    ax12.set_xlim(
        [
            -inputs["t_before"] / 1e-9,
            (vc_out["time_f"][-1] - sdf_out["t_start_corrected"]) / 1e-9,
        ]
    )
    ax12.set_ylim(
        [
            np.min(vc_out["velocity_f_smooth"]) - 100,
            np.max(vc_out["velocity_f_smooth"]) + 100,
        ]
    )

    if np.max(iua_out["inst_noise"]) > 1.0:
        ax10.set_ylim([0, 100])
        ax11.set_ylim([0, iua_out["freq_uncert_scaling"] * (inputs["lam"] / 2)])

    # table to show results of the run
    run_data1 = {
        "Name": [
            "Date",
            "Time",
            "File Name",
            "Run Time",
            "Smoothing FWHM (ns)",
            "Peak Shock Stress (GPa)",
            "Strain Rate (x1e6)",
            "Spall Strength (GPa)",
        ],
        "Value": [
            start_time.strftime("%b %d %Y"),
            start_time.strftime("%I:%M %p"),
            inputs["filepath"],
            (end_time - start_time),
            round(iua_out["tau"] * 1e9, 2),
            round(
                (0.5 * inputs["density"] * inputs["C0"] * sa_out["v_max_comp"]) / 1e9, 6
            ),
            rf"{round(sa_out['strain_rate_est'] / 1e6, 6)} $\pm$ {round(fua_out['strain_rate_uncert'] / 1e6, 6)}",
            rf"{round(sa_out['spall_strength_est'] / 1e9, 6)} $\pm$ {round(fua_out['spall_uncert'] / 1e9, 6)}",
        ],
    }

    df1 = pd.DataFrame(data=run_data1)
    cellLoc1 = "center"
    loc1 = "center"
    table1 = ax13.table(
        cellText=df1.values, colLabels=df1.columns, cellLoc=cellLoc1, loc=loc1
    )
    table1.auto_set_font_size(False)
    table1.set_fontsize(table_fontsize)
    table1.scale(1, 1.5)
    ax13.axis("tight")
    ax13.axis("off")

    # fix the layout
    plt.tight_layout()
    
    # Add extra padding to prevent subplot squishing
    plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05, hspace=0.5, wspace=1.0)
    
    # Apply font sizes to all axes
    for ax in fig.get_axes():
        ax.tick_params(axis='both', which='major', labelsize=tick_fontsize)
        for label in ax.get_xticklabels():
            label.set_fontsize(tick_fontsize)
        for label in ax.get_yticklabels():
            label.set_fontsize(tick_fontsize)
        ax.xaxis.label.set_fontsize(label_fontsize)
        ax.yaxis.label.set_fontsize(label_fontsize)
        ax.title.set_fontsize(title_fontsize)

    # display the plots if desired. if this is turned off the plots will still save
    if inputs["display_plots"] == "yes":
        plt.show()

    return fig


def plot_voltage(data, **inputs):

    # rename the columns of the data
    data.columns = ["Time", "Ampl"]

    # put the data into numpy arrays. Zero the time data
    time = data["Time"].to_numpy()
    time = time - time[0]
    voltage = data["Ampl"].to_numpy()

    # calculate the sample rate from the experimental data
    fs = 1 / np.mean(np.diff(time))

    # calculate the short time fourier transform
    f, t, Zxx = stft(voltage, fs, **inputs)

    # calculate magnitude of Zxx
    mag = np.abs(Zxx)

    # plotting
    fig, (ax1, ax2) = plt.subplots(1, 2, num=2, figsize=(11, 4), dpi=300, clear=True)
    ax1.plot(time / 1e-9, voltage / 1e-3)
    ax1.set_xlabel("Time (ns)")
    ax1.set_ylabel("Voltage (mV)")
    ax2.imshow(
        10 * np.log10(mag**2),
        aspect="auto",
        origin="lower",
        interpolation="none",
        extent=[t[0] / 1e-9, t[-1] / 1e-9, f[0] / 1e9, f[-1] / 1e9],
        cmap=inputs["cmap"],
    )
    ax2.set_xlabel("Time (ns)")
    ax2.set_ylabel("Frequency (GHz)")
    fig.suptitle("ERROR: Program Failed", c="r", fontsize=16)

    
    plt.tight_layout()
    if inputs["save_data"] == "yes":
        fname = os.path.join(
            inputs["out_files_dir"], os.path.splitext(os.path.basename(inputs["filepath"]))[0]
        )
        unique_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(3))
        dest = f"{fname}--error_plot-{pkg_version}-{unique_id}.png"
        fig.savefig(dest)
    if inputs["display_plots"] == "yes":
        plt.show()
    
    return fig, {'error': [mag, dest if inputs["save_data"] == "yes" else None]}
