from learn_langgraph import add, get_weather, multiply


def test_math_tools() -> None:
    assert add.invoke({"a": 2, "b": 3}) == 5
    assert multiply.invoke({"a": 4, "b": 2.5}) == 10


def test_weather_tool() -> None:
    assert "sunny" in get_weather.invoke({"city": "Madrid"})
    assert get_weather.invoke({"city": "Atlantis"}).startswith("No weather data")


def test_tool_schema_comes_from_signature() -> None:
    assert set(add.args) == {"a", "b"}
    assert add.description == "Add two numbers."
