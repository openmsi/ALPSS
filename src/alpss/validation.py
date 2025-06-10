def validate_inputs(inputs):
    if inputs["t_after"] > inputs["time_to_take"]:
        raise ValueError("'t_after' must be less than 'time_to_take'. ")