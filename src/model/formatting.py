def format_number(value: float) -> str:
    text = f"{value:.2f}"
    if "." not in text:
        return text
    return text.rstrip("0").rstrip(".")
