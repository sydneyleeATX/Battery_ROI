class Battery:
    def __init__(
        self,
        capacity_kwh=39.2,
        nominal_power_kw=11,
        efficiency=0.90,
        minimum_soc=0.20,
        maximum_soc=1.00,
        initial_soc_kwh=39.2 * 0.5,
    ):
        self.capacity_kwh = capacity_kwh
        self.nominal_power_kw = nominal_power_kw
        self.efficiency = efficiency

        self.minimum_soc_kwh = capacity_kwh * minimum_soc
        self.maximum_soc_kwh = capacity_kwh * maximum_soc

        self.soc_kwh = initial_soc_kwh

    def get_economic_soc_limit(self):
        """
        Return the minimum battery SOC allowed for economic dispatch.
        The battery's minimum SOC is reserved for homeowner backup.
        This can be made more complex later if we dynamically determine min SOC based on weather / grid reliability / etc
        """
        return self.minimum_soc_kwh

    
    def get_home_service_limit(
        self,
        service_amps,
        service_voltage=240
    ):
        """
        Convert the home's electrical service rating
        from amps to approximate kW.
        Realistic input amp range: 100-400 amps
        """
        return service_amps * service_voltage / 1000


    def get_available_discharge_kwh(self) -> float:
        """
        Return the amount of energy that can be discharged
        without falling below the minimum SOC.
        
        Accounts for efficiency losses: when discharging X kWh,
        the battery loses X/efficiency kWh from its SOC.
        """
        available_soc_kwh = self.soc_kwh - self.minimum_soc_kwh
        # Account for efficiency: discharging uses more SOC than delivered energy
        return available_soc_kwh * self.efficiency


    def get_available_charge_kwh(self) -> float:
        """
        Return the amount of energy that can be charged
        without exceeding the maximum SOC.
        """
        return self.maximum_soc_kwh - self.soc_kwh
    

    def update_soc(
        self,
        energy_charged_kwh: float,
        energy_discharged_kwh: float,
        charge_efficiency: float,
    ) -> None:
        """
        Update the battery's state of charge after a charging
        or discharging action.

        Parameters
        ----------
        energy_charged_kwh : float
            Energy supplied to the battery during charging, in kWh.

        energy_discharged_kwh : float
            Energy delivered by the battery during discharging, in kWh.

        charge_efficiency : float
            Fraction of charging energy that is stored in the battery.
            Also used as the efficiency for discharging (round-trip efficiency).

        Returns
        -------
        None
            Updates self.soc_kwh in place.
        """

        if energy_charged_kwh < 0:
            raise ValueError("energy_charged_kwh cannot be negative.")

        if energy_discharged_kwh < 0:
            raise ValueError("energy_discharged_kwh cannot be negative.")

        if not 0 < charge_efficiency <= 1:
            raise ValueError("charge_efficiency must be between 0 and 1.")

        energy_stored_kwh = (
            energy_charged_kwh * charge_efficiency
        )

        energy_removed_kwh = (
            energy_discharged_kwh / charge_efficiency
        )

        self.soc_kwh += (
            energy_stored_kwh
            - energy_removed_kwh
        )

    
    def get_effective_discharge_power_kw(
        self,
        temperature_derating: float,
    ) -> float:
        """
        Return the maximum battery discharge power currently available,
        after applying temperature derating.

        Parameters
        ----------
        temperature_derating : float
            Derating factor between 0 and 1 produced by temp_derating().

        Returns
        -------
        float
            Effective maximum discharge power in kW.
        """

        if not 0 < temperature_derating <= 1:
            raise ValueError(
                "temperature_derating must be between 0 and 1."
            )

        return self.nominal_power_kw * temperature_derating


    def get_effective_charge_power_kw(
        self,
        temperature_derating: float,
        service_limit_amps: float,
        household_load_kw: float,
        voltage: float = 240.0, 
    ) -> float:
        """
        Return the maximum battery charging power currently available,
        considering battery power, temperature, and home electrical capacity.

        Returns:
            Maximum charging power in kW.
        """

        if service_limit_amps <= 0:
            raise ValueError(
                "service_limit_amps must be greater than 0."
            )

        if household_load_kw < 0:
            raise ValueError(
                "household_load_kw cannot be negative."
            )

        if voltage <= 0:
            raise ValueError(
                "voltage must be greater than 0."
            )

        # Battery charging power after temperature derating
        # Reuse existing function
        temperature_limited_power_kw = self.get_effective_discharge_power_kw(
            temperature_derating
        )

        # Convert home service rating from amps to kW
        # Reuse existing function
        home_service_capacity_kw = self.get_home_service_limit(
            service_amps=service_limit_amps,
            service_voltage=voltage
        )

        # Remaining home electrical capacity available for charging
        available_home_power_kw = (
            home_service_capacity_kw - household_load_kw
        )

        # Battery cannot charge at a negative power
        available_home_power_kw = max(
            0.0,
            available_home_power_kw
        )

        # The most restrictive power limit determines
        # the maximum charging power.
        return min(
            temperature_limited_power_kw,
            available_home_power_kw,
        )



    def get_effective_battery_power(
        self,
        temperature_derating: float,
        service_limit_amps: float,
        household_load_kw: float,
        inverter_limit_kw: float,
        voltage: float = 240.0,
    ) -> dict:
        """
        Return the maximum battery charge and discharge power
        available under current physical constraints.

        Returns:
            {
                "max_charge_kw": float,
                "max_discharge_kw": float
            }
        """

        # Get base charge power using existing function
        base_charge_kw = self.get_effective_charge_power_kw(
            temperature_derating=temperature_derating,
            service_limit_amps=service_limit_amps,
            household_load_kw=household_load_kw,
            voltage=voltage
        )

        # Get base discharge power using existing function
        base_discharge_kw = self.get_effective_discharge_power_kw(
            temperature_derating=temperature_derating
        )

        # Apply inverter limit to charge power
        max_charge_kw = min(
            base_charge_kw,
            inverter_limit_kw,
        )

        # Apply inverter limit to discharge power
        max_discharge_kw = min(
            base_discharge_kw,
            inverter_limit_kw,
        )

        return {
            "max_charge_kw": max_charge_kw,
            "max_discharge_kw": max_discharge_kw,
        }
    
    def get_battery_status(self):
        """
        Return the current battery status.
        """
        return {
            "soc_kwh": self.soc_kwh,
            "minimum_soc_kwh": self.minimum_soc_kwh,
            "maximum_soc_kwh": self.maximum_soc_kwh,
        }
    
    def should_charge(
        self,
        price_kwh: float,
        time,
        price_thresholds: dict,
    ) -> bool:
        """
        Determine whether the battery should charge under the current
        economic conditions.

        The applicable low-price threshold is selected based on the
        current month.
        """

        month = time.month
        low_price_threshold = price_thresholds[month]["charge"]

        return (
            price_kwh <= low_price_threshold
            and self.soc_kwh < self.maximum_soc_kwh
        )


    def should_discharge(
        self,
        price_kwh: float,
        time,
        price_thresholds: dict,
    ) -> bool:
        """
        Determine whether the battery should discharge under the current
        economic conditions.
        May need to investigate if time scaling is processed correctly
        The applicable high-price threshold is selected based on the
        current month.

        Parameters
        ----------
        price_kwh : float
            Current electricity price in $/kWh.

        time : datetime
            Current simulation timestamp.

        price_thresholds : dict
            Monthly price thresholds calculated from historical ERCOT data.

        Returns
        -------
        bool
            True if discharging is economically appropriate.
        """

        month = time.month
        high_price_threshold = price_thresholds[month]["discharge"]

        return (
            price_kwh >= high_price_threshold
            and self.soc_kwh > self.get_economic_soc_limit()
        )


    @staticmethod
    def dispatch_battery(
        battery,
        home_load_kw: float,
        price_kwh: float,
        price_thresholds: dict,
        timestamp,
        temperature_derating: float,
        service_limit_amps: float,
        inverter_limit_kw: float,
        voltage: float = 240.0,
    ) -> dict:
        """
        Determine the battery dispatch for the current simulation interval.

        Combines the economic decision with the battery's physical constraints
        and available SOC energy.

        Parameters
        ----------
        battery : Battery
            Battery being dispatched.

        home_load_kw : float
            Current household electricity load in kW.

        price_kwh : float
            Current electricity price in $/kWh.

        price_thresholds : dict
            Monthly price thresholds calculated from historical ERCOT data.

        timestamp : datetime
            Current simulation timestamp. Used to select the appropriate
            monthly price thresholds.

        temperature_derating : float
            Battery power derating factor due to temperature.

        service_limit_amps : float
            Home electrical service limit in amps.

        inverter_limit_kw : float
            Maximum inverter power in kW.

        voltage : float, default=240.0
            Household service voltage.

        Returns
        -------
        dict
            Dispatch result containing the action, power, energy, SOC before
            and after dispatch, and information about the economic decision.
        """

        INTERVAL_HOURS = 0.25

        # --------------------------------------------------
        # Get monthly price thresholds
        # --------------------------------------------------

        month = timestamp.month

        low_price_threshold = price_thresholds[month]["charge"]
        high_price_threshold = price_thresholds[month]["discharge"]

        # --------------------------------------------------
        # Get battery's physical constraints
        # --------------------------------------------------

        battery_power = battery.get_effective_battery_power(
            temperature_derating=temperature_derating,
            service_limit_amps=service_limit_amps,
            household_load_kw=home_load_kw,
            inverter_limit_kw=inverter_limit_kw,
            voltage=voltage,
        )

        max_charge_kw = battery_power["max_charge_kw"]
        max_discharge_kw = battery_power["max_discharge_kw"]

        available_charge_kwh = battery.get_available_charge_kwh()
        available_discharge_kwh = battery.get_available_discharge_kwh()

        # --------------------------------------------------
        # Store SOC before dispatch
        # --------------------------------------------------

        soc_before_kwh = battery.soc_kwh

        # --------------------------------------------------
        # Determine economic decision
        # --------------------------------------------------

        should_charge = battery.should_charge(
            price_kwh=price_kwh,
            time=timestamp,
            price_thresholds=price_thresholds,
        )

        should_discharge = battery.should_discharge(
            price_kwh=price_kwh,
            time=timestamp,
            price_thresholds=price_thresholds,
        )

        # --------------------------------------------------
        # CHARGE
        # --------------------------------------------------

        if should_charge:

            max_charge_energy_kwh = (
                max_charge_kw * INTERVAL_HOURS
            )

            energy_kwh = min(
                max_charge_energy_kwh,
                available_charge_kwh,
            )

            power_kw = energy_kwh / INTERVAL_HOURS

            battery.update_soc(
                energy_charged_kwh=energy_kwh,
                energy_discharged_kwh=0.0,
                charge_efficiency=battery.efficiency,
            )

            action = "charge"

        # --------------------------------------------------
        # DISCHARGE
        # --------------------------------------------------

        elif should_discharge:

            max_discharge_energy_kwh = (
                max_discharge_kw * INTERVAL_HOURS
            )

            energy_kwh = min(
                max_discharge_energy_kwh,
                available_discharge_kwh,
            )

            power_kw = energy_kwh / INTERVAL_HOURS

            battery.update_soc(
                energy_charged_kwh=0.0,
                energy_discharged_kwh=energy_kwh,
                charge_efficiency=battery.efficiency,
            )

            action = "discharge"

        # --------------------------------------------------
        # IDLE
        # --------------------------------------------------

        else:

            action = "idle"
            power_kw = 0.0
            energy_kwh = 0.0

        # --------------------------------------------------
        # Store SOC after dispatch
        # --------------------------------------------------

        soc_after_kwh = battery.soc_kwh

        # --------------------------------------------------
        # Return dispatch result
        # --------------------------------------------------

        return {
            "action": action,
            "power_kw": power_kw,
            "energy_kwh": energy_kwh,
            "soc_before_kwh": soc_before_kwh,
            "soc_after_kwh": soc_after_kwh,
            "price_kwh": price_kwh,
            "low_price_threshold": low_price_threshold,
            "high_price_threshold": high_price_threshold,
            "max_charge_kw": max_charge_kw,
            "max_discharge_kw": max_discharge_kw,
            "available_charge_kwh": available_charge_kwh,
            "available_discharge_kwh": available_discharge_kwh,
            "timestamp": timestamp,
        }
