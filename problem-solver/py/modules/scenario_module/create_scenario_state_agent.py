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

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScStructure
from sc_kpm.utils import (
    generate_link,
    get_link_content_data,
)
from sc_kpm.utils.action_utils import (
    finish_action_with_status,
    get_action_arguments,
    generate_action_result
)

from sc_kpm import ScKeynodes


from datetime import datetime, timezone, time
from typing import Optional

from .additions import (
    get_interval
)


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
            self.logger.info("This scenario is not actual yet.")
            return ScResult.OK
        instructions = self.get_instructions(scenario)
        print(len(instructions))
        for instruction in instructions:
            room, temp, hum = instruction
            temp_dev = abs(self.get_measurement(room, ScKeynodes.resolve("nrel_temp", sc_type.CONST_NODE_NON_ROLE)) - temp) / temp
            hum_dev = abs(self.get_measurement(room, ScKeynodes.resolve("nrel_hum", sc_type.CONST_NODE_NON_ROLE)) - hum) / hum
            co2_dev = 0.0
            co2 = self.get_measurement(room, ScKeynodes.resolve("nrel_co2", sc_type.CONST_NODE_NON_ROLE))
            if co2 > 800: co2_dev = (co2 - 800) / 700

            temp_state, hum_state, co2_state = self.get_state(room=room, temp=[temp - 0.5, temp + 0.5], hum=[hum - 1.0, hum + 1.0])
            self.delete_previous_state(scenario, room)
            self.set_new_state(scenario, room, temp_state, hum_state, co2_state, temp_dev, hum_dev, co2_dev)

        
        link = generate_link(
            "CreateScenarioStateAgent is called", ScLinkContentType.STRING, link_type=sc_type.CONST_NODE_LINK)
        generate_action_result(action_node, link)
        return ScResult.OK
    

    def is_actual(self, scenario: ScAddr) -> bool:
        def extract_time_from_iso(iso_str: str) -> Optional[time]:
            try:
                iso_str = iso_str.strip()
                
                if 'T' not in iso_str:
                    self.logger.warning(f"No 'T' found in ISO string: {iso_str}")
                    return None
                
                time_part = iso_str.split('T')[1]
                
                if '+' in time_part:
                    time_part = time_part.split('+')[0]
                elif '-' in time_part and ':' in time_part.split('-')[1]:
                    time_part = time_part.split('-')[0]
                elif 'Z' in time_part:
                    time_part = time_part.split('Z')[0]
                
                parts = time_part.split(':')
                
                if len(parts) < 2:
                    self.logger.warning(f"Invalid time format: {time_part}")
                    return None
                
                hour = int(parts[0])
                minute = int(parts[1])
                
                if len(parts) > 2:
                    seconds_part = parts[2]
                    if '.' in seconds_part:
                        seconds_part = seconds_part.split('.')[0]
                    second = int(seconds_part)
                else:
                    second = 0
                
                if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
                    self.logger.warning(f"Invalid time values: {hour}:{minute}:{second}")
                    return None
                
                return time(hour, minute, second)
                
            except (ValueError, IndexError, AttributeError) as e:
                self.logger.error(f"Failed to parse time from '{iso_str}': {e}")
                return None
            
        templ = ScTemplate()
        templ.quintuple(
            scenario,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_start_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_start_time", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            scenario,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_finish_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_finish_time", sc_type.CONST_NODE_NON_ROLE)
        )
        
        search_results = search_by_template(templ)
        if not search_results: 
            return False
        
        start_iso = get_link_content_data(search_results[0].get("_start_link"))
        finish_iso = get_link_content_data(search_results[0].get("_finish_link"))
        
        start_time = extract_time_from_iso(start_iso)
        finish_time = extract_time_from_iso(finish_iso)
        
        
        now_local = datetime.now()
        current_time = time(now_local.hour, now_local.minute, now_local.second)
        

        if start_time <= finish_time:
            is_in_interval = start_time <= current_time <= finish_time
            return is_in_interval
        else:
            is_in_interval = current_time >= start_time or current_time <= finish_time
            return is_in_interval


    def get_measurement(self, room: ScAddr, type: ScAddr) -> float:
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
            (sc_type.VAR_NODE_LINK, "_link"),
            sc_type.VAR_PERM_POS_ARC,
            type
        )
        search_results = search_by_template(templ)
        if not search_results: return -1000.0
        return float(get_link_content_data(search_results[0].get("_link")))


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


    def delete_previous_state(self, room: ScAddr, scenario: ScAddr) -> None:
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
        templ.quintuple(
            "_co2_state",
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE_LINK,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_hum_state",
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE_LINK,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_temp_state",
            sc_type.VAR_COMMON_ARC,
            sc_type.VAR_NODE_LINK,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )


        search_results = search_by_template(templ)
        if not search_results:
            return None
        for i in range(len(search_results)):
            element = search_results[0].get(i)
            if element != room and not is_relation(element) and not is_state(element): erase_elements(element)
        
        return None
    


    def set_new_state(self, scenario: ScAddr, room: ScAddr, temp_state: ScAddr, hum_state: ScAddr, co2_state: ScAddr, temp_dev: float, hum_dev: float, co2_dev: float) -> None:
        def generate_link_with_data(data: float) -> ScAddr:
            construction = ScConstruction()
            link_content = ScLinkContent(data, ScLinkContentType.FLOAT)
            construction.generate_link(sc_type.CONST_NODE_LINK, link_content, 'link')
            link = generate_elements(construction)[0]
            return link
        

        temp_link = generate_link_with_data(temp_dev)
        hum_link = generate_link_with_data(hum_dev)
        co2_link = generate_link_with_data(co2_dev)

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
        templ.quintuple(
            temp_state,
            sc_type.VAR_COMMON_ARC,
            temp_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            hum_state,
            sc_type.VAR_COMMON_ARC,
            hum_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            co2_state,
            sc_type.VAR_COMMON_ARC,
            co2_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_deviation", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            scenario,
            sc_type.VAR_PERM_POS_ARC,
            hum_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            scenario,
            sc_type.VAR_PERM_POS_ARC,
            temp_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            scenario,
            sc_type.VAR_PERM_POS_ARC,
            co2_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
        )

        generate_by_template(templ)