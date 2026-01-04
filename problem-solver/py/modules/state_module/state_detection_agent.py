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
    get_link_content,
    get_elements_types,
    generate_elements,
    erase_elements
)

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScStructure
from sc_kpm.utils import (
    generate_link,
    get_link_content_data,
    get_element_system_identifier
)
from sc_kpm.utils.action_utils import (
    finish_action_with_status,
    get_action_arguments,
    generate_action_result
)

from sc_kpm import ScKeynodes


from datetime import datetime

from .additions import (
    get_interval
)


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class StateDetectionAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_state_detection")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("StateDetectionAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("StateDetectionAgent started")
        house = get_action_arguments(action_node, 1)[0]
        rooms = self.get_rooms(house)
        user = self.get_user(house)
        temp_min, temp_max, hum_min, hum_max = self.get_preferences(user)
        for room in rooms:
            temp_state, hum_state, co2_state = self.get_state(room, temp=[temp_min, temp_max], hum=[hum_min, hum_max])
            self.delete_previous_state(room)
            self.set_new_state(room, temp_state, hum_state, co2_state)

        
        link = generate_link(
            "StateDetectionAgent is called", ScLinkContentType.STRING, link_type=sc_type.CONST_NODE_LINK)
        generate_action_result(action_node, link)
            
        return ScResult.OK
    

    def get_rooms(self, house: ScAddr) -> List[ScAddr]:
        templ = ScTemplate()
        templ.quintuple(
            house,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_set_rooms"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_rooms", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.triple(
            "_set_rooms",
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE, "_room")
        )

        search_results = search_by_template(templ)
        rooms = []
        for result in search_results:
            rooms.append(result.get("_room"))
        return rooms
    

    def get_user(self, house: ScAddr) -> ScAddr:
        templ = ScTemplate()
        templ.quintuple(
            (sc_type.VAR_NODE, "_user"),
            sc_type.VAR_PERM_POS_ARC,
            house,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
        )

        search_results = search_by_template(templ)
        return search_results[0].get("_user")
    

    def get_preferences(self, user: ScAddr) -> Tuple[float, float, float, float]:
        templ = ScTemplate()
        templ.quintuple(
            (sc_type.VAR_NODE, "_prefs"),
            sc_type.VAR_PERM_POS_ARC,
            user,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_owner", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            "_prefs",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_temp_range"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp_range", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_temp_range",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_temp_min"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_min", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_temp_range",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_temp_max"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_max", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_prefs",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_hum_range"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_humidity_range", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_hum_range",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_hum_min"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_min", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_hum_range",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_hum_max"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_max", sc_type.CONST_NODE_NON_ROLE)
        )

        search_results = search_by_template(templ)
        if not search_results:
            return -1, -1, -1, -1
        return float(get_link_content_data(search_results[0].get("_temp_min"))), float(get_link_content_data(search_results[0].get("_temp_max"))), float(get_link_content_data(search_results[0].get("_hum_min"))), float(get_link_content_data(search_results[0].get("_hum_max"))),
        
    

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
        if float(get_link_content_data(search_results[0].get("_co2_link"))) <= 800: co2_state = ScKeynodes.resolve("concept_state_normal", sc_type.CONST_NODE_CLASS)
        else: co2_state = ScKeynodes.resolve("concept_state_high", sc_type.CONST_NODE_CLASS)
        return ScKeynodes.resolve(f"concept_state_{get_interval(l=temp[0], r=temp[1], value=float(get_link_content_data(search_results[0].get("_temp_link"))))}", sc_type.CONST_NODE_CLASS), ScKeynodes.resolve(f"concept_state_{get_interval(l=hum[0], r=hum[1], value=float(get_link_content_data(search_results[0].get("_hum_link"))))}", sc_type.CONST_NODE_CLASS), co2_state


    def delete_previous_state(self, room: ScAddr) -> None:
        templ = ScTemplate()
        templ.quintuple(
            "_temp_state",
            (sc_type.VAR_ACTUAL_TEMP_POS_ARC, "_arc1"),
            room, 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_temp_state", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            "_hum_state",
            (sc_type.VAR_ACTUAL_TEMP_POS_ARC, "_arc2"),
            room, 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_hum_state", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            "_co2_state",
            (sc_type.VAR_ACTUAL_TEMP_POS_ARC, "_arc3"),
            room, 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_co2_state", sc_type.CONST_NODE_ROLE)
        )

        search_results = search_by_template(templ)
        if not search_results: return None

        erase_elements(search_results[0].get("_arc1"), search_results[0].get("_arc2"), search_results[0].get("_arc3"))
        return None
    


    def set_new_state(self, room: ScAddr, temp_state: ScAddr, hum_state: ScAddr, co2_state: ScAddr) -> None:
        templ = ScTemplate()
        templ.quintuple(
            temp_state,
            sc_type.VAR_ACTUAL_TEMP_POS_ARC,
            room, 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_temp_state", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            hum_state,
            sc_type.VAR_ACTUAL_TEMP_POS_ARC,
            room, 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_hum_state", sc_type.CONST_NODE_ROLE)
        )
        templ.quintuple(
            co2_state,
            sc_type.VAR_ACTUAL_TEMP_POS_ARC,
            room, 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_co2_state", sc_type.CONST_NODE_ROLE)
        )

        generate_by_template(templ)
        
    

            







        


        

        


        