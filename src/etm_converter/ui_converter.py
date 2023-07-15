import re
import sys
from typing import Callable

import etm_converter.model as model
from etm_converter import api_converter
from etm_converter.converter_common import THN_OBJECT_NAME_1, create_repository_sheet, create_test_data_sheet, \
    parse_time, substitute_value, TestDataSheet, UIObject
from etm_converter.excel_utils import load_excel, SpreadSheet

DEFAULT_WAIT_FOR_OBJECT_IN_SECONDS = 60
DEFAULT_DATA_REGEXP = re.compile(r"^~defaultdata\((.*)\)$", re.IGNORECASE)
LAUNCH_URL_REGEXP = re.compile(r"^\[(.*)\]$")
# states for the _locate_scenarios automaton
STATE_START = 0
STATE_CREATE_KEYWORD = 1
STATE_UI = 2

TEST_ASSERTIONS = (model.TAF_OBJECT_NOT_ENABLED, model.TAF_OBJECT_NOT_EXIST, model.TAF_OBJECT_NOT_HIDDEN,
                   model.TAF_OBJECT_ENABLED, model.TAF_OBJECT_EXIST, model.TAF_OBJECT_HIDDEN, model.TAF_VALIDATION)


def parse_ui_objects(filename: str) -> dict[str, UIObject] | None:
    """
    Parses the given Excel file into a map of UIObjects.

    :param filename: The name of the file to parse
    :return: A map of Object names to UIObject
    """
    try:
        print(f'Parsing UI Objects file: {filename}', file=sys.stderr)
        spread_sheet = load_excel(filename)
        return {ui_object.object_name: ui_object
                for ui_object in (repository_sheet.ui_object(row_index)
                                  for repository_sheet in (create_repository_sheet(spread_sheet.sheet(sheet_name))
                                                           for sheet_name in spread_sheet.sheet_names())
                                  for row_index in range(1, repository_sheet.rows()))
                if ui_object is not None}
    except Exception as e:
        print(e, file=sys.stderr)
        return None


def _locate_scenarios(sheet: TestDataSheet) -> list[tuple[int, int]]:
    """
    Identifies the various scenarios in the given sheet.
    :param sheet: The sheet containing the data
    :return: a list of pairs (start, end) of row indexes for each scenario

    Each XmlWebServiceTest is returned as a scenario
    Each DatabaseTest is returned as a scenario
    Out of UI scenarios, Consecutive CreateKeywords are returned as a scenario.
    The end of a UI scenario is reached when we have a close_all_browser action or the end of the sheet.
    """
    scenarios = []
    start = None
    state = STATE_START
    for row_index in range(1, sheet.rows()):
        testing_action = sheet.action(row_index).lower()
        if testing_action and sheet.runnable(row_index):
            if state == STATE_START:
                # start state: We check for one line scenarios and for start create keyword and start ui
                if testing_action == model.TAF_DATABASE_TEST or testing_action == model.TAF_WEB_SERVICE:
                    scenarios.append((row_index, row_index + 1))
                elif testing_action == model.TAF_CREATE_KEYWORD:
                    start = row_index
                    state = STATE_CREATE_KEYWORD
                else:
                    start = row_index
                    state = STATE_UI
            elif state == STATE_CREATE_KEYWORD:
                # create keyword state: we check for one line scenarios and start ui
                if testing_action == model.TAF_DATABASE_TEST or testing_action == model.TAF_WEB_SERVICE:
                    scenarios.append((start, row_index))
                    scenarios.append((row_index, row_index + 1))
                    start = None
                    state = STATE_START
                elif testing_action != model.CreateKeywordAction:
                    scenarios.append((start, row_index))
                    start = row_index
                    state = STATE_UI
            else:
                # ui state: we check for one line scenarios and end ui
                if testing_action == model.TAF_DATABASE_TEST or testing_action == model.TAF_WEB_SERVICE:
                    scenarios.append((start, row_index))
                    scenarios.append((row_index, row_index + 1))
                    start = None
                    state = STATE_START
                elif testing_action == model.TAF_CLOSE_ALL:
                    scenarios.append((start, row_index + 1))
                    start = None
                    state = STATE_START
    if state != STATE_START:
        scenarios.append((start, sheet.rows()))
    print(scenarios)
    return scenarios


