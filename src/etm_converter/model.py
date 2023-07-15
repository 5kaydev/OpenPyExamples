import abc
import re
from dataclasses import dataclass

from etm_converter.converter_common import UIObject

DEBUG_INFO = True

PARAM_GET_SHEET = 'GetSheet'
PARAM_REQUEST_HEADER = 'RequestHeader'
PARAM_REQUEST_HEADER_STRING = 'RequestHeaderString'
PARAM_REQUEST_SHEET = 'RequestSheet'
PARAM_URL = 'URL'
PARAM_VALIDATION_SHEET = 'ValidationSheet'

RESPONSE_BODY_REGEXP = re.compile(r'response\s*body')
XPATH_SUBST_REGEX = re.compile(r"^(.*)\|\|(.*)$", re.IGNORECASE)

TAF_ACTION = 'action'
TAF_CLOSE_ALL = 'closeallbrowsers'
TAF_CREATE_KEYWORD = 'createkeyword'
TAF_DATABASE_TEST = 'databasetest'
TAF_DATA_ENTRY = 'enterdata'
TAF_DATA_ENTRY_CUSTOM = 'enterdatacustom'
TAF_GET_OBJECT_DATA = 'getobjectdata'
TAF_LAUNCH_AUT = 'launchaut'
TAF_OBJECT_ENABLED = 'objectenabled'
TAF_OBJECT_EXIST = 'objectexists'
TAF_OBJECT_HIDDEN = 'objecthidden'
TAF_OBJECT_NOT_ENABLED = 'objectnotenabled'
TAF_OBJECT_NOT_EXIST = 'objectnotexists'
TAF_OBJECT_NOT_HIDDEN = 'objectnothidden'
TAF_SHARED_STEP = 'sharedstep'
TAF_TAKE_SCREENSHOT = 'takescreenshot'
TAF_VALIDATION = 'validatedata'
TAF_WAIT = 'wait'
TAF_WAIT_FOR_OBJECT = 'waitforobject'
TAF_WEB_SERVICE = 'xmlwebservicetest'


