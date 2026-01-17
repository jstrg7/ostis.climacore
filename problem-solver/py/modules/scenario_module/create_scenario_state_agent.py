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


from datetime import datetime, timedelta, timezone
from .additions import get_interval


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class CreateScenarioStateAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_create_scenario_state")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("CreateScenarioStateAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("CreateScenarioStateAgent started")
        scenario = get_action_arguments(action_node, 1)[0]
        if not self.is_actual(scenario):
            self.logger.info("CreateScenarioStateAgent: this scenario is not actual yet.")
            return ScResult.OK
        instructions = self.get_instructions(scenario)
        print(len(instructions))
        for instruction in instructions:
            room, temp, hum = instruction
            temp_state, hum_state, co2_state = self.get_state(room, temp=[temp - 0.5, temp + 0.5], hum=[hum - 1.0, hum + 1.0])
            self.delete_previous_state(scenario, room)
            self.set_new_state(scenario, room, temp_state, hum_state, co2_state)

        
        link = generate_link(
            "CreateScenarioStateAgent is called", ScLinkContentType.STRING, link_type=sc_type.CONST_NODE_LINK)
        generate_action_result(action_node, link)
            
        return ScResult.OK
    


    def is_actual(self, scenario: ScAddr) -> bool:
        templ = ScTemplate()
        templ.quintuple(
            scenario,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_timestamp", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: 
            self.logger.info("Timestamp was not found")
            return False
        iso_timestamp = get_link_content_data(search_results[0].get("_link"))
        timestamp = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(timezone.utc) if timestamp.tzinfo else datetime.now()
        delta = abs(timestamp - now)
        return delta <= timedelta(minutes=10)



    def get_instructions(self, scenario: ScAddr) -> List[Tuple[ScAddr, float, float]]:
        templ = ScTemplate()
        templ.quintuple(
            scenario,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_set"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_instructions", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.triple(
            "_set",
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE, "_instruction")
        )
        search_result = search_by_template(templ)
        instructions = []
        for result in search_result:
            templ = ScTemplate()
            element = result.get("_instruction")
            templ.quintuple(
                element,
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE_LINK, "_temp_link"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_temp", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                element,
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE_LINK, "_hum_link"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_hum", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.quintuple(
                element,
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE, "_room"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_room", sc_type.CONST_NODE_NON_ROLE)
            )
            search_results = search_by_template(templ)
            temp = float(get_link_content_data(search_results[0].get("_temp_link")))
            hum = float(get_link_content_data(search_results[0].get("_hum_link")))
            room = search_results[0].get("_room")
            instructions.append((room, temp, hum))
        
        return instructions


    def get_state(self, room: ScAddr, temp: List[float], hum: List[float]) -> Tuple[ScAddr, ScAddr, ScAddr]:
        templ = ScTemplate()
        templ.quintuple(
            (sc_type.VAR_NODE, "_measurement"),
            sc_type.VAR_ACTUAL_TEMP_POS_ARC,
            room,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_current_measurement", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            "_measurement",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_temp_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_measurement",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_hum_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_hum", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_measurement",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_co2_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_co2", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        co2_state = ScAddr(0)
        if float(get_link_content_data(search_results[0].get("_co2_link"))) <= 800: co2_state = ScKeynodes.resolve("concept_co2_state_normal", sc_type.CONST_NODE_CLASS)
        else: co2_state = ScKeynodes.resolve("concept_co2_state_high", sc_type.CONST_NODE_CLASS)
        return ScKeynodes.resolve(f"concept_temp_state_{get_interval(l=temp[0], r=temp[1], value=float(get_link_content_data(search_results[0].get("_temp_link"))))}", sc_type.CONST_NODE_CLASS), ScKeynodes.resolve(f"concept_hum_state_{get_interval(l=hum[0], r=hum[1], value=float(get_link_content_data(search_results[0].get("_hum_link"))))}", sc_type.CONST_NODE_CLASS), co2_state


    def delete_previous_state(self, scenario: ScAddr, room: ScAddr) -> None:
        def is_relation(node: ScAddr) -> bool:
            templ = ScTemplate()
            templ.triple(
                ScKeynodes.resolve("concept_relation", sc_type.CONST_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                node
            )
            search_results = search_by_template(templ)
            if not search_results: return False
            else: return True

        def is_state(node: ScAddr) -> bool:
            templ = ScTemplate()
            templ.triple(
                ScKeynodes.resolve("concept_state", sc_type.CONST_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                node
            )
            search_results = search_by_template(templ)
            if not search_results: return False
            else: return True


        templ = ScTemplate()
        templ.quintuple(
            (sc_type.VAR_NODE, "_state"),
            sc_type.VAR_ACTUAL_TEMP_POS_ARC,
            room,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_current_state", sc_type.CONST_NODE_ROLE)
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
            sc_type.VAR_NODE,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp_state", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_hum_state", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_co2_state", sc_type.CONST_NODE_NON_ROLE)
        )

        search_results = search_by_template(templ)
        if not search_results:
            return None
        for i in range(len(search_results)):
            element = search_results[0].get(i)
            if element != room and element != scenario and not is_relation(element) and not is_state(element): erase_elements(element)
        
        return None



    def set_new_state(self, scenario: ScAddr, room: ScAddr, temp_state: ScAddr, hum_state: ScAddr, co2_state: ScAddr) -> None:
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
            temp_state,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp_state", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            hum_state,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_hum_state", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_state",
            sc_type.VAR_COMMON_ARC,
            co2_state,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_co2_state", sc_type.CONST_NODE_NON_ROLE)
        )

        generate_by_template(templ)

            
