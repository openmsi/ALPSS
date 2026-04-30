import os
from alpss.detection.spall_doi_finder import spall_doi_finder
from alpss.plotting.plots import plot_results, plot_voltage
from alpss.plotting.hel import plot_hel_detection
from alpss.carrier.frequency import carrier_frequency
from alpss.carrier.filter import carrier_filter
from alpss.velocity.calculation import velocity_calculation
from alpss.validation import validate_inputs
from alpss.analysis.spall import spall_analysis, spall_analysis_with_dns, SpallResult
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
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = (
            False  # prevent duplicate output via root logger (e.g. in Jupyter)
        )

    # Otherwise (if processor already set things up) → just use its config
    return logger


logger = setup_alpss_logger()


def _default_spall_output():
    """Return NaN-filled spall analysis output for graceful degradation."""
    return {
        "t_max_comp": np.nan,
        "t_max_ten": np.nan,
        "t_rc": np.nan,
        "v_max_comp": np.nan,
        "v_max_ten": np.nan,
        "v_rc": np.nan,
        "spall_strength_est": np.nan,
        "strain_rate_est": np.nan,
        "peak_velocity_freq_uncert": np.nan,
        "peak_velocity_vel_uncert": np.nan,
        "max_ten_freq_uncert": np.nan,
        "max_ten_vel_uncert": np.nan,
    }


def _default_uncertainty_output():
    """Return NaN-filled uncertainty output for graceful degradation."""
    return {"spall_uncert": np.nan, "strain_rate_uncert": np.nan}


def _default_hel_output():
    """Return a failed HEL result for graceful degradation."""
    from alpss.analysis.hel import HELResult

    return HELResult(ok=False)


def _default_spall_result():
    """Return a failed SpallResult for graceful degradation."""
    return SpallResult(ok=False, dns_classification="analysis not run")


# main function to link together all the sub-functions
def alpss_main(**inputs):
    # validate the inputs for the run
    validate_inputs(inputs)

    # --- Phase 1: Velocity Processing ---
    try:
        start_time = datetime.now()
        data = extract_data(inputs)
        logger.info(
            "Signal: %s | %d samples | %.2f GS/s | window %.1f–%.1f µs (%.1f µs duration)",
            os.path.basename(inputs.get("filepath", "")),
            len(data),
            inputs.get("sample_rate", 0) / 1e9,
            inputs.get("time_to_skip", 0) / 1e-6,
            (inputs.get("time_to_skip", 0) + inputs.get("time_to_take", 0)) / 1e-6,
            inputs.get("time_to_take", 0) / 1e-6,
        )

        # function to find the spall signal domain of interest
        logger.info("Finding spall domain of interest...")
        sdf_out = spall_doi_finder(data, **inputs)
        logger.info(
            "Spall DOI found: start=%.3e s, end=%.3e s",
            sdf_out["t_doi_start"],
            sdf_out["t_doi_end"],
        )

        # function to find the carrier frequency
        logger.info("Estimating carrier frequency...")
        cen = carrier_frequency(sdf_out, **inputs)
        logger.info("Carrier frequency: %.6e Hz", cen)

        # function to filter out the carrier frequency after the signal has started
        logger.info("Filtering carrier frequency...")
        cf_out = carrier_filter(sdf_out, cen, **inputs)
        logger.info("Carrier filter applied")

        # function to calculate the velocity from the filtered voltage signal
        logger.info("Calculating velocity...")
        vc_out = velocity_calculation(sdf_out, cen, cf_out, **inputs)
        logger.info("Velocity calculated (%d points)", len(vc_out["time_f"]))

        # function to estimate the instantaneous uncertainty for all points in time
        logger.info("Computing instantaneous uncertainty...")
        iua_out = instantaneous_uncertainty_analysis(sdf_out, vc_out, cen, **inputs)
        logger.info("Uncertainty computed")

        # end the velocity processing timer
        end_time = datetime.now()
        logger.info("Velocity processing complete in %s", end_time - start_time)

    except Exception as e:
        logger.error("Error in velocity processing: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        # Try to save a fallback voltage plot for diagnostics
        try:
            logger.info("Attempting a fallback visualization of the voltage signal...")
            plot_voltage(data, **inputs)
            logger.info("Fallback voltage plot saved.")
        except Exception:
            logger.error("Fallback visualization also failed.")
        # Re-raise so the caller can track this as a failure
        raise

    # --- Phase 2a: Spall analysis ---
    errors = []
    sa_out = _default_spall_output()
    spall_result = _default_spall_result()
    spall_ok = False
    spall_detection_method = inputs.get("spall_detection_method", "max_min")
    use_dns = inputs.get("spall_calculation", "yes") == "yes"
    try:
        logger.info("Running spall analysis (method=%s)...", spall_detection_method)
        sa_out = spall_analysis(vc_out, iua_out, **inputs)
        spall_ok = True
        logger.info(
            "Spall analysis complete: spall strength=%.4f Pa, strain rate=%.4e s^-1",
            sa_out["spall_strength_est"],
            sa_out["strain_rate_est"],
        )
        if use_dns:
            spall_result = spall_analysis_with_dns(
                vc_out, iua_out,
                spall_detection_method=spall_detection_method,
                rdp_epsilon=inputs.get("spall_rdp_epsilon", 5.0),
                min_pullback_velocity=inputs.get("min_pullback_velocity", 10.0),
                min_recomp_ratio=inputs.get("min_recomp_ratio", 0.03),
                min_recomp_velocity_ratio=inputs.get("min_recomp_velocity_ratio", 1.10),
                min_recomp_time_ns=inputs.get("min_recomp_time_ns", 2.5),
                **inputs,
            )
            logger.info(
                "DNS classification: %s (ok=%s)",
                spall_result.dns_classification,
                spall_result.ok,
            )
    except Exception as e:
        errors.append(f"spall: {e}")
        logger.error("Error in spall analysis: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())
        logger.info("Continuing without spall analysis.")

    # --- Phase 2b: Full uncertainty analysis ---
    fua_out = _default_uncertainty_output()
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
    hel_out = _default_hel_output()
    hel_enabled = inputs.get("hel_detection_enabled", False)
    if hel_enabled:
        try:
            logger.info("Running HEL detection...")
            # Convert velocity time from seconds to nanoseconds for HEL
            time_ns = vc_out["time_f"] / 1e-9
            hel_method = inputs.get("hel_method", "gradient")
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
                method=hel_method,
                hel_rdp_epsilon=inputs.get("hel_rdp_epsilon", 1.25),
                hel_slope_drop_ratio=inputs.get("hel_slope_drop_ratio", 0.9),
                hel_min_plateau_duration=inputs.get("hel_min_plateau_duration", 0.5),
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
                time_ns,
                vc_out["velocity_f_smooth"],
                hel_out,
                hel_start_ns=inputs.get("hel_start_time_ns", 0.0),
                hel_end_ns=inputs.get("hel_end_time_ns", time_ns[-1]),
                angle_threshold_deg=inputs.get("hel_angle_threshold_deg", 45.0),
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
        spall_result=spall_result,
        **inputs,
    )

    logger.info("Outputs saved")

    return (fig, items)
