def calculate_roi(
    annual_benefit: float,
    installation_cost: float,
    monthly_fee: float,
    years: int = 5
) -> dict:
    """
    Calculate return on investment for Base battery system.
    
    Args:
        annual_benefit: Estimated annual benefit in dollars
        installation_cost: Upfront installation cost
        monthly_fee: Monthly membership fee
        years: Number of years for analysis (default 5)
        
    Returns:
        dict with net_5_year_value, simple_payback, annual_net_value
    """
    pass

def get_base_plan(utility: str, zip_code: str) -> dict:
    """
    Get Base pricing plan for specific utility and location.
    
    Args:
        utility: Utility name
        zip_code: ZIP code
        
    Returns:
        dict with installation_fee, monthly_fee, battery_count
    """
    pass
