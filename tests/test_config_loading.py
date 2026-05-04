import json
import os
import pytest
from alpss.utils.config import flatten_config as _flatten_config
from alpss.commands import load_json_config


# --- _flatten_config ---

def test_flatten_merges_sections():
    config = {
        "io": {"filepath": "a.csv", "save_data": True},
        "material": {"density": 8960, "C0": 3950},
    }
    flat = _flatten_config(config)
    assert flat["filepath"] == "a.csv"
    assert flat["density"] == 8960
    assert flat["C0"] == 3950


def test_flatten_raises_on_flat_config():
    with pytest.raises(ValueError, match="nested sections"):
        _flatten_config({"filepath": "a.csv", "density": 8960})


def test_flatten_raises_on_unknown_section():
    with pytest.raises(ValueError, match="Unknown config sections"):
        _flatten_config({"io": {"filepath": "a.csv"}, "typo_section": {"x": 1}})


def test_flatten_raises_on_key_collision():
    with pytest.raises(ValueError, match="collision"):
        _flatten_config({
            "io": {"density": 1.0},
            "material": {"density": 8960},
        })


def test_flatten_single_section():
    flat = _flatten_config({"io": {"filepath": "a.csv"}})
    assert flat == {"filepath": "a.csv"}


def test_flatten_all_valid_sections():
    config = {s: {"key_" + s: 1} for s in [
        "io", "stft", "start_time", "carrier", "velocity",
        "material", "spall", "hel", "uncertainty", "plotting",
    ]}
    flat = _flatten_config(config)
    assert len(flat) == 10
    assert "key_io" in flat
    assert "key_plotting" in flat


# --- load_json_config ---

def test_load_json_config_returns_dict_unchanged():
    d = {"io": {"filepath": "a.csv"}, "material": {"density": 8960}}
    result = load_json_config(d)
    assert result is d


def test_load_json_config_from_file(tmp_path):
    config = {"io": {"filepath": "a.csv"}, "material": {"density": 8960}}
    f = tmp_path / "config.json"
    f.write_text(json.dumps(config))
    result = load_json_config(str(f))
    assert result["io"]["filepath"] == "a.csv"
    assert result["material"]["density"] == 8960


def test_load_json_config_invalid_path_raises():
    with pytest.raises(ValueError, match="Invalid config input"):
        load_json_config("/nonexistent/path/config.json")


def test_load_json_config_flat_file_loads_without_error(tmp_path):
    """load_json_config is a loader — validation happens downstream in flatten_config."""
    config = {"filepath": "a.csv", "density": 8960}
    f = tmp_path / "config.json"
    f.write_text(json.dumps(config))
    result = load_json_config(str(f))
    assert result == config
