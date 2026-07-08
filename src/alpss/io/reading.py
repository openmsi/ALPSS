import io
import pandas as pd
import logging

logger = logging.getLogger("alpss")

# How many leading lines to scan when auto-detecting the start of the numeric
# data. Scope headers are short (Keysight ~22, LeCroy ~5); this is generous.
_MAX_HEADER_SCAN = 500


def _is_numeric_data_row(line, min_cols=2):
    """True if `line` looks like a data row: >= min_cols comma-separated fields
    whose first min_cols entries all parse as floats."""
    parts = line.split(",")
    if len(parts) < min_cols:
        return False
    try:
        for p in parts[:min_cols]:
            float(p)
    except ValueError:
        return False
    return True


def _detect_data_start(lines):
    """Return the index of the first line that is a numeric data row.

    `lines` is any iterable of strings. Skips arbitrary metadata blocks of any
    column count (e.g. LeCroy's 3-column `Segment,TrigTime,...` header) and
    column-name rows (`Time,Ampl`), stopping at the first all-numeric row."""
    for i, line in enumerate(lines):
        if i >= _MAX_HEADER_SCAN:
            break
        if _is_numeric_data_row(line):
            return i
    raise ValueError(
        f"Could not locate numeric data rows within the first {_MAX_HEADER_SCAN} "
        "lines. Check the file format or set an integer 'header_lines'."
    )


def extract_data(inputs):
    t_step = 1 / inputs["sample_rate"]
    nrows = int(inputs["time_to_take"] / t_step)
    fname = inputs["filepath"]
    header_lines = inputs.get("header_lines", "auto")

    # Resolve the raw source into a fresh reader factory so we can both scan for
    # the data start and hand a clean stream to pandas.
    if "bytestring" in inputs and isinstance(inputs["bytestring"], bytes):
        raw = inputs["bytestring"]
        make_reader = lambda: io.BytesIO(raw)
        text_lines = lambda: raw.decode("utf-8", errors="replace").splitlines()
    elif isinstance(fname, str):
        make_reader = lambda: fname
        text_lines = lambda: _read_lines(fname)
    else:
        raise TypeError(
            f"Unsupported input type, which must be 'bytestring' or 'filepath': {type(fname)}"
        )

    if isinstance(header_lines, str) and header_lines.lower() == "auto":
        # Auto-detect: skip everything up to the first numeric row. header=None
        # so the first data sample is preserved (no row consumed as a header).
        data_start = _detect_data_start(text_lines())
        rows_to_skip = int(data_start + inputs["time_to_skip"] / t_step)
        header = None
        logger.debug("Auto-detected data start at line %d", data_start)
    else:
        # Legacy behavior: caller supplies the header line count explicitly and
        # pandas consumes the next row as the column header.
        rows_to_skip = int(header_lines + inputs["time_to_skip"] / t_step)
        header = 0

    data = pd.read_csv(make_reader(), skiprows=rows_to_skip, nrows=nrows, header=header)

    # Downstream code assumes exactly two columns (Time, Ampl). Some exports
    # (e.g. multi-channel LeCroy) carry extra columns; keep the first two.
    if data.shape[1] < 2:
        raise ValueError(
            f"Expected at least 2 data columns, parsed {data.shape[1]}. "
            "Check 'header_lines'/'sample_rate' or the file format."
        )
    return data.iloc[:, :2]


def _read_lines(path):
    with open(path, "r") as f:
        for line in f:
            yield line
