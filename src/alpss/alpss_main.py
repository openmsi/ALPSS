import os
from alpss.detection.spall_doi_finder import spall_doi_finder
from alpss.plotting.plots import plot_results, plot_voltage
from alpss.carrier.frequency import carrier_frequency
from alpss.carrier.filter import carrier_filter
from alpss.velocity.calculation import velocity_calculation
from alpss.validation import validate_inputs
from alpss.analysis.spall import spall_analysis
from alpss.analysis.full_uncertainty import full_uncertainty_analysis
from alpss.analysis.instantaneous_uncertainty import instantaneous_uncertainty_analysis
from alpss.analysis.hel import hel_detection
from alpss.utils import extract_data
from alpss.io.saving import save
from datetime import datetime
import traceback
import logging
import numpy as np

def setup_alpss_logger():
    logger = logging.getLogger("alpss")

    if not logger.handlers:  # no handlers = nothing configured yet
        # Standalone mode → set up a default
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    # Otherwise (if processor already set things up) → just use its config
    return logger

logger = setup_alpss_logger()


def _default_spall_output():
    """Return NaN-filled spall analysis output for graceful degradation."""
    return {
        "t_max_comp": np.nan, "t_max_ten": np.nan, "t_rc": np.nan,
        "v_max_comp": np.nan, "v_max_ten": np.nan, "v_rc": np.nan,
        "spall_strength_est": np.nan, "strain_rate_est": np.nan,
        "peak_velocity_freq_uncert": np.nan, "peak_velocity_vel_uncert": np.nan,
        "max_ten_freq_uncert": np.nan, "max_ten_vel_uncert": np.nan,
    }


def _default_uncertainty_output():
    """Return NaN-filled uncertainty output for graceful degradation."""
    return {"spall_uncert": np.nan, "strain_rate_uncert": np.nan}


def _default_hel_output():
    """Return a failed HEL result for graceful degradation."""
    from alpss.analysis.hel import HELResult
    return HELResult(ok=False)


# main function to link together all the sub-functions
def alpss_main(**inputs):
    # validate the inputs for the run
    validate_inputs(inputs)

    # --- Phase 1: Velocity Processing ---
    try:
        # begin the program timer
        start_time = datetime.now()
        data = extract_data(inputs)

        # function to find the spall signal domain of interest
        sdf_out = spall_doi_finder(data, **inputs)

        # function to find the carrier frequency
        cen = carrier_frequency(sdf_out, **inputs)

        # function to filter out the carrier frequency after the signal has started
        cf_out = carrier_filter(sdf_out, cen, **inputs)

        # function to calculate the velocity from the filtered voltage signal
        vc_out = velocity_calculation(sdf_out, cen, cf_out, **inputs)

        # function to estimate the instantaneous uncertainty for all points in time
        iua_out = instantaneous_uncertainty_analysis(sdf_out, vc_out, cen, **inputs)

        # end the velocity processing timer
        end_time = datetime.now()

    except Exception as e:
        logger.error("Error in velocity processing: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        try:
            logger.info("Attempting a fallback visualization of the voltage signal...")
            fig, items = plot_voltage(data, **inputs)
            logger.info("Fallback visualization was successful.")
            return (fig, items)
        except Exception as e2:
            logger.error("Fallback visualization also failed: %s", str(e2))
        return None

    # --- Phase 2: Analysis (spall points + uncertainties) ---
    try:
        sa_out = spall_analysis(vc_out, iua_out, **inputs)
        fua_out = full_uncertainty_analysis(cen, sa_out, iua_out, **inputs)
    except Exception as e:
        logger.error("Error in analysis phase: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        logger.info("Continuing with velocity results only (no spall analysis).")
        sa_out = _default_spall_output()
        fua_out = _default_uncertainty_output()

    # --- Phase 2b: HEL detection (optional) ---
    hel_out = _default_hel_output()
    hel_enabled = inputs.get("hel_detection_enabled", False)
    if hel_enabled:
        try:
            # Convert velocity time from seconds to nanoseconds for HEL
            time_ns = vc_out["time_f"] / 1e-9
            hel_out = hel_detection(
                time_ns,
                vc_out["velocity_f_smooth"],
                iua_out["vel_uncert"],
                hel_start_ns=inputs.get("hel_start_time_ns", 0.0),
                hel_end_ns=inputs.get("hel_end_time_ns", None),
                angle_threshold_deg=inputs.get("hel_angle_threshold_deg", 45.0),
                min_points=inputs.get("hel_detection_min_points", 3),
                min_velocity=inputs.get("minimum_HEL_velocity_expected", 10.0),
                density=inputs.get("density", None),
                acoustic_velocity=inputs.get("C0", None),
                C_L=inputs.get("C_L", None),
            )
        except Exception as e:
            logger.error("Error in HEL detection: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            logger.info("Continuing without HEL results.")

    # --- Phase 3: Output (plotting + saving) ---
    end_time_final = datetime.now()

    # function to generate the final figure
    fig = plot_results(
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
    )

    logger.info(
        f"\nFull runtime: {end_time_final - start_time}\n"
    )

    # function to save the output files if desired
    items = save(
        sdf_out,
        cen,
        vc_out,
        sa_out,
        iua_out,
        fua_out,
        start_time,
        end_time,
        fig,
        hel_out=hel_out,
        **inputs,
    )

    return (fig, items)
