import json
import re
import sys

import etm_converter.model as model
from etm_converter.converter_common import create_test_data_sheet, parse_time, substitute_value, TestDataSheet
from etm_converter.excel_utils import load_excel, Sheet, SpreadSheet

# parameters for parsing database test
PARAM_DB_CONNECTION_STRING = 'DBConnectionString'
PARAM_DB_LOCATION = 'DBLocation'
PARAM_DB_QUERY = 'DBQuery'
PARAM_DB_VALIDATION = 'ValidationString'
DB_PARAMETERS = [PARAM_DB_CONNECTION_STRING, PARAM_DB_QUERY, PARAM_DB_LOCATION, PARAM_DB_VALIDATION]

"""Constants for elements to parse in the Excel file"""
DO_NOT_INCLUDE = 'DONOTINCLUDE'
TYPE_JSON_OPENING = 0
TYPE_JSON_CLOSING = 1
TYPE_JSON_FIELD = 2

RESPONSE_CODE_REGEXP = re.compile(r'response\s*code', re.IGNORECASE)


def _cell_value(cell: str, is_input: bool) -> str | None:
    if cell is None:
        return '' if is_input else None
    if cell == DO_NOT_INCLUDE:
        return None
    return cell


def _parse_create_keyword(spread_sheet: SpreadSheet,
                          sheet: TestDataSheet,
                          row_index: int) -> model.CreateKeywordScenario | None:
    keywords = sheet.name_value_pairs(row_index)
    if len(keywords) > 0:
        processed_keywords = tuple((key, substitute_value(value))
                                   for key, value in keywords)
        return model.CreateKeywordScenario(processed_keywords)
    else:
        print(f'ERROR: No data specified in CreateKeyword action on row {row_index + 1}', file=sys.stderr)
        return None


def _parse_get_input(request_sheet: Sheet) -> tuple[tuple[str, str]] | None:
    """
    Parses a get request sheet
    :param request_sheet: The sheet to parse
    :return: a tuple of pairs (scenario name, url) or None in case of error
    """
    url_row = None
    for row_index in range(1, request_sheet.rows):
        cell = request_sheet.cell(row_index, 0)
        if cell and 'url' == cell.lower():
            url_row = row_index
            break
    last_url = 0
    while last_url < request_sheet.columns - 1 and \
            request_sheet.cell(url_row, last_url + 1) and \
            'url' == request_sheet.cell(url_row, last_url + 1).lower():
        last_url = last_url + 1
    inputs = []
    invalid = False
    for column_index in range(last_url + 1, request_sheet.columns):
        scenario_name = request_sheet.cell(0, column_index)
        if scenario_name:
            url = request_sheet.cell(url_row, column_index)
            if url:
                inputs.append((scenario_name.lower(), url))
            else:
                print(f'ERROR: URL found in url request sheet {request_sheet.name} on column {column_index}',
                      file=sys.stderr)
                invalid = True
        else:
            print(
                f'WARNING: Missing scenario name in url request in sheet {request_sheet.name} on column {column_index}',
                file=sys.stderr)
    if invalid:
        return None
    if len(inputs) == 0:
        print(f'ERROR: No scenario found in sheet {request_sheet.name}', file=sys.stderr)
        return None
    return tuple(inputs)


def _locate_json(request_sheet: Sheet) -> tuple[int | None, int | None]:
    """
    determines the limits of the json request in a request sheet.
    :param request_sheet: The request sheet to parse
    :return: a pair of integers (opening_row, closing_row). The interval is inclusive
    """
    opening_row = None
    closing_row = None
    closing = None
    for row_index in range(0, request_sheet.rows):
        json_element = request_sheet.cell(row_index, 0)
        if json_element is not None:
            if opening_row is None and (json_element == '{' or json_element == '['):
                closing = '}' if json_element == '{' else ']'
                opening_row = row_index
            if json_element == closing:
                closing_row = row_index
    return opening_row, closing_row


def _json_row_type(json_template: str) -> int:
    if '{' in json_template or '[' in json_template:
        return TYPE_JSON_OPENING
    if '}' in json_template or ']' in json_template:
        return TYPE_JSON_CLOSING
    return TYPE_JSON_FIELD


def _substitute_json_template(json_template: str, value: str) -> str:
    template_regexp = re.compile('([^:]*):\\s*,$')
    match = template_regexp.search(json_template)
    if match:
        return f'{match.group(1)}: {value},'
    return json_template.replace('string', value.replace('"', '\\"'))


