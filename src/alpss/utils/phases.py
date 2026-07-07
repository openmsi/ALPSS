import logging
import traceback
from datetime import datetime
import os
import numpy as np

from alpss.io.reading import extract_data
from alpss.io.saving import save
from alpss.detection.spall_doi_finder import spall_doi_finder
from alpss.carrier.frequency import carrier_frequency
from alpss.carrier.filter import carrier_filter
from alpss.velocity.calculation import velocity_calculation
from alpss.analysis.instantaneous_uncertainty import instantaneous_uncertainty_analysis
from alpss.analysis.velocity_uncertainty import velocity_uncertainty_analysis
from alpss.analysis.spall import spall_analysis
from alpss.analysis.spall_uncertainty import spall_uncertainty_analysis
from alpss.analysis.shock import shock_analysis
from alpss.analysis.hel import hel_detection
from alpss.plotting.plots import plot_results
from alpss.plotting.hel import plot_hel_detection
from alpss.utils.defaults import (
    default_spall_output,
    default_spall_uncertainty_output,
    default_shock_output,
    default_hel_output,
)

logger = logging.getLogger("alpss")


def run_velocity_phase(**inputs) -> tuple:
    """Run Phase 1 (velocity processing). Returns (vel_out, velocity_ok, error_msg)."""
    start_time = datetime.now()
    velocity_ok = True
    errors = []
    vel_out = {}

    try:
        data = extract_data(inputs)
        logger.info("Extracted %d samples", len(data))

        sdf_out = spall_doi_finder(data, **inputs)
        logger.info(
            "Spall DOI found: start=%.3e s, end=%.3e s",
            sdf_out["t_doi_start"],
            sdf_out["t_doi_end"],
        )
        vel_out["sdf_out"] = sdf_out

        cen = carrier_frequency(sdf_out, **inputs)
        logger.info("Carrier frequency: %.6e Hz", cen)
        vel_out["cen"] = cen

        cf_out = carrier_filter(sdf_out, cen, **inputs)
        logger.info("Carrier filter applied")
        vel_out["cf_out"] = cf_out

        vc_out = velocity_calculation(sdf_out, cen, cf_out, **inputs)
        logger.info("Velocity calculated (%d points)", len(vc_out["time_f"]))
        vel_out["vc_out"] = vc_out

        iua_out = instantaneous_uncertainty_analysis(sdf_out, vc_out, cen, **inputs)
        logger.info("Instantaneous uncertainty computed")
        vel_out["iua_out"] = iua_out

        vu_out = velocity_uncertainty_analysis(vc_out, iua_out)
        vel_out["vu_out"] = vu_out
        logger.info("Velocity uncertainties computed")

        logger.info("Velocity processing complete")

        min_velocity = inputs["min_velocity_threshold"]
        max_uncertainty = inputs["max_velocity_uncertainty_threshold"]

        # min velocity qualifier
        if vc_out['v_max_comp'] < min_velocity:
            velocity_ok = False
            errors.append(f"Velocity {vc_out['v_max_comp']} did not exceed minimum velocity of ({min_velocity})")

        # max uncertainty qualifier
        if vu_out['peak_velocity_vel_uncert'] > max_uncertainty:
            velocity_ok = False
            errors.append(f"Uncertainty of value {vu_out['peak_velocity_vel_uncert']} is too high (>{max_uncertainty})")

    except Exception as e:
        velocity_ok = False
        errors.append(str(e))
        logger.error("Error in velocity processing: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        try:
            from alpss.plotting.plots import plot_voltage

            plot_voltage(extract_data(inputs), errors=errors, **inputs)
        except Exception:
            logger.error("Fallback voltage plot also failed.")
        # Re-raise to exit pipeline early after fallback plot
        raise

    end_time = datetime.now()
    vel_out["start_time"] = start_time
    vel_out["end_time"] = end_time
    error_msg = f"velocity: {'; '.join(errors)}" if errors else None
    return vel_out, velocity_ok, error_msg


def run_spall_phase(vc_out, iua_out, **inputs) -> tuple:
    """Phase 2a: Spall analysis (optional). Returns (sa_out, spall_ok, error_msg)."""
    sa_out = default_spall_output()
    spall_ok = False
    error_msg = None

    if inputs["spall_enabled"]:
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
            error_msg = f"spall: {e}"
            logger.error("Error in spall analysis: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            logger.info("Continuing without spall analysis.")

    return sa_out, spall_ok, error_msg


def run_spall_uncertainty_phase(cen, vc_out, vu_out, sa_out, iua_out, spall_ok, **inputs) -> tuple:
    """Phase 2b: Spall uncertainty analysis. Returns (sua_out, spall_uncertainty_ok, error_msg)."""
    sua_out = default_spall_uncertainty_output()
    spall_uncertainty_ok = False
    error_msg = None

    if not spall_ok:
        error_msg = "spall_uncertainty: skipped due to spall_ok=false"
        logger.info(error_msg)
        return sua_out, spall_uncertainty_ok, error_msg

    try:
        logger.info("Running spall uncertainty analysis...")
        sua_out = spall_uncertainty_analysis(cen, vc_out, vu_out, iua_out, **inputs)
        spall_uncertainty_ok = True
        logger.info(
            "Spall uncertainty analysis complete."
        )
    except Exception as e:
        error_msg = f"spall_uncertainty: {e}"
        logger.error("Error in spall uncertainty analysis: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        logger.info("Continuing without spall uncertainty analysis.")

    return sua_out, spall_uncertainty_ok, error_msg


def run_hel_phase(vc_out, iua_out, **inputs) -> tuple:
    """Phase 2c: HEL detection (optional). Returns (hel_out, error_msg)."""
    hel_out = default_hel_output()
    error_msg = None

    if inputs["hel_enabled"]:
        try:
            logger.info("Running HEL detection...")
            # Convert velocity time from seconds to nanoseconds for HEL
            time_ns = vc_out["time_f"] / 1e-9
            hel_out = hel_detection(
                time_ns,
                vc_out["velocity_f_smooth"],
                iua_out["vel_uncert"],
                hel_start_ns=inputs.get("hel_start_time_ns"),
                hel_end_ns=inputs.get("hel_end_time_ns"),
                angle_threshold_deg=inputs.get("hel_angle_threshold_deg"),
                min_points=inputs.get("hel_detection_min_points"),
                min_velocity=inputs.get("minimum_HEL_velocity_expected"),
                density=inputs.get("density"),
                C_L=inputs.get("C_L"),
            )
            if hel_out.ok:
                logger.info(
                    "HEL detected: strength=%.4f GPa, FSV=%.2f m/s, time=%.2f ns",
                    hel_out.strength_gpa,
                    hel_out.free_surface_velocity,
                    hel_out.time_detection_ns,
                )
            else:
                if hel_out.error_message:
                    error_msg = f"hel: {hel_out.error_message}"
                logger.info("HEL detection complete: no HEL found")
        except Exception as e:
            error_msg = f"hel: {e}"
            logger.error("Error in HEL detection: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            logger.info("Continuing without HEL results.")

    return hel_out, error_msg


def run_shock_phase(vc_out, **inputs) -> tuple:
    """Phase 2d: Shock analysis. Returns (shock_out, error_msg)."""
    shock_out = default_shock_output()
    error_msg = None

    try:
        logger.info("Running shock analysis...")
        shock_out = shock_analysis(vc_out, **inputs)
        logger.info("Shock analysis complete: peak shock stress=%.4f Pa", shock_out["peak_shock_stress"])
    except Exception as e:
        error_msg = f"shock: {e}"
        logger.error("Error in shock analysis: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        logger.info("Continuing without shock analysis.")

    return shock_out, error_msg


def run_output_phase(
    sdf_out,
    cen,
    cf_out,
    vc_out,
    vu_out,
    sa_out,
    iua_out,
    sua_out,
    shock_out,
    hel_out,
    start_time,
    end_time,
    velocity_ok,
    spall_ok,
    spall_uncertainty_ok,
    errors,
    **inputs,
) -> tuple:
    """Phase 3: Output (plotting + saving). Returns (fig, hel_fig, items)."""
    # Generate plots
    logger.info("Generating plots...")
    fig = plot_results(
        sdf_out,
        cen,
        cf_out,
        vc_out,
        vu_out,
        sa_out,
        iua_out,
        sua_out,
        shock_out,
        start_time,
        end_time,
        velocity_ok,
        spall_ok,
        spall_uncertainty_ok,
        hel_out.ok,
        **inputs,
    )

    # Generate HEL diagnostic plot
    hel_fig = None
    if hel_out.ok:
        try:
            time_ns = vc_out["time_f"] / 1e-9
            hel_fig = plot_hel_detection(
                time_ns,
                vc_out["velocity_f_smooth"],
                hel_out,
                hel_start_ns=inputs["hel_start_time_ns"],
                hel_end_ns=inputs["hel_end_time_ns"],
                angle_threshold_deg=inputs["hel_angle_threshold_deg"],
                sample_name=os.path.basename(inputs.get("filepath", "")),
            )
            if not inputs["display_plots"]:
                import matplotlib.pyplot as _plt

                _plt.close(hel_fig)
        except Exception as e:
            logger.error("Error generating HEL plot: %s", str(e))

    logger.info("Plots generated")

    # Save outputs
    logger.info("Saving outputs...")
    items = save(
        sdf_out,
        cen,
        vc_out,
        vu_out,
        sa_out,
        iua_out,
        sua_out,
        shock_out,
        start_time,
        end_time,
        fig,
        velocity_ok,
        spall_ok,
        spall_uncertainty_ok,
        iq_fig=sdf_out.get("iq_fig"),
        hel_fig=hel_fig,
        hel_out=hel_out,
        error_msg="; ".join(errors) if errors else "",
        **inputs,
    )

    logger.info("Outputs saved")

    return fig, hel_fig, items
