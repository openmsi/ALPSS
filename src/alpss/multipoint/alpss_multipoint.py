import logging
from alpss.alpss_main import alpss_main
from alpss.multipoint.freq_refinement import find_carrier
from alpss.multipoint.extract_multipoint_data import extract_multipoint_data
from alpss.multipoint.multipoint_saving import save_combined_series

logger = logging.getLogger("alpss")

_C = 3e8  # speed of light (m/s)


def alpss_multipoint(
    channels,
    filepath,
    freq_lower=1e9,
    freq_upper=1e9,
    freq_refine_lower=None,
    freq_refine_upper=None,
    **kwargs,
):
    """Run alpss_main over every probe in a multi-point PDV channel configuration.

    Parameters
    ----------
    channels : dict[str, pd.DataFrame]
        Keys are channel names (e.g. ``"ch1"``); values are DataFrames with
        columns ``tar_lam`` (nm), ``ref_lam`` (nm), and ``probe_number``.
    filepath : str
        Path to the input CSV file containing all probe channels. Column 0 is
        time; columns 1, 2, 3, … are probe voltages in the order probes are
        listed across all channels.
    freq_lower : float
        How far below the beat frequency to set ``freq_min`` (Hz). Default 1 GHz.
    freq_upper : float
        How far above the beat frequency to set ``freq_max`` (Hz). Default 1 GHz.
    freq_refine_lower : float or None
        If set, carrier centre frequency refinement is performed. find_carrier()
        is called first using the wide ``freq_lower``/``freq_upper`` bounds to
        locate the carrier, then alpss_main runs with tight bounds centred on
        that carrier: ``freq_min = cen - freq_refine_lower``. Default None
        (no refinement; wide bounds are used directly).
    freq_refine_upper : float or None
        Upper half-width for the refined bounds (Hz): ``freq_max = cen + freq_refine_upper``.
        If only one of the two refine params is provided, the other mirrors it.
    **kwargs
        All other keyword arguments are forwarded to :func:`alpss_main`.
        ``filepath``, ``_data``, ``multipoint_probe``, ``lam``, ``freq_min``, and
        ``freq_max`` are set automatically and should **not** be passed here.

    Returns
    -------
    list[tuple]
        One ``(fig, items)`` tuple per probe (or ``None`` on failure),
        in channel-then-probe order.
    """
    reserved = {"filepath", "_data", "multipoint_probe", "lam", "freq_min", "freq_max"}
    conflicts = reserved & kwargs.keys()
    if conflicts:
        raise ValueError(
            f"The following kwargs are set automatically by alpss_multipoint "
            f"and must not be passed manually: {conflicts}"
        )

    # Read the full multi-column file once; each probe gets a 2-column slice
    raw = extract_data({**kwargs, "filepath": filepath})

    # If only one refine bound is given, mirror it for the other
    refine = freq_refine_lower is not None or freq_refine_upper is not None
    if refine:
        if freq_refine_lower is None:
            freq_refine_lower = freq_refine_upper
        if freq_refine_upper is None:
            freq_refine_upper = freq_refine_lower

    results = []
    probe_numbers = []
    voltage_idx = 1
    for channel_name, channel_df in channels.items():
        for _, row in channel_df.iterrows():
            tar_lam_nm = row["tar_lam"]
            ref_lam_nm = row["ref_lam"]
            probe_number = int(row["probe_number"])

            # Beat frequency between target and reference wavelengths
            upshift = _C / (tar_lam_nm * 1e-9) - _C / (ref_lam_nm * 1e-9)

            # 2-column DataFrame slice [time, voltage] for this probe
            probe_data = raw.iloc[:, [0, voltage_idx]].copy()

            logger.info(
                "Channel %s | probe %s | upshift=%.4f GHz",
                channel_name,
                probe_number,
                upshift / 1e9,
            )

            try:
                common = dict(
                    _data=probe_data,
                    filepath=filepath,
                    multipoint_probe=probe_number,
                    lam=ref_lam_nm * 1e-9,
                )

                if refine:
                    logger.info(
                        "Channel %s | probe %s | finding carrier (wide bounds)",
                        channel_name,
                        probe_number,
                    )
                    cen = find_carrier(
                        data=probe_data.values,
                        filepath=filepath,
                        freq_min=upshift - freq_lower,
                        freq_max=upshift + freq_upper,
                        **{k: v for k, v in kwargs.items()
                           if k in ("sample_rate", "time_to_skip", "carrier_band_time",
                                    "header_lines")},
                    )
                    logger.info(
                        "Channel %s | probe %s | carrier found: %.4f GHz — running with refined bounds",
                        channel_name,
                        probe_number,
                        cen / 1e9,
                    )

                    result = alpss_main(
                        **common,
                        freq_min=cen - freq_refine_lower,
                        freq_max=cen + freq_refine_upper,
                        **kwargs,
                    )
                else:
                    result = alpss_main(
                        **common,
                        freq_min=upshift - freq_lower,
                        freq_max=upshift + freq_upper,
                        **kwargs,
                    )

                results.append(result)

            except Exception as e:
                logger.error(
                    "Channel %s | probe %s failed: %s — skipping.",
                    channel_name,
                    probe_number,
                    e,
                )
                results.append(None)

            probe_numbers.append(probe_number)

        voltage_idx += 1

    if kwargs.get("save_data"):
        save_combined_series(results, probe_numbers, filepath, kwargs["out_files_dir"])

    return results
