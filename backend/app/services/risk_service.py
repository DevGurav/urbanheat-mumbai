def calculate_heat_risk(lst, ndvi):

    if lst is None or ndvi is None:
        return "Unknown"


    # Extreme heat + no vegetation
    if lst >= 40 and ndvi < 0.2:
        return "High"


    # Medium heat
    elif lst >= 35 and ndvi < 0.4:
        return "Moderate"


    else:
        return "Low"



def vegetation_status(ndvi):

    if ndvi is None:
        return "Unknown"

    if ndvi < 0.2:
        return "Poor"

    elif ndvi < 0.5:
        return "Moderate"

    else:
        return "Good"