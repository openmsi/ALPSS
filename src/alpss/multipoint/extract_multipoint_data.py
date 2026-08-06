import os
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("alpss")


def extract_multipoint_data(inputs, multipoint_metadata=None, file_input_type="single", probe_index=0):
    """Extract the [time, voltage] pair for one probe.

    multipoint_metadata: pandas DataFrame mirroring the config's flat metadata
    table (one row per probe), must include "osc_channel" and, for
    file_input_type="separate", "pdv_filename" columns.

    file_input_type: "single" or "separate" depending on oscilloscope saving.
    "single" reads one voltage column per channel out of `inputs["filepath"]`,
    ordered by ascending osc_channel. "separate" reads each channel's own
    [time, voltage] file, located in the same directory as
    `inputs["filepath"]` but named after the probe's own
    `multipoint_metadata["pdv_filename"]` (with the same extension).

    probe_index: row of multipoint_metadata to read.
    """
    t_step = 1 / inputs["sample_rate"]
    rows_to_skip = inputs["header_lines"] + inputs["time_to_skip"] / t_step
    nrows = inputs["time_to_take"] / t_step

    channel = multipoint_metadata["osc_channel"].iloc[probe_index]

    if file_input_type == "single":
        # Column 0 is time; voltage columns follow in ascending channel order
        unique_channels = np.unique(multipoint_metadata["osc_channel"].values)
        voltage_idx = int(np.where(unique_channels == channel)[0][0]) + 1
        fname = inputs["filepath"]
        columns = [0, voltage_idx]
    elif file_input_type == "separate":
        dirname = os.path.dirname(inputs["filepath"])
        _, ext = os.path.splitext(inputs["filepath"])
        pdv_filename = multipoint_metadata["pdv_filename"].iloc[probe_index]
        fname = os.path.join(dirname, pdv_filename + ext)
        columns = [0, 1]
    else:
        raise ValueError(
            f"Unsupported file_input_type {file_input_type!r}, must be 'single' or 'separate'"
        )

    data = pd.read_csv(
        fname,
        skiprows=int(rows_to_skip),
        nrows=int(nrows),
        usecols=columns,
    )

    return data
