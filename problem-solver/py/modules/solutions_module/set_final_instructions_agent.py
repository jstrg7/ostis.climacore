"""
This source file is part of an OSTIS project. For the latest info, see http://ostis.net
Distributed under the MIT License
(See accompanying file COPYING.MIT or copy at http://opensource.org/licenses/MIT)
"""

import logging
from typing import List, Tuple, Dict
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



logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class CreateFinalInstructionsAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_create_final_instructions")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("CreateFinalInstructionsAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("CreateFinalInstructionsAgent started")
        room = get_action_arguments(action_node, 1)[0]
        machine_instructions = self.get_machine_instructions(room)
        scenario_instructions = self.get_scenario_instructions(room)
        for machine_instruction in machine_instructions:
            device = machine_instruction[0]
            state = machine_instruction[1]
            if not device in scenario_instructions:
                scenario_instructions[device] = state
        
        self.delete_previous_instructions(room)
        self.create_final_instructions(room, scenario_instructions)
        link = generate_link(
            "EditWeatherConditionsAgent is called", ScLinkContentType.STRING, link_type=sc_type.CONST_NODE_LINK)
        generate_action_result(action_node, link)
        return ScResult.OK


    def get_machine_instructions(self, room: ScAddr) -> List[Tuple[ScAddr, ScAddr]]:
        templ = ScTemplate()
        templ.quintuple(
            room,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_set"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_machine_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.triple(
            "_set",
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE, "_instruction")
        )
        templ.quintuple(
            "_instruction",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_device"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_instruction",
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE, "_state"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        instructions = []
        for result in search_results: instructions.append((another_search_results[0].get("_device"), another_search_results[0].get("_state")))
        return instructions
    


    def get_scenario_instructions(self, room: ScAddr) -> Dict[ScAddr, ScAddr]:
        def get_most_priority(device: ScAddr):
            to_off = 0
            to_off_count = 0
            to_on = 0
            to_on_count = 0
            is_on_node = ScKeynodes.resolve("is_on", sc_type.VAR_NODE)
            templ = ScTemplate()
            templ.quintuple(
                room,
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE, "_set"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_scenario_instructions", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.triple(
                "_set",
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_instruction")
            )
            templ.quintuple(
                "_instruction",
                sc_type.VAR_COMMON_ARC,
                device,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                "_instruction",
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_state"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                (sc_type.VAR_NODE, "_scenario"),
                sc_type.VAR_PERM_POS_ARC,
                "_set",
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
            )
            templ.quintuple(
                "_scenario",
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE_LINK, "_link"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_priority", sc_type.CONST_NODE_NON_ROLE)
            )
            search_results = search_by_template(templ)
            scenario_was = []
            for result in search_results:
                state = result.get("_state")
                priority = int(get_link_content_data(result.get("_link")))
                scenario = result.get("_scenario")
                if scenario in scenario_was: continue
                print(get_element_system_identifier(scenario))
                scenario_was.append(scenario)
                if state == is_on_node:
                    to_on += priority
                    to_on_count += 1
                else:
                    to_off += priority
                    to_off_count += 1

            print(scenario_was)
            print(to_off_count)
            print(to_on_count)

            if to_on_count == 0: return ScKeynodes.resolve("is_off", sc_type.VAR_NODE)
            if to_off_count == 0: return is_on_node
            if to_on / to_on_count > to_off / to_off_count: return is_on_node
            return ScKeynodes.resolve("is_off", sc_type.VAR_NODE)




        scenario_list = []
        templ = ScTemplate()
        templ.quintuple(
            room,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_set"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_scenario_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: return []
        for result in search_results:
            set_node = result.get("_set")
            templ = ScTemplate()
            scenario_instruction = []
            templ.triple(
                set_node,
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_instruction")
            )
            templ.quintuple(
                "_instruction",
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE, "_device"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                "_instruction",
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_state"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_NON_ROLE)
            )
            another_search_results = search_by_template(templ)
            if not another_search_results: continue
            for another_result in another_search_results:
                scenario_instruction.append((another_result.get("_device"), another_result.get("_state")))
            scenario_list.append(scenario_instruction)
        

        conflicted_instructions = []
        not_conflicted_instructions = {}
        for scenario in scenario_list:
            for device, state in scenario:
                if device not in not_conflicted_instructions:
                    not_conflicted_instructions[device] = state
                else:
                    if not_conflicted_instructions[device] != state:
                        conflicted_instructions.append(device)
                        del not_conflicted_instructions[device]
        
        for device in conflicted_instructions: not_conflicted_instructions[device] = get_most_priority(device)
        return not_conflicted_instructions
    


    def delete_previous_instructions(self, room: ScAddr) -> None:
        templ = ScTemplate()
        templ.quintuple(
            room,
            (sc_type.VAR_COMMON_ARC, "_arc2"),
            (sc_type.VAR_NODE, "_set"),
            (sc_type.VAR_PERM_POS_ARC, "_arc1"),
            ScKeynodes.resolve("nrel_final_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: return None
        set_node = search_results[0].get("_set")
        arc1 = search_results[0].get("_arc1")
        arc2 = search_results[0].get("_arc2")
        erase_elements(arc1, arc2)
        templ = ScTemplate()
        templ.triple(
            set_node,
            (sc_type.VAR_PERM_POS_ARC, "_arc1"),
            "_instruction"
        )
        templ.quintuple(
            "_instruction",
            (sc_type.VAR_PERM_POS_ARC, "_arc3"),
            sc_type.VAR_NODE,
            (sc_type.VAR_PERM_POS_ARC, "_arc2"),
            ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            "_instruction",
            (sc_type.VAR_COMMON_ARC, "_arc5"),
            sc_type.VAR_NODE,
            (sc_type.VAR_PERM_POS_ARC, "_arc4"),
            ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        for result in search_results:
            for i in range(1, 6):
                erase_elements(result.get(f"_arc{i}"))
            erase_elements(
                search_results[0].get("_instruction")
            )
        erase_elements(set_node)
        return None


    def create_final_instructions(self, room: ScAddr, instructions: Dict[ScAddr, ScAddr]) -> None:
        templ = ScTemplate()
        templ.quintuple(
            room,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_set"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_final_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        generation_result = generate_by_template(templ)
        set_node = generation_result.get("_set")
        for device in instructions:
            templ = ScTemplate()
            templ.triple(
                set_node,
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_instruction")
            )
            templ.quintuple(
                "_instruction",
                sc_type.VAR_PERM_POS_ARC,
                instructions[device],
                sc_type.VAR_PERM_POS_ARC, 
                ScKeynodes.resolve("rrel_change_to_state", sc_type.CONST_NODE_ROLE)
            )
            templ.quintuple(
                "_instruction",
                sc_type.VAR_COMMON_ARC, 
                device,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
            )

            generate_by_template(templ)
            


            
