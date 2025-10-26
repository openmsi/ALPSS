import os
from alpss.spall_doi_finder import spall_doi_finder
from alpss.plotting import plot_results, plot_voltage
from alpss.carrier_frequency import carrier_frequency
from alpss.carrier_filter import carrier_filter
from alpss.velocity_calculation import velocity_calculation
from alpss.validation import validate_inputs
from alpss.spall_analysis import spall_analysis
from alpss.full_uncertainty_analysis import full_uncertainty_analysis
from alpss.instantaneous_uncertainty_analysis import instantaneous_uncertainty_analysis
from alpss.utils import extract_data
from alpss.saving import save
from datetime import datetime
import traceback
import logging

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

# main function to link together all the sub-functions
def alpss_main(**inputs):
    # Convert filename + exp_data_dir to filepath if needed
    if "filename" in inputs and "filepath" not in inputs:
        filename = inputs["filename"]
        exp_data_dir = inputs.get("exp_data_dir", "")
        inputs["filepath"] = os.path.join(exp_data_dir, filename)
    
    # validate the inputs for the run
    validate_inputs(inputs)
    # attempt to run the program in full
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

        # function to find points of interest on the velocity trace
        sa_out = spall_analysis(vc_out, iua_out, **inputs)

        # function to calculate uncertainties in the spall strength and strain rate due to external uncertainties
        fua_out = full_uncertainty_analysis(cen, sa_out, iua_out, **inputs)

        # end the program timer
        end_time = datetime.now()

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

        # function to save the output files if desired
        # MOVED to plotting
        # end final timer and display full runtime
        end_time2 = datetime.now()
        logger.info(
            f"\nFull program runtime (including plotting and saving):\n{end_time2 - start_time}\n"
        )

        # return the figure so it can be saved if desired
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
            **inputs,
        )

        return (fig, items)

    # in case the program throws an error
    except Exception as e:
        logger.error("Error in the execution of the main program:: %s", str(e))
        logger.error("Traceback: %s", traceback.format_exc())

        # attempt to plot the voltage signal from the imported data
        try:
            logger.info("Attempting a fallback visualization of the voltage signal...")
            fig, items = plot_voltage(data, **inputs)
            logger.info("Fallback visualization was succexssful.")
            return (fig, items)

        # if that also fails then log the traceback and stop running the program
        except Exception as e:
            logger.error(
                "Error in the fallback visualization of the voltage signal: %s", str(e)
            )
            logger.error("Traceback: %s", traceback.format_exc())
