import copy
import os
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from alpss.carrier.frequency import prescan_carrier
from alpss.multipoint.runner import _probe_filepath, alpss_multipoint
from alpss.multipoint.combine import combine_probes

BASE_DIR = os.path.dirname(__file__)


def fake_items(t0, n=50, value=1.0):
    """Minimal stand-in for the items dict alpss_main returns."""
    time = np.linspace(t0, t0 + 1e-7, n)
    series = np.stack((time, np.full(n, value)), axis=1)
    voltage = np.stack((time, np.full(n, value), np.full(n, -value)), axis=1)
    return (
        None,
        {
            "velocity": [series],
            "smooth_velocity": [series],
            "noise": [series],
            "vel_uncert": [series],
            "voltage": [voltage],
            "results": [{"Carrier Frequency": value * 1e9}],
            "inputs": [pd.DataFrame([{"lam": 1.55e-06}])],
        },
    )


class TestPrescanCarrier:
    def test_finds_a_known_tone(self):
        fs = 128e9
        t = np.arange(0, 3e-07, 1 / fs)
        data = np.stack((t, np.sin(2 * np.pi * 4.7e9 * t)), axis=1)
        cen = prescan_carrier(data, freq_min=1e9, freq_max=10e9, carrier_band_time=2.5e-07)
        assert cen == pytest.approx(4.7e9, rel=1e-3)

    def test_narrow_band_picks_the_weaker_tone(self):
        """Several probes share a column; the band decides which one is found."""
        fs = 128e9
        t = np.arange(0, 3e-07, 1 / fs)
        mixed = np.sin(2 * np.pi * 2e9 * t) + 0.3 * np.sin(2 * np.pi * 8e9 * t)
        data = np.stack((t, mixed), axis=1)
        wide = prescan_carrier(data, freq_min=1e9, freq_max=10e9, carrier_band_time=2.5e-07)
        narrow = prescan_carrier(data, freq_min=7e9, freq_max=9e9, carrier_band_time=2.5e-07)
        assert wide == pytest.approx(2e9, rel=1e-3)
        assert narrow == pytest.approx(8e9, rel=1e-3)


class TestProbeFilepath:
    def test_single_shares_one_file(self):
        probe = {"pdv_filename": "ignored"}
        assert _probe_filepath("/d/shot.csv", probe, "single") == "/d/shot.csv"

    def test_separate_uses_the_probes_own_file(self):
        probe = {"pdv_filename": "C2--shot"}
        assert _probe_filepath("/d/shot.csv", probe, "separate") == "/d/C2--shot.csv"

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="file_input_type"):
            _probe_filepath("/d/shot.csv", {}, "sideways")


class TestCombineProbes:
    def test_wide_csvs_one_column_per_probe(self, tmp_path):
        results = [fake_items(0.0, value=1.0), fake_items(0.0, value=2.0)]
        written = combine_probes(results, [10, 6], "shot.csv", str(tmp_path))

        velocity = pd.read_csv(tmp_path / "shot-velocity.csv")
        assert list(velocity.columns) == ["time", "probe_10", "probe_6"]
        assert velocity["probe_10"].iloc[0] == pytest.approx(1.0)
        assert velocity["probe_6"].iloc[0] == pytest.approx(2.0)
        assert any(p.endswith("-voltage.csv") for p in written)

    def test_results_are_one_row_per_probe(self, tmp_path):
        results = [fake_items(0.0, value=1.0), fake_items(0.0, value=2.0)]
        combine_probes(results, [10, 6], "shot.csv", str(tmp_path))

        res = pd.read_csv(tmp_path / "shot-results.csv")
        assert list(res["probe_number"]) == [10, 6]
        assert list(res["Carrier Frequency"]) == [1e9, 2e9]

    def test_failed_probes_are_skipped(self, tmp_path):
        results = [fake_items(0.0, value=1.0), None, fake_items(0.0, value=3.0)]
        combine_probes(results, [10, 6, 19], "shot.csv", str(tmp_path))

        velocity = pd.read_csv(tmp_path / "shot-velocity.csv")
        assert list(velocity.columns) == ["time", "probe_10", "probe_19"]

    def test_offset_probe_is_interpolated_onto_the_reference_axis(self, tmp_path):
        """Probes are clipped to their own DOI, so they need a shared axis."""
        results = [fake_items(0.0, value=1.0), fake_items(5e-8, value=2.0)]
        combine_probes(results, [10, 6], "shot.csv", str(tmp_path))

        velocity = pd.read_csv(tmp_path / "shot-velocity.csv")
        # the second probe starts later, so the head of its column is NaN
        assert np.isnan(velocity["probe_6"].iloc[0])
        assert velocity["probe_6"].notna().any()
        assert velocity["probe_10"].notna().all()


