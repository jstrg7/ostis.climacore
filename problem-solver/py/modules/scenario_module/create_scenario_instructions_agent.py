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
from .additions import solves_problem


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class CreateScenarioInstructionsAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_create_scenario_instructions")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("CreateScenarioInstructionsAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("CreateScenarioInstructionsAgent started")
        [scenario, room] = get_action_arguments(action_node, 2)
        problem_states, normal_states = self.get_states(scenario, room)
        if len(problem_states) == 0 and len(normal_states) == 0: return ScResult.ERROR
        if len(problem_states) == 0: return ScResult.OK
        devices = self.get_devices(room)

        conflict_enabled_devices = self.get_conflict_enabled_devices(devices, problem_states)
        if len(conflict_enabled_devices) != 0:
            self.create_instructions(scenario, room, conflict_enabled_devices, ScKeynodes.resolve("is_off", sc_type.VAR_NODE))
            return ScResult.OK
    

        one_main_device = self.get_one_main_device(devices, problem_states)
        if one_main_device != ScAddr(0):
            self.create_instructions(scenario, room, [one_main_device], ScKeynodes.resolve("is_on", sc_type.VAR_NODE))
            return ScResult.OK


        devices_for_solving = self.get_solving_devices(devices, problem_states, normal_states) 
        self.create_instructions(scenario, room, devices_for_solving, ScKeynodes.resolve("is_on", sc_type.VAR_NODE))

        
        link = generate_link(
            "CreateInstructionsAgent is called", ScLinkContentType.STRING, link_type=sc_type.CONST_NODE_LINK)
        generate_action_result(action_node, link)
            
        return ScResult.OK

    def get_states(self, scenario: ScAddr, room: ScAddr) -> Tuple[List[ScAddr], List[ScAddr]]:
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
            ScKeynodes.resolve("rrel_current_scenario_state", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            scenario,
            sc_type.VAR_PERM_POS_ARC,
            "_state",
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
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
    


    def get_conflict_enabled_devices(self, devices: List[ScAddr], states: List[ScAddr]) -> List[ScAddr]:
        all_devices = []
        for device in devices:
            for state in states:
                templ = ScTemplate()
                templ.quintuple(
                    device,
                    sc_type.VAR_COMMON_ARC,
                    ScKeynodes.resolve("is_on", sc_type.VAR_NODE),
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("nrel_device_state", sc_type.CONST_NODE_NON_ROLE)
                )
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_type"),
                    sc_type.VAR_PERM_POS_ARC,
                    device
                )
                templ.quintuple(
                    "_type",
                    sc_type.VAR_PERM_POS_ARC,
                    state,
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("rrel_causes_state", sc_type.CONST_NODE_ROLE)
                )
                search_results = search_by_template(templ)
                if search_results:
                    all_devices.append(device)
                    break
        
        return all_devices
    


    def create_instructions(self, scenario: ScAddr, room: ScAddr, devices: List[ScAddr], type: ScAddr) -> None:
        templ = ScTemplate()
        set_node = generate_node(sc_type.CONST_NODE)
        sc_set = ScSet(set_node=set_node)
        templ.quintuple(
            room, 
            sc_type.VAR_COMMON_ARC,
            set_node,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_scenario_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            scenario,
            sc_type.VAR_PERM_POS_ARC,
            set_node,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
        )
        generate_by_template(templ)
        for device in devices:
            templ = ScTemplate()
            templ.quintuple(
                (sc_type.VAR_NODE, "_instruction"), 
                sc_type.VAR_COMMON_ARC,
                device,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                "_instruction", 
                sc_type.VAR_PERM_POS_ARC,
                type,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_ROLE)
            )
            generate_by_template(templ)
            sc_set.add(generate_by_template(templ).get("_instruction"))
        return None



    def get_one_main_device(self, devices: List[ScAddr], states: List[ScAddr]) -> ScAddr:
        variants = []
        for device in devices:
            templ = ScTemplate()
            templ.triple(
                (sc_type.VAR_NODE_CLASS, "_type"),
                sc_type.VAR_PERM_POS_ARC,
                device
            )
            for state in states:
                templ.quintuple(
                    "_type",
                    sc_type.VAR_PERM_POS_ARC,
                    state,
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
                )
            search_results = search_by_template(templ)
            if search_results: variants.append(device)
        
        if len(variants) == 0: return ScAddr(0)
        else: return variants[0]



    def get_solving_devices(self, devices: List[ScAddr], problems: List[ScAddr], normals: List[ScAddr]) -> List[ScAddr]:
        def has_causes(device: ScAddr, normal_states: List[ScAddr]) -> bool:
            for normal in normal_states:
                templ = ScTemplate()
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_type"),
                    sc_type.VAR_PERM_POS_ARC,
                    device
                )
                templ.quintuple(
                    "_type",
                    sc_type.VAR_PERM_POS_ARC,
                    (sc_type.VAR_NODE, "_problem"),
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
                )
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_param_class"),
                    sc_type.VAR_PERM_POS_ARC,
                    "_problem"
                )
                templ.triple(
                    "_param_class",
                    sc_type.VAR_PERM_POS_ARC,
                    normal
                )
                if search_by_template(templ): return True
            return False
        

        def has_conflict(all_devices: List[ScAddr], this_device: ScAddr):
            for chosen_device in all_devices:
                templ = ScTemplate()
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_type1"),
                    sc_type.VAR_PERM_POS_ARC,
                    this_device
                )
                templ.quintuple(
                    "_type1",
                    sc_type.VAR_PERM_POS_ARC,
                    (sc_type.VAR_NODE, "_problem1"),
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
                )
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_type2"),
                    sc_type.VAR_PERM_POS_ARC,
                    chosen_device
                )
                templ.quintuple(
                    "_type2",
                    sc_type.VAR_PERM_POS_ARC,
                    (sc_type.VAR_NODE, "_problem2"),
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
                )
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_param_class"),
                    sc_type.VAR_PERM_POS_ARC,
                    "_problem1"
                )
                templ.triple(
                    "_param_class",
                    sc_type.VAR_PERM_POS_ARC,
                    "_problem1"
                )
                search_results = search_by_template(templ)
                if not search_results: continue
                if search_results[0].get("_problem2") != search_results[0].get("_problem1"): return True
            return False
        

        device_effitient_list = []
        for device in devices:
            device_class = DeviceEfficiency(device=device)

            for problem in problems:
                templ = ScTemplate()
                templ.triple(
                    (sc_type.VAR_NODE_CLASS, "_type"),
                    sc_type.VAR_PERM_POS_ARC,
                    device
                )
                templ.quintuple(
                    "_type",
                    sc_type.VAR_PERM_POS_ARC,
                    problem,
                    sc_type.VAR_PERM_POS_ARC,
                    ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
                )
                search_results = search_by_template(templ)
                if search_results:
                    device_class.add_solution(problem)

            device_effitient_list.append(device_class)

        devices_result = []
        device_effitient_list = sorted(device_effitient_list, key=lambda de: de.solutions, reverse=True)
        for device_class in device_effitient_list:
            if len(problems) == 0: break
            if not has_causes(device=device_class.device, normal_states=normals) and not has_conflict(devices_result, device_class.device) and len(solves_problem(problems, device_class.problems_solve)) < len(problems):
                devices_result.append(device_class.device)
                problems = solves_problem(problems, device_class.problems_solve)

        return devices_result

            