def _parse_json_input(request_sheet: Sheet) -> tuple[tuple[str, str]] | None:
    """
    Parses a json request sheet
    :param request_sheet: The sheet to parse
    :return: a tuple of pairs (scenario name, request body) or None in case of error
    """
    inputs = []
    opening_row, closing_row = _locate_json(request_sheet)
    if opening_row is None or closing_row is None:
        print(f'ERROR: Unable to delimit json request in sheet {request_sheet.name}', file=sys.stderr)
        return None
    invalid = False
    for column_index in range(1, request_sheet.columns):
        scenario_name = request_sheet.cell(0, column_index)
        if scenario_name:
            properties = []
            types = []
            for row_index in range(opening_row, closing_row + 1):
                json_template = request_sheet.cell(row_index, 0)
                input_value = _cell_value(request_sheet.cell(row_index, column_index), True)
                if json_template and input_value is not None:
                    current_type = _json_row_type(json_template)
                    types.append(current_type)
                    if current_type != TYPE_JSON_FIELD:
                        properties.append(json_template)
                    else:
                        value = substitute_value(input_value)
                        properties.append(_substitute_json_template(json_template, value))
            for index in range(0, len(properties) - 1):
                if (types[index] != TYPE_JSON_OPENING and types[index + 1] == TYPE_JSON_CLOSING):
                    properties[index] = properties[index].rstrip(',')
            json_body = '\n'.join(properties)
            try:
                parsed_json = json.loads(json_body)
                inputs.append((scenario_name.lower(), json_body))
            except Exception as e:
                print(f'ERROR: Unable to validate json request in sheet {request_sheet.name} on column {column_index}',
                      file=sys.stderr)
                print(e, file=sys.stderr)
                print(json_body, file=sys.stderr)
                print("********************************************************************************",
                      file=sys.stderr)
                invalid = True
        else:
            print(
                f'WARNING: Missing scenario name in json request in sheet {request_sheet.name} on column {column_index}',
                file=sys.stderr)
    if invalid:
        return None
    if len(inputs) == 0:
        print(f'ERROR: No scenario found in sheet {request_sheet.name}', file=sys.stderr)
        return None
    return tuple(inputs)


def _locate_xml(request_sheet: Sheet) -> tuple[int | None, int | None]:
    """
    determines the limits of the xml request in a request sheet.
    :param request_sheet: The request sheet to parse
    :return: a pair of integers (opening_row, closing_row). The interval is inclusive
    """
    opening_row = None
    closing_row = None
    for row_index in range(0, request_sheet.rows):
        xml_element = request_sheet.cell(row_index, 0)
        if xml_element is not None and xml_element.startswith('<'):
            if opening_row is None:
                opening_row = row_index
            else:
                closing_row = row_index
    return opening_row, closing_row


def _clean_tag(tag: str) -> str:
    return tag.replace('{', '').replace('}', '') if tag else tag


def _parse_xml_element(request_sheet: Sheet, row_index: int, column_index: int) -> str | None:
    input_value = _cell_value(request_sheet.cell(row_index, column_index), True)
    if input_value is None:
        return None
    start_tag = _clean_tag(request_sheet.cell(row_index, 0))
    end_tag = _clean_tag(request_sheet.cell(row_index, 1))
    if end_tag is None or end_tag == '':
        return start_tag
    return start_tag + substitute_value(input_value) + end_tag


def _parse_xml_input(request_sheet: Sheet) -> tuple[tuple[str, str]] | None:
    """
    Parses a xml request sheet
    :param request_sheet: The sheet to parse
    :return: a tuple of pairs (scenario name, request body) or None in case of error
    """
    inputs = []
    opening_row, closing_row = _locate_xml(request_sheet)
    if opening_row is None or closing_row is None:
        print(f'ERROR: Unable to delimit xml request in sheet {request_sheet.name}', file=sys.stderr)
        return None
    for column_index in range(2, request_sheet.columns):
        scenario_name = request_sheet.cell(0, column_index)
        if scenario_name:
            properties = []
            for row_index in range(opening_row, closing_row + 1):
                tag = _parse_xml_element(request_sheet, row_index, column_index)
                if tag is not None:
                    properties.append(tag)
            body = '\n'.join(properties)
            inputs.append((scenario_name.lower(), body))
        else:
            print(
                f'WARNING: Missing scenario name in xml request in sheet {request_sheet.name} on column {column_index}',
                file=sys.stderr)
    if len(inputs) == 0:
        print(f'ERROR: No scenario found in sheet {request_sheet.name}', file=sys.stderr)
        return None
    return tuple(inputs)