def _validate_object(ui_objects_map: dict[str, UIObject], object_name: str, row_index: int) -> bool:
    """
    Validates that the given object name exists.
    :param ui_objects_map: The UIObject map
    :param object_name: The object name
    :param row_index: The row index where the object name came from
    :return: True if the object name exists in the map.
    """
    if object_name in ui_objects_map:
        return True
    print(f'ERROR: Object named {object_name} not found on row {row_index + 1}', file=sys.stderr)
    return False


def _process_boolean_value(val: str) -> str:
    """
    Normalize the string representation of boolean if the given is such a representation
    :param val: The input string value
    :return: A normalized boolean string representation or the initial value
    """
    lower = val.lower()
    return lower if lower == 'true' or lower == 'false' else val


def _parse_action(spread_sheet: SpreadSheet,
                  sheet: TestDataSheet,
                  row_index: int,
                  ui_objects_map: dict[str, UIObject]) -> tuple[model.ActionAction] | None:
    return tuple(model.ActionAction(action, object_name, row_index)
                 for object_name, action in _parse_name_value_pairs(sheet, row_index, ui_objects_map))


def _parse_close_all_browser(spread_sheet: SpreadSheet,
                             sheet: TestDataSheet,
                             row_index: int,
                             ui_objects_map: dict[str, UIObject]) -> model.CloseAllBrowsersAction:
    return model.CloseAllBrowsersAction()


def _parse_name_value_pairs(sheet: TestDataSheet,
                            row_index: int,
                            ui_objects_map: dict[str, UIObject]) -> tuple[tuple[str, str]]:
    inputs = []
    object_error = False
    for object_name, value in sheet.name_value_pairs(row_index):
        object_name = object_name.lower()
        inputs.append((object_name, _process_boolean_value(value)))
        if not _validate_object(ui_objects_map, object_name, row_index):
            object_error = True
    return () if object_error else tuple(inputs)


def _parse_create_keyword(spread_sheet: SpreadSheet,
                          sheet: TestDataSheet,
                          row_index: int,
                          ui_objects_map: dict[str, UIObject]) -> tuple[model.CreateKeywordAction] | None:
    return tuple(model.CreateKeywordAction(object_name, substitute_value(value), row_index)
                 for object_name, value in sheet.name_value_pairs(row_index))


def _parse_data_entry(spread_sheet: SpreadSheet,
                      sheet: TestDataSheet,
                      row_index: int,
                      ui_objects_map: dict[str, UIObject]) -> tuple[model.DataEntryAction] | None:
    return tuple(model.DataEntryAction(object_name, substitute_value(value), row_index)
                 for object_name, value in _parse_name_value_pairs(sheet, row_index, ui_objects_map))


def _parse_get_object_data(spread_sheet: SpreadSheet,
                           sheet: TestDataSheet,
                           row_index: int,
                           ui_objects_map: dict[str, UIObject]) -> tuple[model.GetObjectDataAction] | None:
    return tuple(model.GetObjectDataAction(object_name, value, row_index)
                 for object_name, value in _parse_name_value_pairs(sheet, row_index, ui_objects_map))


def _parse_launch_aut(spread_sheet: SpreadSheet,
                      sheet: TestDataSheet,
                      row_index: int,
                      ui_objects_map: dict[str, UIObject]) -> model.LaunchAUTAction | None:
    url = sheet.sheet.cell(row_index, sheet.header_map[THN_OBJECT_NAME_1] + 1)
    if url is None:
        print(f'ERROR: Missing url on LaunchAUT action on row {row_index + 1}', file=sys.stderr)
        return None
    else:
        match = LAUNCH_URL_REGEXP.search(url)
        url = match.group(1) if match else url
        return model.LaunchAUTAction(url)


def _parse_object_flags(sheet: TestDataSheet,
                        row_index: int,
                        ui_objects_map: dict[str, UIObject],
                        action_factory: Callable[[str, str, int], model.Action]) -> tuple[model.Action] | None:
    testing_action = sheet.action(row_index)
    negated = 'not' in testing_action.lower()
    actions = []
    error = False
    for object_name, value in _parse_name_value_pairs(sheet, row_index, ui_objects_map):
        if _validate_object(ui_objects_map, object_name, row_index):
            object_name = object_name.lower()
            flag = value is None or value == '' or 'true' == value.lower()
            if negated:
                flag = not flag
            actions.append(action_factory(object_name, str(flag).lower(), row_index))
        else:
            error = True
    return None if error else tuple(actions)