def _remove_duplicates(input_str: str) -> str:
    if input_str:
        input_length = len(input_str)
        if input_length > 10:
            for rep in range(input_length // 2, 1, -1):
                if input_length % rep == 0:
                    substring = input_str[:input_length // rep]
                    if substring * rep == input_str:
                        return substring
    return input_str


class ScenarioSource(abc.ABC):
    @abc.abstractmethod
    def api_scenarios(self, big_request: bool) -> tuple[str]:
        """
        Generate scenarios from this source.
        :param big_request: true if requests must be generated in a separate request file.
        :return: A tuple of scenarios.
        """
        pass


@dataclass(frozen=True)
class APIScenario:
    name: str  # The scenario name
    outputs: tuple[tuple[str, str]] | None  # pairs (expression, value)
    request: str  # The scenario request
    request_header: str  # The request header
    request_type: str  # The request type
    response_code: str | None  # The response code
    url: str  # The scenario url
    variables: tuple[tuple[str, str]] | None  # pairs (expression, variable name)

    def _scenario_annotation(self) -> str:
        if self.name.startswith('S_'):
            return '@SmokeTest\n'
        if self.name.startswith('R_'):
            return '@RegressionTest\n'
        return ''

    def scenario(self, big_request: bool) -> str:

        if self.request_type == 'get':
            request_line = f'When I send a GET request to URL "{self.url}" with request header "{self.request_header}"'
        else:
            request_line = f'When I send a request to URL "{self.url}" with request header "{self.request_header}' \
                           + f'" and the following {self.request_type} ' \
                           + (f'request "{self.name}"' if big_request else f'body\n"""\n{self.request}\n"""')
        lines = [f'{self._scenario_annotation()}Scenario: {self.name}',
                 'Given I am a XMLWebservice client',
                 request_line]
        # Append validation of response status code
        if self.response_code is None:
            prefix = 'Then'
        else:
            prefix = 'And'
            lines.append(f'Then I validate that the Response Code should be {self.response_code}')
        # Append variable storage from get sheet
        if self.variables:
            if big_request:
                lines.append(f'{prefix} I store the {self.request_type} expressions in {self.name}')
                prefix = 'And'
            else:
                for expression, variable in self.variables:
                    lines.append(
                        f'{prefix} I store the value of the {self.request_type} path expression "{expression}" in variable "{variable}"')
                    prefix = 'And'
        # Append validations from validation sheet
        if self.outputs:
            if big_request:
                validations = False
                for expression, value in self.outputs:
                    if RESPONSE_BODY_REGEXP.search(expression.lower()):
                        lines.append(f'{prefix} I validate that the Response Body should be\n"""\n{value}\n"""')
                    else:
                        validations = True
                if validations:
                    lines.append(f'{prefix} I validate the {self.request_type} expressions in {self.name}')
            else:
                for expression, value in self.outputs:
                    if RESPONSE_BODY_REGEXP.search(expression.lower()):
                        line = f'{prefix} I validate that the Response Body should be\n"""\n{value}\n"""'
                    else:
                        clean_value = _remove_duplicates(value)
                        line = f'{prefix} I validate that the {self.request_type} path expression "{expression}" should be'
                        line = line + (
                            f' "{clean_value}"' if 'json' == self.request_type else f'\n"""\n{clean_value}\n"""')
                    lines.append(line)
                    prefix = 'And'
        return '\n'.join(lines)

    def request_data(self) -> list[str]:
        data = []
        if self.request_type != 'get':
            data.append(f'##KEY:{self.name}')
            data.append(self.request)
        if self.variables:
            data.append(f'##KEY:##STORE:{self.name}')
            for expression, variable in self.variables:
                data.append(f'Path:{expression}')
                data.append(variable)
        if self.outputs:
            validations = []
            for expression, value in self.outputs:
                if not RESPONSE_BODY_REGEXP.search(expression.lower()):
                    validations.append(f'Path:{expression}')
                    validations.append(_remove_duplicates(value))
            if validations:
                data.append(f'##KEY:##VALIDATE:{self.name}')
                data.extend(validations)
        return data

    def size(self) -> int:
        request_length = len(self.request) if self.request_type != 'get' else 0
        variable_length = sum(len(expression) + len(variable)
                              for expression, variable in self.variables) if self.variables else 0
        validation_length = sum(len(expression) + len(value)
                                for expression, value in self.outputs
                                if not RESPONSE_BODY_REGEXP.search(expression.lower())) if self.outputs else 0
        return 2 * (request_length + variable_length + validation_length)


@dataclass(frozen=True)
class APITest(ScenarioSource):
    scenarios: tuple[APIScenario]

    def api_scenarios(self, big_request: bool) -> tuple[str]:
        return tuple(scenario.scenario(big_request)
                     for scenario in self.scenarios)

    def request_data(self) -> list[str]:
        requests = []
        for scenario in self.scenarios:
            requests.extend(scenario.request_data())
        return requests

    def size(self) -> int:
        return sum(scenario.size()
                   for scenario in self.scenarios)


@dataclass(frozen=True)
class CreateKeywordScenario(ScenarioSource):
    keywords: tuple[tuple[str, str]]

    def api_scenarios(self, big_request: bool) -> tuple[str]:
        lines = ['Scenario: CreateKeywordScenario']
        prefix = 'When'
        for name, value in self.keywords:
            variable_name = '{' + name.replace('{', '').replace('}', '') + '}'
            lines.append(f'{prefix} I create a keyword with value "{value}" in variable "{variable_name}"')
            prefix = 'And'
        return ('\n'.join(lines),)


@dataclass(frozen=True)
class DatabaseTest(ScenarioSource):
    connection_string: str
    location: str
    query: str
    result_json: str

    def api_scenarios(self, big_request: bool) -> tuple[str]:
        return ()


@dataclass(frozen=True)
class SharedStepTest(ScenarioSource):
    keywords: tuple[tuple[str, str]]
    row_index: int

    def api_scenarios(self, big_request: bool) -> tuple[str]:
        pairs = [f'{name} = {value}' for name, value in self.keywords]
        pairs_str = ', '.join(pairs)
        return (f'# SharedStep on row {self.row_index + 1}: {pairs_str}',)


@dataclass(frozen=True)
class WaitScenario(ScenarioSource):
    time_in_seconds: int

    def api_scenarios(self, big_request: bool) -> tuple[str]:
        lines = ['Scenario: WaitScenario', '', f'When I wait for {self.time_in_seconds} seconds']
        return ('\n'.join(lines),)


def xpath_substitution(ui_object: UIObject, value: str) -> tuple[UIObject, str]:
    match = XPATH_SUBST_REGEX.search(value)
    if match and ui_object.xpath and '{}' in ui_object.xpath:
        new_ui_object = UIObject(ui_object.browser_title, ui_object.browser_url, ui_object.class_name,
                                 ui_object.descriptive_programming, ui_object.frame, ui_object.id,
                                 ui_object.inner_text, ui_object.name, ui_object.object_name,
                                 ui_object.recovery_scenario, ui_object.tag_name, ui_object.time_out,
                                 ui_object.type, ui_object.xpath.replace('{}', match.group(1)))
        return new_ui_object, match.group(2)
    else:
        return ui_object, value


class Action(abc.ABC):
    @abc.abstractmethod
    def generate(self, ui_objects_map):
        pass


@dataclass(frozen=True)
class ActionAction(Action):
    action: str
    object_name: str
    row_index: int

    def generate(self, ui_objects_map):
        ui_object, action = xpath_substitution(ui_objects_map[self.object_name], self.action)
        object_ref = ui_object.reference()
        debug_info = f'({self.row_index + 1},{self.object_name}) ' if DEBUG_INFO else ''
        return f'{debug_info}I execute the action "{action}" on object {object_ref}'


@dataclass(frozen=True)
class CloseAllBrowsersAction(Action):
    def generate(self, _):
        return 'I close all browsers'


@dataclass(frozen=True)
class CreateKeywordAction(Action):
    name: str
    value: str
    row_index: int

    def generate(self, _):
        debug_info = f'({self.row_index + 1}) ' if DEBUG_INFO else ''
        return f'{debug_info}I create a keyword with value "{self.value}" in variable "{self.name}"'


@dataclass(frozen=True)
class DataEntryAction(Action):
    object_name: str
    value: str
    row_index: int

    def generate(self, ui_objects_map):
        object_ref = ui_objects_map[self.object_name].reference()
        value = self.value.replace('\r\n', r'\r\n').replace('\n', r'\n')
        debug_info = f'({self.row_index + 1},{self.object_name}) ' if DEBUG_INFO else ''
        return f'{debug_info}I enter "{value}" in object {object_ref}'


@dataclass(frozen=True)
class GetObjectDataAction(Action):
    object_name: str
    value: str
    row_index: int

    def generate(self, ui_objects_map):
        object_ref = ui_objects_map[self.object_name].reference()
        debug_info = f'({self.row_index + 1},{self.object_name}) ' if DEBUG_INFO else ''
        return f'{debug_info}I get data from object {object_ref} in "{self.value}"'


@dataclass(frozen=True)
class LaunchAUTAction(Action):
    url: str

    def generate(self, _):
        return f'I launch the application at url "{self.url}"'


@dataclass(frozen=True)
class ObjectTestAction(Action):
    object_name: str
    state: str
    value: str
    row_index: int

    def generate(self, ui_objects_map):
        object_ref = ui_objects_map[self.object_name].reference()
        debug_info = f'({self.row_index + 1},{self.object_name}) ' if DEBUG_INFO else ''
        return f'{debug_info}I test that object {object_ref} {self.state} is "{self.value}"'


@dataclass(frozen=True)
class TakeScreenShotAction(Action):
    def generate(self, _):
        return 'I take a screenshot'


@dataclass(frozen=True)
class ValidationAction(Action):
    object_name: str
    value: str
    row_index: int

    def generate(self, ui_objects_map):
        ui_object, value = xpath_substitution(ui_objects_map[self.object_name], self.value)
        object_ref = ui_object.reference()
        value = value.replace('\r\n', r'\r\n').replace('\n', r'\n')
        debug_info = f'({self.row_index + 1},{self.object_name}) ' if DEBUG_INFO else ''
        return f'{debug_info}I validate that object {object_ref} has value "{value}"'


@dataclass(frozen=True)
class WaitAction(Action):
    time_in_seconds: int
    object_name: str = None
    state: str = None

    def generate(self, ui_objects_map):
        if self.object_name:
            object_ref = ui_objects_map[self.object_name].reference()
            debug_info = f'({self.object_name}) ' if DEBUG_INFO else ''
            return f'{debug_info}I wait for object {object_ref} state {self.state} for {self.time_in_seconds} seconds'
        return f'I wait for {self.time_in_seconds} seconds'


@dataclass(frozen=True)
class UITest(ScenarioSource):
    actions: tuple[Action]
    ui_objects_map: dict[str, UIObject]

    def api_scenarios(self, big_request: bool) -> tuple[str]:
        def assertion_func(action: Action) -> bool:
            return isinstance(action, ObjectTestAction) \
                or isinstance(action, ValidationAction)

        def prefix_func(current_state: str, is_assertion_action: bool, is_close_action: bool) -> str:
            if current_state == 'S':
                if is_close_action:
                    return 'Given {0}'
                else:
                    return '\nThen {0}' if is_assertion_action else '\nWhen {0}'
            elif current_state == 'A':
                return '\nThen {0}' if is_assertion_action or is_close_action else 'And {0}'
            else:
                return 'And {0}' if is_assertion_action or is_close_action else '\nWhen {0}'

        def state_func(current_state: str, is_assertion_action: bool, is_close_action: bool) -> str:
            if is_close_action:
                return current_state
            return 'V' if is_assertion_action else 'A'

        lines = ['Scenario: UI Test', '']
        state = 'S'
        for action in self.actions:
            action_line = action.generate(self.ui_objects_map)
            assertion_action = assertion_func(action)
            close_action = isinstance(action, CloseAllBrowsersAction)
            prefix = prefix_func(state, assertion_action, close_action)
            lines.append(prefix.format(action_line))
            state = state_func(state, assertion_action, close_action)
        return ('\n'.join(lines),)


def object_enabled_action_factory(object_name: str, value: str, row_index: int) -> ObjectTestAction:
    return ObjectTestAction(object_name, 'enabled state', value, row_index)


def object_exist_action_factory(object_name: str, value: str, row_index: int) -> ObjectTestAction:
    return ObjectTestAction(object_name, 'existence', value, row_index)


def object_hidden_action_factory(object_name: str, value: str, row_index: int) -> ObjectTestAction:
    return ObjectTestAction(object_name, 'hidden state', value, row_index)
