import io
import re
import pandas as pd
import logging

logger = logging.getLogger("alpss")

# How many leading lines to scan when locating the start of the numeric data.
# Scope headers are short (Keysight ~24, LeCroy ~5); this is generous.
_MAX_HEADER_SCAN = 500

# Voltage columns of a multi-channel export are labelled "Channel N". The
# number is the oscilloscope channel and need not match the column position --
# a file may hold channels 2, 3, 4 in positions 1, 2, 3.
_CHANNEL_LABEL = re.compile(r"^Channel\s*(\d+)$", re.IGNORECASE)

# Number of leading samples used to measure the sample interval.
_RATE_PROBE_ROWS = 1000


def _is_numeric_data_row(line, min_cols=2):
    """True if `line` looks like a data row: at least min_cols comma-separated
    fields whose first min_cols entries all parse as floats."""
    parts = line.split(",")
    if len(parts) < min_cols:
        return False
    try:
        for p in parts[:min_cols]:
            float(p)
    except ValueError:
        return False
    return True


def _iter_header_lines(inputs):
    """Yield the leading text lines of the raw source (file or bytestring)."""
    if "bytestring" in inputs and isinstance(inputs["bytestring"], bytes):
        text = inputs["bytestring"].decode("utf-8", errors="replace")
        for line in text.splitlines():
            yield line
        return

    fname = inputs["filepath"]
    if not isinstance(fname, str):
        raise TypeError(
            f"Unsupported input type, which must be 'bytestring' or 'filepath': {type(fname)}"
        )
    with open(fname, "r") as f:
        for line in f:
            yield line


def sniff_header(inputs):
    """Locate the numeric data and the column labels that precede it.

    Scope exports vary in header length and column count, so the data start is
    found by scanning for the first all-numeric row rather than trusting a
    caller-supplied line count. Returns (data_start, labels, n_cols):

    data_start  index of the first numeric row
    labels      column names from the last non-numeric row before the data,
                or None if the data begins at the first line
    n_cols      number of columns in the data
    """
    previous = None
    for i, line in enumerate(_iter_header_lines(inputs)):
        if i >= _MAX_HEADER_SCAN:
            break
        if _is_numeric_data_row(line):
            labels = (
                [c.strip() for c in previous.split(",")] if previous is not None else None
            )
            return i, labels, len(line.split(","))
        previous = line

    raise ValueError(
        f"Could not locate numeric data rows within the first {_MAX_HEADER_SCAN} "
        "lines. Check the file format."
    )


def channel_columns(labels, n_cols):
    """Map oscilloscope channel number -> column index for the voltage columns.

    Column 0 is always time. Multi-channel exports name the rest "Channel N";
    single-probe files ("Time,Voltage", "Time,Ampl") carry no channel labels,
    so their columns are numbered from 1 by position.
    """
    columns = {}
    if labels:
        for idx, name in enumerate(labels[1:n_cols], start=1):
            match = _CHANNEL_LABEL.match(name)
            if match:
                columns[int(match.group(1))] = idx

    if not columns:
        columns = {idx: idx for idx in range(1, n_cols)}

    return columns


def _source(inputs):
    """A fresh readable source for pd.read_csv (file path or bytestring)."""
    if "bytestring" in inputs and isinstance(inputs["bytestring"], bytes):
        return io.BytesIO(inputs["bytestring"])
    return inputs["filepath"]


def extract_data(inputs):
    """Read one channel of a scope export as an (N, 2) array of [time, voltage].

    The analysis works on a plain array; everything that knows about file
    formats -- header length, column labels, which channel -- stops here.
    """
    data_start, labels, n_cols = sniff_header(inputs)
    if "header_lines" in inputs:
        logger.warning(
            "Ignoring header_lines=%s; data start auto-detected at line %d.",
            inputs["header_lines"],
            data_start,
        )

    # the sample interval is measured from the time column, so time_to_skip
    # and time_to_take convert to the right row counts whatever the scope.
    # Timestamps are written with limited precision, so individual steps are
    # quantized; averaging over the whole probe span is exact to ~1e-10.
    probe = (
        pd.read_csv(
            _source(inputs),
            skiprows=data_start,
            nrows=_RATE_PROBE_ROWS,
            header=None,
            usecols=[0],
        )
        .to_numpy(dtype=float)
        .ravel()
    )
    if len(probe) < 2:
        raise ValueError("Need at least 2 samples to measure the sample rate.")
    t_step = (probe[-1] - probe[0]) / (len(probe) - 1)
    if "sample_rate" in inputs:
        logger.warning(
            "Ignoring sample_rate=%s; measured %.6g Hz from the time column.",
            inputs["sample_rate"],
            1 / t_step,
        )
    # time_to_take="all" reads to the end of the file
    if inputs["time_to_take"] == "all":
        nrows = None
    else:
        nrows = round(inputs["time_to_take"] / t_step)

    columns = channel_columns(labels, n_cols)
    channel = inputs.get("channel")
    if channel is None:
        # Default to the first voltage column, so a single-probe run against a
        # multi-channel file reads the first channel.
        channel = min(columns)
        voltage_col = columns[channel]
        chosen_by = "defaulted to"
    elif channel in columns:
        voltage_col = columns[channel]
        chosen_by = "requested"
    else:
        raise ValueError(
            f"Channel {channel!r} not found in {inputs.get('filepath')!r}. "
            f"Available channels: {sorted(columns)}."
        )

    # record what was actually read, so the results and plots can report it even
    # when the caller did not name a channel
    inputs["channel"] = channel

    logger.info(
        "Reading channel %s (%s, column %d of %d) from %s; available channels: %s",
        channel,
        chosen_by,
        voltage_col,
        n_cols,
        inputs.get("filepath", "<bytestring>"),
        sorted(columns),
    )

    rows_to_skip = data_start + round(inputs["time_to_skip"] / t_step)

    # header=None because the label row is skipped outright -- letting pandas
    # infer a header here would consume the first data sample.
    data = pd.read_csv(
        _source(inputs),
        skiprows=rows_to_skip,
        nrows=nrows,
        header=None,
        usecols=[0, voltage_col],
    )

    if data.shape[1] < 2:
        raise ValueError(
            f"Expected at least 2 data columns, parsed {data.shape[1]}. "
            "Check 'time_to_skip' or the file format."
        )

    return data.to_numpy(dtype=float)