def _parse_object_enabled(spread_sheet: SpreadSheet,
                          sheet: TestDataSheet,
                          row_index: int,
                          ui_objects_map: dict[str, UIObject]) -> tuple[model.ObjectTestAction] | None:
    return _parse_object_flags(sheet, row_index, ui_objects_map, model.object_enabled_action_factory)


def _parse_object_exists(spread_sheet: SpreadSheet,
                         sheet: TestDataSheet,
                         row_index: int,
                         ui_objects_map: dict[str, UIObject]) -> tuple[model.ObjectTestAction] | None:
    return _parse_object_flags(sheet, row_index, ui_objects_map, model.object_exist_action_factory)


def _parse_object_hidden(spread_sheet: SpreadSheet,
                         sheet: TestDataSheet,
                         row_index: int,
                         ui_objects_map: dict[str, UIObject]) -> tuple[model.ObjectTestAction] | None:
    return _parse_object_flags(sheet, row_index, ui_objects_map, model.object_hidden_action_factory)


def _parse_take_screenshot(spread_sheet: SpreadSheet,
                           sheet: TestDataSheet,
                           row_index: int,
                           ui_objects_map: dict[str, UIObject]) -> model.TakeScreenShotAction:
    return model.TakeScreenShotAction()


def _process_validation_value(value: str) -> str:
    match = DEFAULT_DATA_REGEXP.search(value)
    if match:
        return match.group(1)
    if value.startswith('~') and '||' in value:
        return f'~or({value[1:]})'
    return value


def _parse_validation(spread_sheet: SpreadSheet,
                      sheet: TestDataSheet,
                      row_index: int,
                      ui_objects_map: dict[str, UIObject]) -> tuple[model.ValidationAction] | None:
    return tuple(
        model.ValidationAction(object_name, _process_validation_value(substitute_value(value)), row_index)
        for object_name, value in _parse_name_value_pairs(sheet, row_index, ui_objects_map))


def _parse_wait(spread_sheet: SpreadSheet,
                sheet: TestDataSheet,
                row_index: int,
                ui_objects_map: dict[str, UIObject]) -> model.WaitAction:
    time = parse_time(sheet.object_value1(row_index))
    return model.WaitAction(time)


def _parse_wait_for_object(spread_sheet: SpreadSheet,
                           sheet: TestDataSheet,
                           row_index: int,
                           ui_objects_map: dict[str, UIObject]) -> model.WaitAction:
    object_name = sheet.object_name1(row_index)
    if object_name is None:
        print(f'ERROR: Missing object name for wait for object action on row {row_index + 1}', file=sys.stderr)
        return None
    object_name = object_name.lower()
    if _validate_object(ui_objects_map, object_name, row_index):
        state = sheet.object_value1(row_index)
        state = state if state else 'existence'
        return model.WaitAction(DEFAULT_WAIT_FOR_OBJECT_IN_SECONDS, object_name, state)
    return None


ACTION_PARSERS = {model.TAF_ACTION: _parse_action,
                  model.TAF_CLOSE_ALL: _parse_close_all_browser,
                  model.TAF_CREATE_KEYWORD: _parse_create_keyword,
                  model.TAF_DATA_ENTRY: _parse_data_entry,
                  model.TAF_DATA_ENTRY_CUSTOM: _parse_data_entry,
                  model.TAF_GET_OBJECT_DATA: _parse_get_object_data,
                  model.TAF_LAUNCH_AUT: _parse_launch_aut,
                  model.TAF_OBJECT_ENABLED: _parse_object_enabled,
                  model.TAF_OBJECT_NOT_ENABLED: _parse_object_enabled,
                  model.TAF_OBJECT_EXIST: _parse_object_exists,
                  model.TAF_OBJECT_NOT_EXIST: _parse_object_exists,
                  model.TAF_OBJECT_HIDDEN: _parse_object_hidden,
                  model.TAF_OBJECT_NOT_HIDDEN: _parse_object_hidden,
                  model.TAF_TAKE_SCREENSHOT: _parse_take_screenshot,
                  model.TAF_VALIDATION: _parse_validation,
                  model.TAF_WAIT: _parse_wait,
                  model.TAF_WAIT_FOR_OBJECT: _parse_wait_for_object}


