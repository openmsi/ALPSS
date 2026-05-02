import os
from alpss.plotting.plots import plot_results, plot_voltage
from alpss.plotting.hel import plot_hel_detection
from alpss.validation import validate_inputs
from alpss.analysis.spall import spall_analysis
from alpss.analysis.full_uncertainty import full_uncertainty_analysis
from alpss.analysis.hel.hel import hel_detection
from alpss.io.saving import save
from alpss.utils.phases import run_velocity_phase
from alpss.utils.defaults import (
    default_spall_output,
    default_uncertainty_output,
    default_hel_output,
)
from alpss.utils.logging import setup_alpss_logger
from datetime import datetime
import traceback
import numpy as np


logger = setup_alpss_logger()


# main function to link together all the sub-functions
def alpss_main(**inputs):
    # validate the inputs for the run
    validate_inputs(inputs)

    # --- Phase 1: Velocity Processing ---
    try:
        vel = run_velocity_phase(**inputs)
    except Exception as e:
        logger.error("Error in velocity processing: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        try:
            from alpss.utils.helpers import extract_data

            plot_voltage(extract_data(inputs), **inputs)
        except Exception:
            logger.error("Fallback voltage plot also failed.")
        raise

    sdf_out = vel["sdf_out"]
    cen = vel["cen"]
    cf_out = vel["cf_out"]
    vc_out = vel["vc_out"]
    iua_out = vel["iua_out"]
    start_time = vel["start_time"]
    end_time = vel["end_time"]

    # --- Phase 2a: Spall analysis ---
    errors = []
    sa_out = default_spall_output()
    spall_ok = False
    try:
        logger.info("Running spall analysis...")
        sa_out = spall_analysis(vc_out, iua_out, **inputs)
        spall_ok = True
        logger.info(
            "Spall analysis complete: spall strength=%.4f, strain rate=%.4e",
            sa_out["spall_strength_est"],
            sa_out["strain_rate_est"],
        )
    except Exception as e:
        errors.append(f"spall: {e}")
        logger.error("Error in spall analysis: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        logger.info("Continuing without spall analysis.")

    # --- Phase 2b: Full uncertainty analysis ---
    fua_out = default_uncertainty_output()
    uncertainty_ok = False
    if not spall_ok:
        logger.info("Skipping uncertainty analysis: spall analysis did not succeed.")
        errors.append(f"uncertainty: analysis skipped due to spall_ok=false")
    else:
        try:
            logger.info("Running full uncertainty analysis...")
            fua_out = full_uncertainty_analysis(cen, sa_out, iua_out, **inputs)
            uncertainty_ok = True
            logger.info(
                "Uncertainty analysis complete: spall uncertainty=%.4f, strain rate uncertainty=%.4e",
                fua_out["spall_uncert"],
                fua_out["strain_rate_uncert"],
            )
        except Exception as e:
            errors.append(f"uncertainty: {e}")
            logger.error("Error in uncertainty analysis: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            logger.info("Continuing without uncertainty analysis.")

    # --- Phase 2c: HEL detection (optional) ---
    hel_out = default_hel_output()
    hel_enabled = inputs.get("hel_detection_enabled")
    if hel_enabled:
        try:
            logger.info("Running HEL detection...")
            # Convert velocity time from seconds to nanoseconds for HEL
            # AND zero the time to signal start time
            t_start_corrected = sdf_out["t_start_corrected"]
            time_ns = (vc_out["time_f"] - t_start_corrected) / 1e-9
            hel_out = hel_detection(
                time_ns,
                vc_out["velocity_f_smooth"],
                iua_out["vel_uncert"],
                hel_start_ns=inputs["hel_start_time_ns"],
                hel_end_ns=inputs["hel_end_time_ns"],
                angle_threshold_deg=inputs["hel_angle_threshold_deg"],
                min_points=inputs["hel_detection_min_points"],
                min_velocity=inputs["minimum_HEL_velocity_expected"],
                density=inputs.get("density"),
                acoustic_velocity=inputs.get("C0"),
                C_L=inputs.get("C_L"),
                method=inputs["hel_method"],
                hel_rdp_epsilon=inputs["hel_rdp_epsilon"],
                hel_slope_drop_ratio=inputs["hel_slope_drop_ratio"],
                hel_min_plateau_duration=inputs["hel_min_plateau_duration"],
            )
            if hel_out.ok:
                logger.info(
                    "HEL detected: strength=%.4f GPa, FSV=%.2f m/s, time=%.2f ns (method=%s)",
                    hel_out.strength_gpa,
                    hel_out.free_surface_velocity,
                    hel_out.time_detection_ns,
                    hel_out.method,
                )
            else:
                if hel_out.error_message:
                    errors.append(f"hel: {hel_out.error_message}")
                logger.info("HEL detection complete: no HEL found")
        except Exception as e:
            errors.append(f"hel: {e}")
            logger.error("Error in HEL detection: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            logger.info("Continuing without HEL results.")

    # --- Phase 3: Output (plotting + saving) ---
    end_time_final = datetime.now()

    # function to generate the final figure
    logger.info("Generating plots...")
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

    # Generate HEL diagnostic plot as a separate figure
    hel_fig = None
    if hel_enabled and hel_out.ok:
        try:
            time_ns = vc_out["time_f"] / 1e-9
            hel_fig = plot_hel_detection(
                time_ns - t_start_corrected * 1e9,
                vc_out["velocity_f_smooth"],
                hel_out,
                hel_start_ns=inputs.get("hel_start_time_ns"),
                hel_end_ns=inputs.get("hel_end_time_ns"),
                angle_threshold_deg=inputs.get("hel_angle_threshold_deg"),
                sample_name=os.path.basename(inputs.get("filepath", "")),
                sample_material=inputs.get("material", ""),
            )
            if inputs.get("display_plots") != "yes":
                import matplotlib.pyplot as _plt

                _plt.close(hel_fig)
        except Exception as e:
            logger.error("Error generating HEL plot: %s", str(e))

    logger.info(f"\nFull runtime: {end_time_final - start_time}\n")

    logger.info("Plots generated")

    # function to save the output files if desired
    logger.info("Saving outputs...")
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
        iq_fig=sdf_out.get("iq_fig"),
        hel_fig=hel_fig,
        hel_out=hel_out if hel_enabled else None,
        spall_ok=spall_ok,
        uncertainty_ok=uncertainty_ok,
        error_msg="; ".join(errors) if errors else "",
        **inputs,
    )

    logger.info("Outputs saved")

    return (fig, items)