if __name__ == "__main__":
    # Test Battery class functionality
    print("Testing Battery class...")
    print("=" * 60)
    
    # Initialize battery with default Base Core specs
    battery = Battery()
    
    print(f"\nInitial Battery State:")
    print(f"  Capacity: {battery.capacity_kwh} kWh")
    print(f"  Nominal Power: {battery.nominal_power_kw} kW")
    print(f"  Current SOC: {battery.soc_kwh:.2f} kWh ({battery.soc_kwh/battery.capacity_kwh*100:.1f}%)")
    print(f"  Min SOC: {battery.minimum_soc_kwh:.2f} kWh")
    print(f"  Max SOC: {battery.maximum_soc_kwh:.2f} kWh")
    
    # Test available discharge/charge
    print(f"\nAvailable Energy:")
    print(f"  Can discharge: {battery.get_available_discharge_kwh():.2f} kWh")
    print(f"  Can charge: {battery.get_available_charge_kwh():.2f} kWh")
    
    # Test discharge
    print(f"\nDischarging 5 kWh...")
    battery.update_soc(
        energy_charged_kwh=0,
        energy_discharged_kwh=5,
        charge_efficiency=0.90
    )
    print(f"  New SOC: {battery.soc_kwh:.2f} kWh ({battery.soc_kwh/battery.capacity_kwh*100:.1f}%)")
    
    # Test charge
    print(f"\nCharging 10 kWh...")
    battery.update_soc(
        energy_charged_kwh=10,
        energy_discharged_kwh=0,
        charge_efficiency=0.90
    )
    print(f"  New SOC: {battery.soc_kwh:.2f} kWh ({battery.soc_kwh/battery.capacity_kwh*100:.1f}%)")
    
    # Test home service limit
    print(f"\nTesting home service limit conversion:")
    service_200a = battery.get_home_service_limit(service_amps=200)
    service_400a = battery.get_home_service_limit(service_amps=400)
    print(f"  200A service: {service_200a:.2f} kW")
    print(f"  400A service: {service_400a:.2f} kW")
    
    # Test temperature derating on discharge
    print(f"\nTesting discharge power with temperature derating:")
    temp_derating_normal = 1.0
    temp_derating_hot = 0.8
    
    print(f"  Normal temp (derating={temp_derating_normal}): {battery.get_effective_discharge_power_kw(temp_derating_normal):.2f} kW")
    print(f"  Hot temp (derating={temp_derating_hot}): {battery.get_effective_discharge_power_kw(temp_derating_hot):.2f} kW")
    
    # Test charge power with home constraints
    print(f"\nTesting charge power with home electrical constraints:")
    charge_power_low_load = battery.get_effective_charge_power_kw(
        temperature_derating=1.0,
        service_limit_amps=200,
        household_load_kw=5.0
    )
    charge_power_high_load = battery.get_effective_charge_power_kw(
        temperature_derating=1.0,
        service_limit_amps=200,
        household_load_kw=40.0
    )
    print(f"  200A service, 5kW load: {charge_power_low_load:.2f} kW")
    print(f"  200A service, 40kW load: {charge_power_high_load:.2f} kW")
    
    # Test combined battery power limits
    print(f"\nTesting combined battery power with all constraints:")
    power_limits = battery.get_effective_battery_power(
        temperature_derating=0.9,
        service_limit_amps=200,
        household_load_kw=10.0,
        inverter_limit_kw=11.0
    )
    print(f"  Max charge power: {power_limits['max_charge_kw']:.2f} kW")
    print(f"  Max discharge power: {power_limits['max_discharge_kw']:.2f} kW")
    
    # Test economic dispatch decisions with price thresholds
    print(f"\nTesting economic dispatch decisions:")
    from datetime import datetime
    import pandas as pd
    import numpy as np
    
    # Create sample price thresholds
    sample_thresholds = {
        1: {"charge": 0.05, "discharge": 0.12},
        6: {"charge": 0.06, "discharge": 0.15},
    }
    
    # Test charging decision
    jan_time = datetime(2024, 1, 15, 12, 0)
    low_price = 0.04
    should_charge = battery.should_charge(
        price_kwh=low_price,
        time=jan_time,
        price_thresholds=sample_thresholds
    )
    print(f"  January, price=${low_price:.3f}, threshold=${sample_thresholds[1]['charge']:.3f}: Should charge = {should_charge}")
    
    # Test discharge decision
    high_price = 0.15
    should_discharge = battery.should_discharge(
        price_kwh=high_price,
        time=jan_time,
        price_thresholds=sample_thresholds
    )
    print(f"  January, price=${high_price:.3f}, threshold=${sample_thresholds[1]['discharge']:.3f}: Should discharge = {should_discharge}")
    
    # Test with different month
    june_time = datetime(2024, 6, 15, 12, 0)
    mid_price = 0.10
    should_charge_june = battery.should_charge(
        price_kwh=mid_price,
        time=june_time,
        price_thresholds=sample_thresholds
    )
    should_discharge_june = battery.should_discharge(
        price_kwh=mid_price,
        time=june_time,
        price_thresholds=sample_thresholds
    )
    print(f"  June, price=${mid_price:.3f}: Should charge = {should_charge_june}, Should discharge = {should_discharge_june}")
    
    # Test battery dispatch function
    print(f"\nTesting battery dispatch function:")
    
    # Reset battery to 50% SOC
    battery.soc_kwh = 19.6
    
    # Test dispatch with low price (should charge)
    jan_time = datetime(2024, 1, 15, 12, 0)
    dispatch_result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.04,
        price_thresholds=sample_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    print(f"\n  Low price scenario (${dispatch_result['price_kwh']:.3f}):")
    print(f"    Action: {dispatch_result['action']}")
    print(f"    Power: {dispatch_result['power_kw']:.2f} kW")
    print(f"    Energy: {dispatch_result['energy_kwh']:.2f} kWh")
    print(f"    SOC: {dispatch_result['soc_before_kwh']:.2f} -> {dispatch_result['soc_after_kwh']:.2f} kWh")
    
    # Test dispatch with high price (should discharge)
    dispatch_result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.15,
        price_thresholds=sample_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    print(f"\n  High price scenario (${dispatch_result['price_kwh']:.3f}):")
    print(f"    Action: {dispatch_result['action']}")
    print(f"    Power: {dispatch_result['power_kw']:.2f} kW")
    print(f"    Energy: {dispatch_result['energy_kwh']:.2f} kWh")
    print(f"    SOC: {dispatch_result['soc_before_kwh']:.2f} -> {dispatch_result['soc_after_kwh']:.2f} kWh")
    
    # Test dispatch with mid price (should idle)
    battery.soc_kwh = 19.6  # Reset
    dispatch_result = Battery.dispatch_battery(
        battery=battery,
        home_load_kw=5.0,
        price_kwh=0.08,
        price_thresholds=sample_thresholds,
        timestamp=jan_time,
        temperature_derating=1.0,
        service_limit_amps=200,
        inverter_limit_kw=11.0,
    )
    
    print(f"\n  Mid price scenario (${dispatch_result['price_kwh']:.3f}):")
    print(f"    Action: {dispatch_result['action']}")
    print(f"    Power: {dispatch_result['power_kw']:.2f} kW")
    print(f"    Energy: {dispatch_result['energy_kwh']:.2f} kWh")
    print(f"    SOC: {dispatch_result['soc_before_kwh']:.2f} -> {dispatch_result['soc_after_kwh']:.2f} kWh")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")


