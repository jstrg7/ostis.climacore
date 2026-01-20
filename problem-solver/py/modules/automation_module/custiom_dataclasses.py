from dataclasses import dataclass, field
from typing import List
from sc_client.models import ScAddr

@dataclass 
class DeviceEfficiency:
    device: ScAddr = field(default_factory=lambda: ScAddr(0))
    problems_solve: List[ScAddr] = field(default_factory=list)
    solutions: float = 0.0

    def __init__(self, device: ScAddr = None, solutions: float = 0.0):
        self.device = device if device is not None else ScAddr(0)
        self.solutions = solutions
        self.problems_solve = []

    def add_solution(self, solution: ScAddr, coefficient: float):
        self.solutions += 10 * coefficient
        self.problems_solve.append(solution)
    
    def add_cause(self):
        self.solutions -= 10


@dataclass
class Problem:
    problem: ScAddr = field(default_factory=lambda: ScAddr(0))
    problem_coefficient: float = 0.0

    def __init__(self, problem: ScAddr = None, problem_coefficient: int = 0):
        self.problem = problem if problem is not None else ScAddr(0)
        self.problem_coefficient: float = problem_coefficient