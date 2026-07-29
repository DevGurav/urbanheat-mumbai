from app.llm.groq_client import generate_response



def generate_heat_explanation(data):


    prompt = f"""

You are an Urban Heat Intelligence AI assistant.

Analyze this prediction:

Location:
{data['location']}

Predicted Land Surface Temperature:
{data['predicted_LST']} °C


Environmental Indicators:

NDVI (Vegetation):
{data['NDVI']}

NDBI (Built-up):
{data['NDBI']}

NDWI (Water):
{data['NDWI']}


Risk Level:
{data['risk']}


Generate a concise dashboard explanation.

Include:

1. Heat condition explanation
2. Vegetation condition
3. Urban heat island reason
4. Recommendations for reducing heat


Answer in simple language.
"""


    result = generate_response(
        prompt
    )


    return result