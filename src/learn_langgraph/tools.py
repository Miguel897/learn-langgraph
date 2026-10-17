"""Toy tools shared by the demos. A tool is just a typed, documented Python
function: the docstring and type hints become the JSON schema the LLM sees."""
from langchain_core.tools import tool

_FAKE_WEATHER = {
    "madrid": "28°C and sunny",
    "london": "14°C and rainy",
    "tokyo": "22°C and cloudy",
}


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return _FAKE_WEATHER.get(city.lower(), f"No weather data for {city}")


@tool
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


BASIC_TOOLS = [get_weather, add, multiply]