class TestMultipointLoop:
    def _config(self, valid_inputs, probes, **multipoint):
        config = copy.deepcopy(valid_inputs)
        config["io"]["save_data"] = False
        config["io"]["display_plots"] = False
        config["multipoint"] = {"metadata": probes, **multipoint}
        return config

    def test_no_metadata_runs_as_a_single_probe(self, valid_inputs):
        config = copy.deepcopy(valid_inputs)
        config["io"]["save_data"] = False
        config["io"]["display_plots"] = False

        results = alpss_multipoint(config)
        assert len(results) == 1
        assert results[0] is not None

    def test_probes_sharing_a_channel_read_the_trace_once(self, valid_inputs):
        probes = [
            {"osc_channel": 2, "probe_number": 6, "tar_lam": 1.55e-06, "expected_upshift": 2.2e9},
            {"osc_channel": 2, "probe_number": 9, "tar_lam": 1.54e-06, "expected_upshift": 2.2e9},
        ]
        config = self._config(valid_inputs, probes)

        with patch("alpss.multipoint.runner.extract_data") as mock_extract, \
             patch("alpss.multipoint.runner.alpss_main") as mock_main:
            mock_extract.return_value = np.zeros((10, 2))
            mock_main.return_value = fake_items(0.0)
            alpss_multipoint(config)

        assert mock_extract.call_count == 1, "same channel should be read once"
        assert mock_main.call_count == 2, "but analysed once per probe"

    def test_each_probe_gets_its_own_wavelength_and_band(self, valid_inputs):
        probes = [
            {"osc_channel": 1, "probe_number": 10, "tar_lam": 1.550e-06, "expected_upshift": 2e9},
            {"osc_channel": 2, "probe_number": 6, "tar_lam": 1.531e-06, "expected_upshift": 8e9},
        ]
        config = self._config(valid_inputs, probes, freq_lower=1e9, freq_upper=1e9)

        with patch("alpss.multipoint.runner.extract_data") as mock_extract, \
             patch("alpss.multipoint.runner.alpss_main") as mock_main:
            mock_extract.return_value = np.zeros((10, 2))
            mock_main.return_value = fake_items(0.0)
            alpss_multipoint(config)

        first, second = [c.kwargs for c in mock_main.call_args_list]
        assert first["lam"] == 1.550e-06
        assert (first["freq_min"], first["freq_max"]) == (1e9, 3e9)
        assert second["lam"] == 1.531e-06
        assert (second["freq_min"], second["freq_max"]) == (7e9, 9e9)
        assert first["multipoint_probe"] == 10
        assert second["multipoint_probe"] == 6

    def test_a_failing_probe_does_not_stop_the_others(self, valid_inputs):
        probes = [
            {"osc_channel": 1, "probe_number": 10, "tar_lam": 1.55e-06, "expected_upshift": 2.2e9},
            {"osc_channel": 2, "probe_number": 6, "tar_lam": 1.55e-06, "expected_upshift": 2.2e9},
        ]
        config = self._config(valid_inputs, probes)

        with patch("alpss.multipoint.runner.extract_data") as mock_extract, \
             patch("alpss.multipoint.runner.alpss_main") as mock_main:
            mock_extract.return_value = np.zeros((10, 2))
            mock_main.side_effect = [RuntimeError("probe 10 blew up"), fake_items(0.0)]
            results = alpss_multipoint(config)

        assert results[0] is None
        assert results[1] is not None
