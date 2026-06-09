import io
import pandas as pd
import logging

logger = logging.getLogger("alpss")


def extract_data(inputs):
    t_step = 1 / inputs["sample_rate"]
    rows_to_skip = inputs["header_lines"] + inputs["time_to_skip"] / t_step

    # Allow time_to_take to be "all" to read the entire signal
    time_to_take = inputs["time_to_take"]
    if isinstance(time_to_take, str) and time_to_take.lower() == "all":
        nrows = None
    else:
        nrows = int(time_to_take / t_step)

    fname = inputs["filepath"]

    if "bytestring" in inputs and isinstance(inputs["bytestring"], bytes):
        data = pd.read_csv(
            io.BytesIO(inputs["bytestring"]),
            skiprows=int(rows_to_skip),
            nrows=nrows,
        )
    elif isinstance(fname, str):
        data = pd.read_csv(
            fname,
            skiprows=int(rows_to_skip),
            nrows=nrows,
        )
    else:
        raise TypeError(
            f"Unsupported input type, which must be 'bytestring' or 'filepath': {type(fname)}"
        )
    return data
