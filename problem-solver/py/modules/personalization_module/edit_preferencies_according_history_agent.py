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
    get_element_system_identifier
)
from sc_kpm.utils.action_utils import (
    finish_action_with_status,
    get_action_arguments,
    generate_action_result
)

from sc_kpm import ScKeynodes


from datetime import datetime


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class EditPreferenciesAccodingHistoryAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_edit_preferencties")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("EditPreferenciesAccodingHistoryAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("EditPreferenciesAccodingHistoryAgent started")
        [device, user] = get_action_arguments(action_node, 2)
        temp_values, hum_values = self.get_history(user, device)
        temp_diapazone_size, hum_diapazone_size = self.get_diapazone_size(user)
        states = self.get_fixing_state(device)
        temp_state = self.has_relation_to(states, ScKeynodes.resolve("concept_temp_state", sc_type.VAR_NODE_CLASS))
        if temp_state != ScAddr(0):
            self.solve(user, temp_values, temp_diapazone_size, temp_state, ScKeynodes.resolve("nrel_temp_range", sc_type.CONST_NODE_NON_ROLE))
        hum_state = self.has_relation_to(states, ScKeynodes.resolve("concept_hum_state", sc_type.VAR_NODE_CLASS))
        if hum_state != ScAddr(0):
            self.solve(user, hum_values, hum_diapazone_size, hum_state, ScKeynodes.resolve("nrel_hum_range", sc_type.CONST_NODE_NON_ROLE))
        


        return ScResult.OK

    
    def get_room(self, device: ScAddr) -> ScAddr:
        templ = ScTemplate()
        templ.quituple(
            device,
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE, "_room"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_located_at", sc_type.CONST_NODE_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: return ScAddr(0)
        return search_results[0].get("_room")
    

    def get_history(self, user: ScAddr, device: ScAddr):
        templ = ScTemplate()
        templ.quintuple(
            user,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_set"), 
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_device_history", sc_type.CONST_NODE_ROLE)
        )
        templ.triple(
            "_set",
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE, "_element")
        )
        templ.quintuple(
            "_element",
            sc_type.VAR_COMMON_ARC,
            device,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_device", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_element",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_temp_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp_value", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_element",
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_hum_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_hum_value", sc_type.CONST_NODE_NON_ROLE)
        )

        search_result = search_by_template(templ)
        temp_values = []
        hum_values = []
        for result in search_result:
            temp = float(get_link_content_data(result.get("_temp_link")))
            hum = float(get_link_content_data(result.get("_hum_link")))
            temp_values.append(temp)
            hum_values.append(hum)
        return temp_values, hum_values
    

    def get_diapazone_size(self, user: ScAddr) -> float:
        templ = ScTemplate()
        templ.quintuple(
            user,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_prefs"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_prefs", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.triple(
            ScKeynodes.resolve("concept_user_preferences", sc_type.VAR_NODE_CLASS),
            sc_type.VAR_PERM_POS_ARC,
            "_prefs"
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
            ScKeynodes.resolve("nrel_hum_range", sc_type.CONST_NODE_NON_ROLE)
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

        search_result = search_by_template(templ)
        if not search_result: return 0.0, 0.0
        return float(get_link_content_data(search_result[0].get("_temp_max"))) - float(get_link_content_data(search_result[0].get("_temp_min"))), float(get_link_content_data(search_result[0].get("_hum_max"))) - float(get_link_content_data(search_result[0].get("_hum_min"))) 
    


    def get_fixing_state(self, device: ScAddr) -> List[ScAddr]:
        templ = ScTemplate()
        templ.triple(
            (sc_type.VAR_NODE_CLASS, "_device_type"),
            sc_type.VAR_PERM_POS_ARC,
            device
        )
        templ.quintuple(
            "_device_type",
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE_CLASS, "_state"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
        )
        search_results = search_by_template(templ)
        states = []
        for result in search_results:
            states.append(result.get("_state"))
        return states
    


    def has_relation_to(self, states: List[ScAddr], relate_class: ScAddr) -> ScAddr:
        for state in states:
            templ = ScTemplate()
            templ.triple(
                relate_class,
                sc_type.VAR_PERM_POS_ARC,
                state
            )
            search_results = search_by_template(templ)
            if search_results: return state
        return ScAddr(0)
    


    def solve(self, user: ScAddr, values: List[float], diapazone: float, state: ScAddr, relation_type: ScAddr) -> None:
        def is_less(state_: ScAddr) -> bool:
            templ = ScTemplate()
            templ.triple(
                ScKeynodes.resolve("concept_state_low", sc_type.VAR_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                state_
            )
            if search_by_template(templ): return True
            return False
        
        def generate_link_with_data(data: float) -> ScAddr:
            construction = ScConstruction()
            link_content = ScLinkContent(data, ScLinkContentType.FLOAT)
            construction.generate_link(sc_type.CONST_NODE_LINK, link_content, 'link')
            link = generate_elements(construction)[0]
            return link
        
        def get_prefs_node(user: ScAddr) -> ScAddr:
            templ = ScTemplate()
            templ.quintuple(
                user,
                sc_type.VAR_COMMON_ARC,
                (sc_type.VAR_NODE, "_prefs"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("nrel_prefs", sc_type.CONST_NODE_NON_ROLE)
            )
            templ.triple(
                ScKeynodes.resolve("concept_user_preferences", sc_type.VAR_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                "_prefs"
            )
            search_results = search_by_template(templ)
            if search_results: return search_results[0].get("_prefs")
            return ScAddr(0)
        
        templ = ScTemplate()
        prefs = get_prefs_node(user)
        templ.quintuple(
            prefs,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE, "_range"),
            sc_type.VAR_PERM_POS_ARC,
            relation_type
        )
        templ.quintuple(
            "_range",
            (sc_type.VAR_COMMON_ARC, "_arc2"),
            (sc_type.VAR_NODE_LINK, "_min"),
            (sc_type.VAR_PERM_POS_ARC, "_arc1"),
            ScKeynodes.resolve("nrel_min", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            "_range",
            (sc_type.VAR_COMMON_ARC, "_arc4"),
            (sc_type.VAR_NODE_LINK, "_max"),
            (sc_type.VAR_PERM_POS_ARC, "_arc3"),
            ScKeynodes.resolve("nrel_max", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: 
            return None
        range = search_results[0].get("_range")
        erase_elements(
            search_results[0].get("_arc1"),
            search_results[0].get("_arc2"),
            search_results[0].get("_arc3"),
            search_results[0].get("_arc4")
        )
        erase_elements(
            search_results[0].get("_min"),
            search_results[0].get("_max")
        )

        min_size = max_size = 0.0
        if is_less(state):
            min_size = sum(values) / len(values)
            max_size = min_size + diapazone
        else:
            max_size = sum(values) / len(values)
            min_size = max_size - diapazone
        min_link = generate_link_with_data(min_size)
        max_link = generate_link_with_data(max_size)
        templ = ScTemplate()
        templ.quintuple(
            range,
            sc_type.VAR_COMMON_ARC,
            min_link,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_min", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            range,
            sc_type.VAR_COMMON_ARC, 
            max_link,
            sc_type.VAR_PERM_POS_ARC, 
            ScKeynodes.resolve("nrel_max", sc_type.CONST_NODE_NON_ROLE)
        )
        generate_by_template(templ)
        return None


