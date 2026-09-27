BASE_CORE = {
    "capacity_kwh": 39.2,
    "efficiency": None,
    "max_charge_kw": None,
    "max_discharge_kw": None,
    "minimum_soc": None,
    "maximum_soc": None,
}

class BatterySOC:
    """
    Battery State of Charge model.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.soc_kwh = config["capacity_kwh"]
    
    def charge(self, power_kw: float, duration_hours: float):
        """Charge the battery."""
        pass
    
    def discharge(self, power_kw: float, duration_hours: float):
        """Discharge the battery."""
        pass
