from typing import List

def get_middle(numbers: List[float]) -> float:
    middle: float = 0.0
    for num in numbers:
        middle += num
    
    return middle / len(numbers)



def get_interval(l: float, r: float, value: float) -> str:
    if value < l: return "low"
    if value > r: return "high"
    return "normal"