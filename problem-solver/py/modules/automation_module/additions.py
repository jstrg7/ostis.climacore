from typing import List
from sc_client.models import ScAddr

def get_middle(numbers: List[float]) -> float:
    middle: float = 0.0
    for num in numbers:
        middle += num
    
    return middle / len(numbers)



def get_interval(l: float, r: float, value: float) -> str:
    if value < l: return "low"
    if value > r: return "high"
    return "normal"


def solves_problem(problems: List[ScAddr], solutions: List[ScAddr]) -> List[ScAddr]:
    result = problems.copy()
    for solution in solutions:
        if len(result) == 0: break
        if solution in problems: result.remove(solution)
    return result