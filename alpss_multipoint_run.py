import json
from alpss.commands import alpss_multipoint_with_config, alpss_main_with_config

with open("tests/input_data/multipoint/multipoint_config.json") as f:
    config = json.load(f)


alpss_multipoint_with_config(config)