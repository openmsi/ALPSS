import os

import numpy as np
import pytest

from alpss.io.reading import (
    channel_columns,
    extract_data,
    sniff_header,
)

BASE_DIR = os.path.dirname(__file__)
LEGACY_FILE = os.path.join(BASE_DIR, "input_data", "example_file.csv")
MULTICHANNEL_FILE = os.path.join(BASE_DIR, "input_data", "multichannel_example.csv")

# Carrier frequencies present in each channel of the multi-channel fixture,
# measured from the raw file. They are far enough apart to identify which
# column the reader actually returned.
CHANNEL_CARRIERS_GHZ = {1: 1.848, 2: 8.232, 3: 4.712}


def read_inputs(filepath, **overrides):
    inputs = {
        "filepath": filepath,
        "sample_rate": 128e9,
        "time_to_skip": 0.0,
        "time_to_take": 2e-07,
    }
    inputs.update(overrides)
    return inputs


def carrier_ghz(data):
    """Dominant frequency of the voltage column, in GHz."""
    time = data.iloc[:, 0].to_numpy()
    voltage = data.iloc[:, 1].to_numpy()
    fs = 1 / np.mean(np.diff(time))
    freq = np.fft.fftfreq(len(voltage), 1 / fs)
    half = len(voltage) // 2
    ampl = np.abs(np.fft.fft(voltage))[:half]
    return freq[:half][np.argmax(ampl[1:]) + 1] / 1e9


class TestSniffHeader:
    def test_legacy_two_column_file(self):
        data_start, labels, n_cols = sniff_header(read_inputs(LEGACY_FILE))
        assert data_start == 1
        assert labels == ["Time", "Voltage"]
        assert n_cols == 2

    def test_multichannel_file(self):
        data_start, labels, n_cols = sniff_header(read_inputs(MULTICHANNEL_FILE))
        assert data_start == 24
        assert labels == ["Time Tags (Channel 1)", "Channel 1", "Channel 2", "Channel 3"]
        assert n_cols == 4

    def test_bytestring_matches_filepath(self):
        with open(MULTICHANNEL_FILE, "rb") as f:
            raw = f.read()
        from_file = sniff_header(read_inputs(MULTICHANNEL_FILE))
        from_bytes = sniff_header(read_inputs(MULTICHANNEL_FILE, bytestring=raw))
        assert from_file == from_bytes

    def test_raises_when_no_numeric_data(self, tmp_path):
        path = tmp_path / "no_data.csv"
        path.write_text("header only\nstill no numbers\n")
        with pytest.raises(ValueError, match="Could not locate numeric data"):
            sniff_header(read_inputs(str(path)))


class TestChannelColumns:
    def test_labelled_channels_map_to_their_column(self):
        labels = ["Time Tags (Channel 1)", "Channel 1", "Channel 2", "Channel 3"]
        assert channel_columns(labels, 4) == {1: 1, 2: 2, 3: 3}

    def test_channel_number_need_not_match_position(self):
        # a scope may export channels 2, 3, 4 into columns 1, 2, 3
        labels = ["Time Tags (Channel 2)", "Channel 2", "Channel 3", "Channel 4"]
        assert channel_columns(labels, 4) == {2: 1, 3: 2, 4: 3}

    def test_unlabelled_file_gets_one_implicit_channel(self):
        assert channel_columns(["Time", "Voltage"], 2) == {1: 1}
        assert channel_columns(["Time", "Ampl"], 2) == {1: 1}

    def test_no_labels_at_all(self):
        assert channel_columns(None, 3) == {1: 1, 2: 2}


class TestExtractData:
    def test_legacy_file(self):
        data = extract_data(read_inputs(LEGACY_FILE, sample_rate=80e9))
        assert data.shape[1] == 2
        # the row count covers time_to_take (exact count depends on how the
        # float division truncates)
        assert len(data) == pytest.approx(2e-07 * 80e9, abs=1)

    def test_no_sample_is_dropped(self):
        """The first data row of the file must survive into the result."""
        with open(LEGACY_FILE) as f:
            f.readline()  # label row
            first = float(f.readline().split(",")[0])
        data = extract_data(read_inputs(LEGACY_FILE, sample_rate=80e9))
        assert data.iloc[0, 0] == pytest.approx(first, rel=1e-12)

    def test_multichannel_defaults_to_first_channel(self):
        data = extract_data(read_inputs(MULTICHANNEL_FILE))
        assert data.shape[1] == 2
        assert carrier_ghz(data) == pytest.approx(CHANNEL_CARRIERS_GHZ[1], abs=0.05)

    @pytest.mark.parametrize("channel", [1, 2, 3])
    def test_channel_selection(self, channel):
        data = extract_data(read_inputs(MULTICHANNEL_FILE, channel=channel))
        assert data.shape[1] == 2
        assert carrier_ghz(data) == pytest.approx(
            CHANNEL_CARRIERS_GHZ[channel], abs=0.05
        )

    def test_unknown_channel_raises(self):
        with pytest.raises(ValueError, match="Channel 9 not found"):
            extract_data(read_inputs(MULTICHANNEL_FILE, channel=9))

    def test_bytestring_matches_filepath(self):
        with open(MULTICHANNEL_FILE, "rb") as f:
            raw = f.read()
        from_file = extract_data(read_inputs(MULTICHANNEL_FILE, channel=2))
        from_bytes = extract_data(
            read_inputs(MULTICHANNEL_FILE, channel=2, bytestring=raw)
        )
        np.testing.assert_array_equal(from_file.to_numpy(), from_bytes.to_numpy())

    def test_header_lines_is_ignored(self):
        """Existing configs carry a hand-tuned header_lines that is usually
        wrong; the auto-detected data start wins."""
        correct = extract_data(read_inputs(MULTICHANNEL_FILE))
        stale = extract_data(read_inputs(MULTICHANNEL_FILE, header_lines=22))
        np.testing.assert_array_equal(correct.to_numpy(), stale.to_numpy())

    def test_time_to_skip_offsets_from_the_data_start(self):
        skip = 1e-08
        full = extract_data(read_inputs(MULTICHANNEL_FILE))
        skipped = extract_data(read_inputs(MULTICHANNEL_FILE, time_to_skip=skip))
        offset = int(skip * 128e9)
        np.testing.assert_array_equal(
            full.to_numpy()[offset : offset + 10], skipped.to_numpy()[:10]
        )

    def test_preloaded_data_passes_through(self):
        data = extract_data(read_inputs(LEGACY_FILE, sample_rate=80e9))
        assert extract_data({"_data": data}) is data