INPUT_PARSERS = {'get': _parse_get_input, 'Json': _parse_json_input, 'XMLTagNamesStart': _parse_xml_input}
INPUT_TYPES = {'get': 'get', 'Json': 'json', 'XMLTagNamesStart': 'xml'}


def _parse_output(sheet: Sheet) -> dict[str, tuple[tuple[str, str]]]:
    """
    Parses and output sheet or a get sheet
    :param sheet: The sheet to parse
    :return: A map of scenario name -> (expression, value)
    """
    outputs = {}
    for column_index in range(1, sheet.columns):
        scenario_name = sheet.cell(0, column_index)
        if scenario_name:
            properties = []
            for row_index in range(1, sheet.rows):
                expression = sheet.cell(row_index, 0)
                output_value = _cell_value(sheet.cell(row_index, column_index), False)
                if expression and output_value is not None:
                    properties.append((expression, substitute_value(output_value)))
            outputs[scenario_name.lower()] = tuple(properties)
    return outputs


def _parse_url(parameters: dict[str, str], row_index: int, size: int) -> tuple[str] | None:
    if model.PARAM_URL not in parameters or parameters[model.PARAM_URL] == "":
        print(f'ERROR: URL parameter missing on row {row_index + 1}', file=sys.stderr)
        return None
    url_parameter = parameters[model.PARAM_URL].strip('\n\r ')
    urls = tuple(url.strip() for url in url_parameter.split(','))
    actual_size = len(urls)
    if actual_size != 1 and actual_size != size:
        print(f'ERROR: Wrong number of urls on row {row_index + 1} Expected {size} but got {actual_size}',
              file=sys.stderr)
        return None
    return urls


def _parse_request_header_string(parameters: dict[str, str], row_index: int) -> dict[str, str]:
    keys = {'accept', 'authorization', 'content-type', 'returnoutputtype', 'verb'}
    pairs = {}
    try:
        header_pairs = json.loads(parameters[model.PARAM_REQUEST_HEADER_STRING])
        for pair in header_pairs:
            if pair['Key'] and pair['Key'].lower() in keys:
                pairs[pair['Key'].lower()] = pair['Value']
        return pairs
    except Exception:
        print(f'WARNING: Unable to parse RequestHeaderString on row {row_index + 1}')
        return {}


def _parse_request_header(parameters: dict[str, str], row_index: int) -> str | None:
    if model.PARAM_REQUEST_HEADER not in parameters or parameters[model.PARAM_REQUEST_HEADER] == "":
        print(f'ERROR: RequestHeader parameter missing on row {row_index + 1}', file=sys.stderr)
        return None
    header_parameter = parameters[model.PARAM_REQUEST_HEADER]
    header_regexp = re.compile(r'.*:\s*(.*)')
    match = header_regexp.search(header_parameter)
    if match:
        fields = _parse_request_header_string(parameters, row_index)
        return f"(accept={fields.get('accept', '')},authorization={fields.get('authorization', 'null')},content-type={fields.get('content-type', '')},returnoutputtype={fields.get('returnoutputtype', '')},sourcesystemidentifier={match.group(1)},verb={fields.get('verb', '')})"
    else:
        return header_parameter


def _parse_request_type(request_sheet: Sheet) -> str:
    for row_index in range(1, request_sheet.rows):
        cell = request_sheet.cell(row_index, 0)
        if cell and 'url' == cell.lower():
            return 'get'
    return request_sheet.cell(0, 0)


