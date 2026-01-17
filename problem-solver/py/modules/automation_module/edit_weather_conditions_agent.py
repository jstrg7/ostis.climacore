"""
This source file is part of an OSTIS project. For the latest info, see http://ostis.net
Distributed under the MIT License
(See accompanying file COPYING.MIT or copy at http://opensource.org/licenses/MIT)
"""

import logging
from typing import List, Tuple
from pyowm import OWM
from pyowm.utils.config import get_default_config

from sc_client.models import ScConstruction
from sc_client.models import ScAddr, ScLinkContentType, ScLinkContent, ScTemplate
from sc_client.constants import sc_type
from sc_client.client import (
    search_by_template,
    generate_by_template, 
    generate_elements,
    get_elements_types,
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
from .additions import get_interval

PYOWM_TOKEN = "YOUR_TOKEN_BOT"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s", datefmt="[%d-%b-%y %H:%M:%S]"
)


class EditWeatherConditionsAgent(ScAgentClassic):
    def __init__(self):
        super().__init__("action_edit_weather_conditions")

    def on_event(self, action_class: ScAddr, arc: ScAddr, action: ScAddr) -> ScResult:
        result = self.run(action)
        is_successful = result == ScResult.OK
        finish_action_with_status(action, is_successful)
        self.logger.info("EditWeatherConditionsAgent finished %s",
                         "successfully" if is_successful else "unsuccessfully")
        return result

    def run(self, action_node: ScAddr) -> ScResult:
        self.logger.info("EditWeatherConditionsAgent started")
        [house, weather, user] = get_action_arguments(action_node, 3)
        temp_min, temp_max = self.get_preferences(user)
        status, temp, hum = self.get_weather_params(house, weather)
        if len(status) == 0: return ScResult.ERROR
        self.delete_previous_state(weather)
        self.create_measurements(weather, status, temp, hum)
        self.edit_device_consequences(temp, temp_min, temp_max)
        link = generate_link(
            "EditWeatherConditionsAgent is called", ScLinkContentType.STRING, link_type=sc_type.CONST_NODE_LINK)
        generate_action_result(action_node, link)
            
        return ScResult.OK
        
    def get_weather_params(self, house: ScAddr, weather: ScAddr) -> Tuple[str, float, float]:
        templ = ScTemplate()
        templ.quintuple(
            house,
            sc_type.VAR_COMMON_ARC,
            (sc_type.VAR_NODE_LINK, "_link"),
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_location", sc_type.CONST_NODE_NON_ROLE)
        )
        search_results = search_by_template(templ)
        if not search_results: return "", -1000, -1000 
        location = get_link_content_data(search_results[0].get("_link"))
        try:
            config_dict = get_default_config()
            config_dict['language'] = 'en'  
            owm = OWM(PYOWM_TOKEN, config_dict) 
            weather_manager = owm.weather_manager()
            observation = weather_manager.weather_at_place(location)
            status = observation.weather.status
            temp = observation.weather.temperature("celsius")['temp']
            hum = observation.weather.humidity
            return status.lower(), temp, hum
        except Exception as e:
            self.logger.info("EditWeatherConditionsAgent has some problems with pyowm.")
            return "", -1000, -1000 
        
    def get_preferences(self, user: ScAddr) -> Tuple[float, float]:
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

        search_results = search_by_template(templ)
        if not search_results:
            return -1, -1
        return float(get_link_content_data(search_results[0].get("_temp_min"))), float(get_link_content_data(search_results[0].get("_temp_max")))
    
    def delete_previous_state(self, weather: ScAddr) -> None:
        templ = ScTemplate()
        templ.triple(
            (sc_type.VAR_NODE_CLASS, "_state_class"),
            (sc_type.VAR_PERM_POS_ARC, "_arc1"),
            weather
        )
        templ.quintuple(
            weather,
            (sc_type.VAR_COMMON_ARC, "_arc3"),
            (sc_type.VAR_NODE_LINK, "_link1"),
            (sc_type.VAR_PERM_POS_ARC, "_arc2"),
            ScKeynodes.resolve("nrel_temp", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            weather,
            (sc_type.VAR_COMMON_ARC, "_arc5"),
            (sc_type.VAR_NODE_LINK, "_link2"),
            (sc_type.VAR_PERM_POS_ARC, "_arc4"),
            ScKeynodes.resolve("nrel_hum", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            weather,
            (sc_type.VAR_COMMON_ARC, "_arc7"),
            (sc_type.VAR_NODE_LINK, "_link3"),
            (sc_type.VAR_PERM_POS_ARC, "_arc6"),
            ScKeynodes.resolve("nrel_timestamp", sc_type.CONST_NODE_NON_ROLE)
        )

        search_results = search_by_template(templ)
        if not search_results: return None
        for i in range(1, 8):
            element = search_results[0].get("_arc" + str(i))
            erase_elements(element)
        for i in range(1, 4):
            element = search_results[0].get("_link" + str(i))
            erase_elements(element)
        return None
    


    def create_measurements(self, weather: ScAddr, status: str, temp: float, hum: float) -> None:
        def create_link_with_content(content: str, type: ScLinkContentType):
            construction = ScConstruction()
            link_content = ScLinkContent(content, type)
            construction.generate_link(sc_type.CONST_NODE_LINK, link_content, 'link')
            link = generate_elements(construction)[0]
            return link
        

        timestamp = create_link_with_content(datetime.now().isoformat(), ScLinkContentType.STRING)
        weather_state = ScKeynodes.resolve(f"concept_weather_{status.lower()}", sc_type.CONST_NODE_CLASS)
        temp = create_link_with_content(temp, ScLinkContentType.FLOAT)
        hum = create_link_with_content(hum, ScLinkContentType.FLOAT)
        templ = ScTemplate()
        templ.triple(
            weather_state,
            sc_type.VAR_PERM_POS_ARC,
            weather
        )
        templ.quintuple(
            weather,
            sc_type.VAR_COMMON_ARC,
            timestamp,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_timestamp", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            weather,
            sc_type.VAR_COMMON_ARC,
            temp,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_temp", sc_type.CONST_NODE_NON_ROLE)
        )
        templ.quintuple(
            weather,
            sc_type.VAR_COMMON_ARC,
            hum,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes.resolve("nrel_hum", sc_type.CONST_NODE_NON_ROLE)
        )
        generate_by_template(templ)


        return None
        


    def edit_device_consequences(self, temp: float, temp_min: float, temp_max: float) -> None:
        templ = ScTemplate()
        templ.triple(
            ScKeynodes.resolve("concept_weather_depended_device", sc_type.VAR_NODE_CLASS),
            sc_type.VAR_PERM_POS_ARC,
            (sc_type.VAR_NODE_CLASS, "_device_class")
        )

        search_results = search_by_template(templ)
        if not search_results: return None
        devices_classes = []
        for result in search_results: devices_classes.append(result.get("_device_class"))

        for device in devices_classes:
            templ = ScTemplate()
            templ.quintuple(
                device,
                (sc_type.VAR_PERM_POS_ARC, "_arc1"),
                (sc_type.VAR_NODE, "_state"),
                (sc_type.VAR_PERM_POS_ARC, "_arc2"),
                ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
            )
            templ.triple(
                ScKeynodes.resolve("concept_temp_state", sc_type.CONST_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                "_state"
            )
            search_results = search_by_template(templ)
            for result in search_results:
                erase_elements(
                    result.get("_arc2"),
                    result.get("_arc1")
                )
            templ.quintuple(
                device,
                (sc_type.VAR_PERM_POS_ARC, "_arc3"),
                (sc_type.VAR_NODE, "_state"),
                (sc_type.VAR_PERM_POS_ARC, "_arc4"),
                ScKeynodes.resolve("rrel_causes_state", sc_type.CONST_NODE_ROLE)
            )
            templ.triple(
                ScKeynodes.resolve("concept_temp_state", sc_type.CONST_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                "_state"
            )
            search_results = search_by_template(templ)
            for result in search_results:
                erase_elements(
                    result.get("_arc4"),
                    result.get("_arc3")
                )

            if get_interval(temp_min, temp_max, temp) == 'normal': return None

            templ = ScTemplate()
            templ.quintuple(
                device,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve(f"concept_temp_state_{get_interval(temp_min, temp_max, temp)}", sc_type.VAR_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_causes_state", sc_type.CONST_NODE_ROLE)
            )

            generate_by_template(templ)
            templ = ScTemplate()
            templ.quintuple(
                ScKeynodes.resolve(f"concept_temp_state_{get_interval(temp_min, temp_max, temp)}", sc_type.VAR_NODE_CLASS),
                sc_type.VAR_PERM_POS_ARC,
                (sc_type.VAR_NODE, "_searched_state"),
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_is_opposite_to", sc_type.CONST_NODE_ROLE)
            )
            search_results = search_by_template(templ)
            opposite_state = search_results[0].get("_searched_state")
            templ = ScTemplate()
            templ.quintuple(
                device,
                sc_type.VAR_PERM_POS_ARC,
                opposite_state,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes.resolve("rrel_fixes_state", sc_type.CONST_NODE_ROLE)
            )
            generate_by_template(templ)

        return None









