import logging
import os

from alpss.alpss_main import alpss_main
from alpss.carrier.frequency import prescan_carrier
from alpss.io.reading import extract_data, list_channels
from alpss.multipoint.combine import combine_probes
from alpss.utils.config import flatten_config
from alpss.utils.validation import validate_inputs

logger = logging.getLogger("alpss")

_DEFAULT_BAND = 1e9


def _probe_filepath(base_filepath, probe, file_input_type):
    """Where this probe's trace lives.

    "single": every probe shares one multi-channel file and is picked out by
    osc_channel. "separate": each channel was exported to its own file, named by
    the probe's pdv_filename and sitting beside the configured filepath.
    """
    if file_input_type == "single":
        return base_filepath
    if file_input_type == "separate":
        dirname = os.path.dirname(base_filepath)
        _, ext = os.path.splitext(base_filepath)
        return os.path.join(dirname, probe["pdv_filename"] + ext)
    raise ValueError(
        f"Unsupported file_input_type {file_input_type!r}, "
        "must be 'single' or 'separate'"
    )


def alpss_multipoint(config):
    """Run alpss_main once per probe in a multi-point PDV configuration.

    Probes are not channels: several probes may be wavelength multiplexed onto
    one oscilloscope channel, reading the same voltage column but separated by
    their frequency band. So the probe list comes from the config's
    "multipoint" section, never from the file.

    Returns one (fig, items) tuple per probe, None where a probe failed, in
    metadata order.
    """
    multipoint = dict(config.get("multipoint") or {})
    base = flatten_config({k: v for k, v in config.items() if k != "multipoint"})

    probes = multipoint.get("metadata") or []
    if not probes:
        # degenerate case: no probe table, so run once on the first channel
        # exactly as a plain single-probe analysis would
        validate_inputs(base)
        logger.info("No multipoint metadata; running as a single probe")
        return [alpss_main(extract_data(base), **base)]

    file_input_type = multipoint.get("file_input_type", "single")
    freq_lower = multipoint.get("freq_lower", _DEFAULT_BAND)
    freq_upper = multipoint.get("freq_upper", _DEFAULT_BAND)
    refine_lower = multipoint.get("freq_refine_lower")
    refine_upper = multipoint.get("freq_refine_upper")

    # one refine bound given means mirror it for the other
    refine = refine_lower is not None or refine_upper is not None
    if refine:
        refine_lower = refine_lower if refine_lower is not None else refine_upper
        refine_upper = refine_upper if refine_upper is not None else refine_lower

    results = []
    probe_numbers = []
    trace_cache = {}

    for probe in probes:
        probe_number = int(probe["probe_number"])
        channel = probe.get("osc_channel")
        upshift = probe["expected_upshift"]
        probe_numbers.append(probe_number)

        inputs = dict(base)
        inputs["filepath"] = _probe_filepath(base["filepath"], probe, file_input_type)
        inputs["lam"] = probe["tar_lam"]
        inputs["multipoint_probe"] = probe_number
        if file_input_type == "single":
            inputs["channel"] = channel
        inputs["freq_min"] = upshift - freq_lower
        inputs["freq_max"] = upshift + freq_upper

        try:
            # probes sharing a channel read the same column, so read it once
            cache_key = (inputs["filepath"], inputs.get("channel"))
            if cache_key not in trace_cache:
                trace_cache[cache_key] = extract_data(dict(inputs))
            data = trace_cache[cache_key]

            if refine:
                cen = prescan_carrier(
                    data,
                    freq_min=inputs["freq_min"],
                    freq_max=inputs["freq_max"],
                    carrier_band_time=inputs["carrier_band_time"],
                )
                inputs["freq_min"] = cen - refine_lower
                inputs["freq_max"] = cen + refine_upper
                logger.info(
                    "Probe %s (channel %s): carrier %.4f GHz, refined band %.4f-%.4f GHz",
                    probe_number, channel, cen / 1e9,
                    inputs["freq_min"] / 1e9, inputs["freq_max"] / 1e9,
                )
            else:
                logger.info(
                    "Probe %s (channel %s): band %.4f-%.4f GHz",
                    probe_number, channel,
                    inputs["freq_min"] / 1e9, inputs["freq_max"] / 1e9,
                )

            validate_inputs(inputs)
            results.append(alpss_main(data, **inputs))

        except Exception as e:
            logger.error("Probe %s failed: %s - skipping.", probe_number, e)
            results.append(None)

    ok = sum(r is not None for r in results)
    logger.info("Multipoint complete: %d of %d probes succeeded", ok, len(results))

    if base.get("save_data"):
        written = combine_probes(
            results, probe_numbers, base["filepath"], base["out_files_dir"]
        )
        logger.info("Wrote %d combined CSVs", len(written))

    return results
