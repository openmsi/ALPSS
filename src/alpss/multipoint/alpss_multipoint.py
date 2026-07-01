import logging
import pandas as pd
from alpss.alpss_main import alpss_main
from alpss.multipoint.freq_refinement import find_carrier
from alpss.multipoint.extract_multipoint_data import extract_multipoint_data
from alpss.multipoint.multipoint_saving import save_combined_series
from alpss.utils.config import flatten_config

logger = logging.getLogger("alpss")

# kwargs alpss_multipoint consumes itself and must not forward to alpss_main
_MULTIPOINT_ONLY_KEYS = {
    "multipoint", "metadata", "file_input_type",
    "freq_lower", "freq_upper", "freq_refine_lower", "freq_refine_upper",
}
# alpss_main kwargs alpss_multipoint sets per-probe and must not forward from config
_RESERVED_KEYS = {"filepath", "_data", "multipoint_probe", "lam", "freq_min", "freq_max"}


def alpss_multipoint(inputs):
    """Run alpss_main over every probe in a multi-point PDV channel configuration.

    Parameters
    ----------
    inputs : dict
        Nested section-based config (same shape as the JSON config file).
        The "io" section must include "filepath"; the "multipoint" section
        must include "metadata" (a list of per-probe records with at least
        "osc_channel", "probe_number", "tar_lam", and "expected_upshift" —
        see extract_multipoint_data for the columns each file_input_type
        needs) and may include "file_input_type" (default "single"),
        "freq_lower"/"freq_upper" (Hz half-widths around the expected
        upshift, default 1 GHz), and "freq_refine_lower"/"freq_refine_upper"
        to enable carrier refinement (find_carrier() locates the carrier
        using the wide bounds first, then alpss_main runs with tight bounds
        centred on it; if only one refine bound is given, the other mirrors
        it). All other flattened config values are forwarded to alpss_main.

    Returns
    -------
    list[tuple]
        One ``(fig, items)`` tuple per probe (or ``None`` on failure), in
        metadata row order.
    """
    flat = flatten_config(inputs)

    multipoint_metadata = pd.DataFrame(inputs["multipoint"]["metadata"])
    file_input_type = inputs["multipoint"].get("file_input_type", "single")
    freq_lower = inputs["multipoint"].get("freq_lower", 1e9)
    freq_upper = inputs["multipoint"].get("freq_upper", 1e9)
    freq_refine_lower = inputs["multipoint"].get("freq_refine_lower")
    freq_refine_upper = inputs["multipoint"].get("freq_refine_upper")
    filepath = flat["filepath"]

    # If only one refine bound is given, mirror it for the other
    refine = freq_refine_lower is not None or freq_refine_upper is not None
    if refine:
        if freq_refine_lower is None:
            freq_refine_lower = freq_refine_upper
        if freq_refine_upper is None:
            freq_refine_upper = freq_refine_lower

    main_kwargs = {
        k: v for k, v in flat.items()
        if k not in _MULTIPOINT_ONLY_KEYS and k not in _RESERVED_KEYS
    }

    results = []
    probe_numbers = []
    for probe_index in range(len(multipoint_metadata)):
        row = multipoint_metadata.iloc[probe_index]
        tar_lam = row["tar_lam"]
        upshift = row["expected_upshift"]
        probe_number = int(row["probe_number"])
        osc_channel = row["osc_channel"]

        probe_data = extract_multipoint_data(
            flat,
            multipoint_metadata=multipoint_metadata,
            file_input_type=file_input_type,
            probe_index=probe_index,
        )

        logger.info(
            "Channel %s | probe %s | upshift=%.4f GHz",
            osc_channel,
            probe_number,
            upshift / 1e9,
        )

        try:
            common = dict(
                _data=probe_data,
                filepath=filepath,
                multipoint_probe=probe_number,
                lam=tar_lam,
            )

            if refine:
                logger.info(
                    "Channel %s | probe %s | finding carrier (wide bounds)",
                    osc_channel,
                    probe_number,
                )
                cen = find_carrier(
                    data=probe_data.values,
                    filepath=filepath,
                    freq_min=upshift - freq_lower,
                    freq_max=upshift + freq_upper,
                    **{k: v for k, v in flat.items()
                       if k in ("sample_rate", "time_to_skip", "carrier_band_time",
                                "header_lines")},
                )
                logger.info(
                    "Channel %s | probe %s | carrier found: %.4f GHz — running with refined bounds",
                    osc_channel,
                    probe_number,
                    cen / 1e9,
                )

                result = alpss_main(
                    **common,
                    freq_min=cen - freq_refine_lower,
                    freq_max=cen + freq_refine_upper,
                    **main_kwargs,
                )
            else:
                result = alpss_main(
                    **common,
                    freq_min=upshift - freq_lower,
                    freq_max=upshift + freq_upper,
                    **main_kwargs,
                )

            results.append(result)

        except Exception as e:
            logger.error(
                "Channel %s | probe %s failed: %s — skipping.",
                osc_channel,
                probe_number,
                e,
            )
            results.append(None)

        probe_numbers.append(probe_number)

    if flat.get("save_data"):
        save_combined_series(results, probe_numbers, filepath, flat["out_files_dir"])

    return results
