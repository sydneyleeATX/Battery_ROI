def get_temperature_derating(
    temperature_f: float
) -> float:
    """
    Determine the battery/inverter power derating factor
    based on ambient temperature.

    Parameters
    ----------
    temperature_f : float
        Ambient temperature in degrees Fahrenheit.

    Returns
    -------
    float
        Derating factor between 0 and 1.
    """

    if temperature_f <= 104:
        return 1.0

    elif temperature_f <= 122:
        return 1.0 - (0.05 / 1.8) * (temperature_f - 104)

    else:
        return 0.0