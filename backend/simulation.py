from datetime import datetime

def get_simulated_load_kw(timestamp: datetime) -> float:
    """
    Returns a realistic home load in kW based on time of day.
    Base Load: 0.5 kW
    Morning Peak (07-09): +1.0 kW
    Evening Peak (18-22): +1.5 kW
    """
    hour = timestamp.hour + (timestamp.minute / 60.0)
    
    base = 0.5
    
    # Morning Peak 07:00 - 09:00
    if 7.0 <= hour < 9.0:
        base += 1.0
        
    # Evening Peak 18:00 - 22:00
    elif 18.0 <= hour < 22.0:
        base += 1.5
        
    return base
