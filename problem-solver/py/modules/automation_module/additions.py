from typing import List, Tuple
from sc_client.models import ScAddr
from .custiom_dataclasses import Problem

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


def delete_element_from_list(l: List[Problem], v: ScAddr) -> List[Problem]:
    for i in range(len(l)):
        if v == l[i].problem:
            del l[i]
            break
    return l


def in_list(v: ScAddr, l: List[Problem]) -> Tuple[bool, int]:
    for i in range(len(l)):
        if v == l[i].problem: return True, i
    return False, -1
