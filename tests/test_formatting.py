from src.model.formatting import format_number


def test_format_number_trim_trailing_zero():
    assert format_number(12) == "12"
    assert format_number(12.5) == "12.5"
    assert format_number(12.34) == "12.34"
