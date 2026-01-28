"""
This source file is part of an OSTIS project. For the latest info, see http://ostis.net
Distributed under the MIT License
(See accompanying file COPYING.MIT or copy at http://opensource.org/licenses/MIT)
"""

import logging
from typing import List, Tuple
from sc_client.models import ScConstruction
from sc_client.models import ScAddr, ScLinkContentType, ScLinkContent, ScTemplate
from sc_client.constants import sc_type
from sc_client.client import (
    search_by_template,
    generate_by_template, 
    generate_elements,
    erase_elements
)

from sc_kpm.sc_sets import ScSet

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScStructure
from sc_kpm.utils import (
    generate_link,
    get_link_content_data,
    get_element_system_identifier,
    generate_node
)
from sc_kpm.utils.action_utils import (
    finish_action_with_status,
    get_action_arguments,
    generate_action_result
)

from sc_kpm import ScKeynodes


from datetime import datetime
from .additions import solves_problem, delete_element_from_list, in_list

from .custiom_dataclasses import DeviceEfficiency, Problem


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class CreateInstructionsAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_create_instructions")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("CreateInstructionsAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("CreateInstructionsAgent started")
        room = get_action_arguments(action_node, 1)[0]
        problem_states, normal_states = self.get_states(room)
        if len(problem_states) == 0 and len(normal_states) == 0: return ScResult.ERROR
        if len(problem_states) == 0:
            print(1) 
            return ScResult.OK
        devices = self.get_devices(room)
        problems = []
        for problem_state in problem_states:
            deviation = self.get_deviation(problem_state)
            problems.append(Problem(problem_state, deviation))

        print(problems)
        
        problems = sorted(problems, key=lambda p: abs(p.problem_coefficient), reverse=True)
        conflict_enable_devices, problems = self.get_conflict_enable_devices(room, devices, problems)
        print(conflict_enable_devices)
        if len(problems) == 0:
            self.logger.info("All enabled devices is off")
            self.create_instructions(room=room, enabled_devices=conflict_enable_devices, other_devices=[])
            return ScResult.OK
        
        other_devices = self.get_other_devices(devices, problems, normal_states)
        print(other_devices)
        self.create_instructions(
            room=room,
            enabled_devices=conflict_enable_devices,
            other_devices=other_devices
        )
        return ScResult.OK
    


    def get_states(self, room: ScAddr) -> Tuple[List[ScAddr], List[ScAddr]]:
        def is_normal(state: ScAddr) -> bool:
            templ = ScTemplate()
            templ.triple(
                ScKeynodes.resolve("concept_state_normal", sc_type.CONST_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                state
            )
            search_results = search_by_template(templ)
            if not search_results: return False
            return True
        

        templ = ScTemplate()
        templ.quintuple(
            (sc_type.VAR_NODE, "_state"),
            sc_type.VAR_ACTUAL_TEMP_POS_ARC,
            room,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_current_state", sc_type.CONST_NODE_ROLE) 
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_temp_state"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp_state", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_hum_state"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_hum_state", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_co2_state"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_co2_state", sc_type.CONST_NODE_NON_ROLE)
        )

        search_results = search_by_template(templ)
        if not search_results:
            return [], []
        problem_states = []
        normal_states = []
        for state in [search_results[0].get('_temp_state'), search_results[0].get('_hum_state'), search_results[0].get('_co2_state')]:
            if is_normal(state): normal_states.append(state)
            else: problem_states.append(state)

        return problem_states, normal_states
    

    def get_devices(self, room: ScAddr) -> List[ScAddr]:
        templ = ScTemplate()
        templ.quintuple(
            (sc_type.VAR_NODE, "_device"),
            sc_type.VAR_PERM_POS_ARC,
            room,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_located_at", sc_type.CONST_NODE_ROLE)
        )
        templ.triple(
            ScKeynodes.resolve("concept_device", sc_type.VAR_NODE_CLASS),
            sc_type.VAR_PERM_POS_ARC,
            "_device"
        )
        search_results = search_by_template(templ)
        devices = []
        for result in search_results: devices.append(result.get("_device"))
        return devices
        



    def create_instructions(self, room: ScAddr, enabled_devices: List[ScAddr], other_devices: List[ScAddr]) -> None:
        templ = ScTemplate()
        set_node = generate_node(sc_type.CONST_NODE)
        sc_set = ScSet(set_node=set_node)
        templ.quintuple(
            room, 
            sc_type.VAR_COMMON_ARC,
            set_node,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_machine_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        generate_by_template(templ)
        for e_device in enabled_devices:
            templ = ScTemplate()
            templ.quintuple(
                (sc_type.VAR_NODE, "_instruction"), 
                sc_type.VAR_COMMON_ARC,
                e_device,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                "_instruction", 
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("is_off", sc_type.VAR_NODE),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_ROLE)
            )
            generate_by_template(templ)
            sc_set.add(generate_by_template(templ).get("_instruction"))
        for o_device in other_devices:
            templ = ScTemplate()
            templ.quintuple(
                (sc_type.VAR_NODE, "_instruction"), 
                sc_type.VAR_COMMON_ARC,
                o_device,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                "_instruction", 
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("is_on", sc_type.VAR_NODE),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_ROLE)
            )
            generate_by_template(templ)
            sc_set.add(generate_by_template(templ).get("_instruction"))
        return None
    


    def get_deviation(self, problem_state: ScAddr) -> float:
        templ = ScTemplate()
        templ.quintuple(
            problem_state,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_deviation"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: return -1000.0
        return float(get_link_content_data(search_results[0].get("_deviation")))
        
    def get_conflict_enable_devices(self, room: ScAddr, devices: List[ScAddr], problems: List[Problem]) -> Tuple[List[ScAddr], List[Problem]]:
        enabled_devices = []
        problems_copy = problems.copy()
        for device in devices:
            if len(problems) == 0: break
            templ = ScTemplate()
            templ.triple(
                (sc_type.VAR_NODE_CLASS, "_device_type"),
                sc_type.VAR_PERM_POS_ARC,
                device
            )
            templ.quintuple(
                device,
                sc_type.VAR_COMMON_ARC,
                ScKeynodes.resolve("is_on", sc_type.VAR_NODE),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device_state", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                "_device_type",
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE_CLASS, "_state"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_causes_state",sc_type.CONST_NODE_ROLE)
            )
            search_results = search_by_template(templ)
            previous_len = len(problems_copy)
            for result in search_results:
                problems_copy = delete_element_from_list(problems_copy, result.get("_state"))
                if len(problems_copy) == 0: break
            if previous_len > len(problems_copy): enabled_devices.append(device) 
        return enabled_devices, problems_copy
    


    def get_other_devices(self, devices: List[ScAddr], problems: List[Problem], normals: List[ScAddr]) -> List[ScAddr]:
        device_list = []
        problems_list = problems 
        
        for device in devices:
            templ = ScTemplate()
            templ.quintuple(
                device,
                sc_type.VAR_COMMON_ARC,
                ScKeynodes.resolve("is_on", sc_type.VAR_NODE),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device_state", sc_type.CONST_NODE_NON_ROLE)
            )
            if search_by_template(templ):  
                continue
            
            device_efficiency = DeviceEfficiency(device=device)
            solves_any_problem = False
            
            templ = ScTemplate()
            templ.triple(
                (sc_type.VAR_NODE_CLASS, "_device_class"),
                sc_type.VAR_PERM_POS_ARC,
                device
            )
            templ.quintuple(
                "_device_class",
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_state"),  
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_NON_ROLE)
            )
            search_results = search_by_template(templ)
            
            for result in search_results:
                state = result.get("_state")
                in_list_flag, index = in_list(state, problems_list)
                if in_list_flag:
                    solves_any_problem = True
                    device_efficiency.add_solution(state, problems_list[index].problem_coefficient)
            
            templ = ScTemplate()
            templ.triple(
                (sc_type.VAR_NODE_CLASS, "_device_class"),
                sc_type.VAR_PERM_POS_ARC,
                device
            )
            templ.quintuple(
                "_device_class",
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_state"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_causes_state", sc_type.CONST_NODE_NON_ROLE)
            )
            search_results = search_by_template(templ)
            
            for result in search_results:
                state = result.get("_state")
                
                
                is_normal_state = False
                for normal in normals:
                    if normal == state:  
                        is_normal_state = True
                        break
                
                
                if not is_normal_state:
                    device_efficiency.add_cause()
            
            if solves_any_problem:
                device_list.append(device_efficiency)
        
        device_list = sorted(device_list, key=lambda de: de.solutions, reverse=True)
        
        
        result_list = []
        remaining_problems = problems_list.copy()
        
        for device_efficiency in device_list:
            if not remaining_problems:
                break
            
            device = device_efficiency.device
            solves_problems = device_efficiency.problems_solve
            
            solves_something = False
            problems_to_remove = []
            
            for solved_state in solves_problems:
                for i, problem in enumerate(remaining_problems):
                    if problem.problem == solved_state:
                        solves_something = True
                        problems_to_remove.append(i)
                        break
            
            if solves_something:
                result_list.append(device)
                
               
                problems_to_remove.sort(reverse=True)
                for idx in problems_to_remove:
                    if 0 <= idx < len(remaining_problems):
                        del remaining_problems[idx]
        
        return result_list





        
