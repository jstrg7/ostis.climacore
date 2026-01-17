def get_interval(l: float, r: float, value: float) -> str:
    if value < l: return "low"
    if value > r: return "high"
    return "normal"