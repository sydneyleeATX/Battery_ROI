def estimate_monthly_kwh(monthly_bill: float, utility: str) -> float:
    """
    Convert monthly electricity bill to estimated kWh consumption.
    
    Args:
        monthly_bill: Average monthly electricity bill in dollars
        utility: Utility name
        
    Returns:
        Estimated monthly kWh consumption
    """
    pass

def create_home_load_profile(
    monthly_kwh: float,
    temperature: list,
    month: int,
    hour: int,
    weekday: bool
):
    """
    Create synthetic 15-minute homeowner load profile.
    
    Args:
        monthly_kwh: Monthly electricity consumption
        temperature: Temperature data
        month: Month of year
        hour: Hour of day
        weekday: Whether it's a weekday
        
    Returns:
        15-minute load profile with timestamp and estimated_home_kw
    """
    pass
