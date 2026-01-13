from dataclasses import dataclass, field
from typing import List
from sc_client.models import ScAddr

@dataclass 
class DeviceEfficiency:
    device: ScAddr = field(default_factory=lambda: ScAddr(0))
    problems_solve: List[ScAddr] = field(default_factory=list)
    solutions: int = 0

    def __init__(self, device: ScAddr = None, solutions: int = 0):
        self.device = device if device is not None else ScAddr(0)
        self.solutions = solutions
        self.problems_solve = []

    def add_solution(self, solution: ScAddr):
        self.solutions += 1
        self.problems_solve.append(solution)