def _parse_scenario_create_keyword(spread_sheet: SpreadSheet,
                                   sheet: TestDataSheet,
                                   row_range: tuple[int, int]) -> model.CreateKeywordScenario | None:
    """
    :param spread_sheet: The SpreadSheet
    :param sheet: The test data sheet
    :param row_range: The range of rows for the scenario to parse in the test data sheet
    :return: A UITest object if successful or else None
    """

    keywords = []
    start, end = row_range
    for row_index in range(start, end):
        if sheet.runnable(row_index):
            keywords.extend(sheet.name_value_pairs(row_index))
    if len(keywords) > 0:
        processed_keywords = tuple((key, substitute_value(value))
                                   for key, value in keywords)
        return model.CreateKeywordScenario(processed_keywords)
    else:
        print(f'ERROR: No data specified in CreateKeyword actions on rows {start} to {end}', file=sys.stderr)
        return None


def _parse_scenario_ui(spread_sheet: SpreadSheet,
                       sheet: TestDataSheet,
                       row_range: tuple[int, int],
                       ui_objects_map: dict[str, UIObject]) -> model.UITest | None:
    """
    :param spread_sheet: The SpreadSheet
    :param sheet: The test data sheet
    :param row_range: The range of rows for the scenario to parse in the test data sheet
    :param ui_objects_map: The ui_objects map.
    :return: A UITest object if successful or else None
    """
    actions = []
    start, end = row_range
    for row_index in range(start, end):
        if sheet.runnable(row_index):
            testing_action = sheet.action(row_index)
            if testing_action is not None and testing_action.lower() in ACTION_PARSERS.keys():
                new_actions = ACTION_PARSERS[testing_action.lower()](spread_sheet, sheet, row_index, ui_objects_map)
                if new_actions is None:
                    return None
                if isinstance(new_actions, tuple):
                    actions.extend(new_actions)
                else:
                    actions.append(new_actions)
            else:
                print(f'ERROR: Unrecognized testing action {testing_action} on row {row_index + 1}', file=sys.stderr)
                return None
    return model.UITest(tuple(actions), ui_objects_map)


def _parse_scenario(spread_sheet: SpreadSheet,
                    sheet: TestDataSheet,
                    row_range: tuple[int, int],
                    ui_objects_map: dict[str, UIObject]) -> model.ScenarioSource | None:
    """
    :param spread_sheet: The SpreadSheet
    :param sheet: The test data sheet
    :param row_range: The range of rows for the scenario to parse in the test data sheet
    :param ui_objects_map: The ui_objects map.
    :return: A Scenario object if successful or else None
    """
    testing_action = sheet.action(row_range[0]).lower()
    if testing_action == model.TAF_DATABASE_TEST:
        return api_converter.parse_database_test(spread_sheet, sheet, row_range[0])
    if testing_action == model.TAF_WEB_SERVICE:
        return api_converter.parse_api_test(spread_sheet, sheet, row_range[0])
    if testing_action == model.TAF_CREATE_KEYWORD:
        return _parse_scenario_create_keyword(spread_sheet, sheet, row_range)
    return _parse_scenario_ui(spread_sheet, sheet, row_range, ui_objects_map)


def parse_file(filename: str, ui_objects_map: dict[str, UIObject]) -> tuple[model.ScenarioSource | None] | None:
    """
    # Parses the given Excel file into a tuple of Scenarios.
    #
    # :param filename: The name of the file to parse
    # :param ui_objects_map: The map of Object names to UIObject
    # :return: A tuple of Scenarios.
    """
    try:
        print(f'Parsing UI Test file: {filename}', file=sys.stderr)
        spread_sheet = load_excel(filename)
        try:
            test_data = spread_sheet.sheet('TestData')
        except KeyError:
            print(f'No sheet found in file {filename}', file=sys.stderr)
            return None
        sheet = create_test_data_sheet(test_data)
        return tuple((_parse_scenario(spread_sheet, sheet, row_range, ui_objects_map)
                      for row_range in _locate_scenarios(sheet)))
    except Exception as e:
        print(e, file=sys.stderr)
        return None
