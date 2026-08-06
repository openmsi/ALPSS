import io
import pandas as pd
import logging

logger = logging.getLogger("alpss")


def extract_data(inputs):
    # Allow for option to have voltage-time data directly passed into function
    if "_data" in inputs:
        return inputs["_data"]

    t_step = 1 / inputs["sample_rate"]
    rows_to_skip = inputs["header_lines"] + inputs["time_to_skip"] / t_step
    nrows = inputs["time_to_take"] / t_step
    fname = inputs["filepath"]

    if "bytestring" in inputs and isinstance(inputs["bytestring"], bytes):
        data = pd.read_csv(
            io.BytesIO(inputs["bytestring"]),
            skiprows=int(rows_to_skip),
            nrows=int(nrows),
        )
    elif isinstance(fname, str):
        data = pd.read_csv(
            fname,
            skiprows=int(rows_to_skip),
            nrows=int(nrows),
        )
    else:
        raise TypeError(
            f"Unsupported input type, which must be 'bytestring' or 'filepath': {type(fname)}"
        )
    return data
