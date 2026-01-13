from dataclasses import dataclass
from typing import List
from sc_client.models import ScAddr

def solves_problem(problems: List[ScAddr], solutions: List[ScAddr]) -> List[ScAddr]:
    result = problems.copy()
    for solution in solutions:
        if len(result) == 0: break
        if solution in problems: result.remove(solution)
    return result