def parse_api_test(spread_sheet: SpreadSheet,
                   sheet: TestDataSheet,
                   row_index: int) -> model.APITest | None:
    name = f'{row_index:0>2}'
    parameters = {name: value for name, value in sheet.name_value_pairs(row_index)}
    try:
        request_sheet = spread_sheet.sheet(parameters[model.PARAM_REQUEST_SHEET])
        validation_sheet = spread_sheet.sheet(parameters[model.PARAM_VALIDATION_SHEET]) \
            if model.PARAM_VALIDATION_SHEET in parameters else None
        get_sheet = spread_sheet.sheet(parameters[model.PARAM_GET_SHEET]) \
            if model.PARAM_GET_SHEET in parameters else None
    except KeyError:
        print(f'ERROR: Get, Request or Validation sheet not found on row {row_index + 1}', file=sys.stderr)
        return None
    request_type = _parse_request_type(request_sheet)
    if request_type not in INPUT_PARSERS.keys():
        print(
            f'ERROR: Unknown request type found request sheet {parameters[model.PARAM_REQUEST_SHEET]}',
            file=sys.stderr)
        return None
    inputs = INPUT_PARSERS[request_type](request_sheet)
    outputs = _parse_output(validation_sheet) if validation_sheet else None
    variables = _parse_output(get_sheet) if get_sheet else None
    if inputs is None:
        return None
    if request_type == 'get':
        urls = tuple(url for name, url in inputs)
    else:
        urls = _parse_url(parameters, row_index, len(inputs))
    request_header = _parse_request_header(parameters, row_index)
    if urls is None or request_header is None:
        return None
    scenarios = []
    for i in range(0, len(inputs)):
        input_name, request = inputs[i]
        sc_name = re.sub(r'\s', '_', f'{name}_{input_name}')
        if outputs and input_name in outputs:
            sc_response_code = None
            filtered_outputs = []
            for expression, value in outputs[input_name]:
                if RESPONSE_CODE_REGEXP.search(expression.lower()):
                    sc_response_code = value
                else:
                    filtered_outputs.append((expression, value))
            sc_outputs = tuple(filtered_outputs)
        else:
            sc_outputs = None
            sc_response_code = None
            print(f'WARNING: No validation for scenario {input_name}', file=sys.stderr)
        sc_url = urls[i] if len(urls) > 1 else urls[0]
        sc_variables = variables[input_name] if variables and input_name in variables else None
        scenarios.append(
            model.APIScenario(sc_name, sc_outputs, request, request_header, INPUT_TYPES[request_type], sc_response_code,
                              sc_url, sc_variables))
    return model.APITest(tuple(scenarios))


def parse_database_test(spread_sheet: SpreadSheet,
                        sheet: TestDataSheet,
                        row_index: int) -> model.DatabaseTest | None:
    params = {name: value for name, value in sheet.name_value_pairs(row_index)}
    for param_name in DB_PARAMETERS:
        param_value = params[param_name]
        print(f'DB param {param_name} = {param_value}')
        if not param_value:
            print(f'ERROR: Missing {param_name} for database test on row {row_index + 1}',
                  file=sys.stderr)
            return None
    return model.DatabaseTest(params[PARAM_DB_CONNECTION_STRING], params[PARAM_DB_LOCATION], params[PARAM_DB_QUERY],
                              params[PARAM_DB_VALIDATION])


def _parse_shared_step(spread_sheet: SpreadSheet,
                       sheet: TestDataSheet,
                       row_index: int) -> model.SharedStepTest:
    keywords = sheet.name_value_pairs(row_index)
    return model.SharedStepTest(keywords, row_index)


def _parse_wait_scenario(spread_sheet: SpreadSheet,
                         sheet: TestDataSheet,
                         row_index: int) -> model.WaitScenario:
    time = parse_time(sheet.object_value1(row_index))
    return model.WaitScenario(time)


TEST_PARSERS = {model.TAF_CREATE_KEYWORD: _parse_create_keyword,
                model.TAF_DATABASE_TEST: parse_database_test,
                model.TAF_SHARED_STEP: _parse_shared_step,
                model.TAF_WAIT: _parse_wait_scenario,
                model.TAF_WEB_SERVICE: parse_api_test}


def _parse_test(spread_sheet: SpreadSheet, sheet: TestDataSheet,
                row_index: int) -> model.ScenarioSource | None:
    testing_action = sheet.action(row_index)
    if testing_action.lower() in TEST_PARSERS.keys():
        return TEST_PARSERS[testing_action.lower()](spread_sheet, sheet, row_index)
    else:
        print(f'ERROR: Unrecognized testing action {testing_action} on row {row_index}', file=sys.stderr)
        return None


def parse_file(filename: str) -> tuple[model.ScenarioSource | None] | None:
    """
    Parses the tests in the given workbook
    :param filename: The file name
    :return: A tuple of ScenarioSource or None in case of error
    """
    try:
        print(f'Parsing API test file: {filename}', file=sys.stderr)
        spread_sheet = load_excel(filename)
        try:
            test_data = spread_sheet.sheet('TestData')
        except KeyError:
            print(f'ERROR: No TestData sheet found in file {filename}', file=sys.stderr)
            return None
        sheet = create_test_data_sheet(test_data)
        tests = tuple(_parse_test(spread_sheet, sheet, row_index)
                      for row_index in range(1, sheet.rows())
                      if sheet.action(row_index) and sheet.runnable(row_index))
        return None if None in tests else tests
    except Exception as e:
        print(f'ERROR: Exception while parsing API test file: {filename}', file=sys.stderr)
        print(e, file=sys.stderr)
        return None
