import json
import re
import sys

import etm_converter.model as model
from etm_converter.converter_common import create_parsing_context, parse_time, substitute_value, ParsingContext
from etm_converter.excel_utils import Sheet

# parameters for parsing database test
PARAM_DB_CONNECTION_STRING = 'dbconnectionstring'
PARAM_DB_LOCATION = 'dblocation'
PARAM_DB_QUERY = 'dbquery'
PARAM_TEST_DB_CONNECTION_STRING = 'testdbconnectionstring'
PARAM_DB_VALIDATION = 'validationstring'
DB_CONNECTION_REGEX = re.compile(r'\s*\[([^\[\]]*)\]\s*')

"""Constants for elements to parse in the Excel file"""
DO_NOT_INCLUDE = 'DONOTINCLUDE'
TYPE_JSON_OPENING = 0
TYPE_JSON_CLOSING = 1
TYPE_JSON_FIELD = 2

JSON_FIELD_REGEXP = re.compile(r'"([A-Z])([^"]*)":')
RESPONSE_CODE_REGEXP = re.compile(r'response\s*code', re.IGNORECASE)


def _cell_value(cell: str, is_input: bool) -> str | None:
    if cell is None:
        return '' if is_input else None
    if cell == DO_NOT_INCLUDE:
        return None
    return cell


def _parse_create_keyword(parsing_context: ParsingContext,
                          row_index: int) -> model.CreateKeywordScenario | None:
    keywords = parsing_context.sheet.name_value_pairs(row_index)
    if len(keywords) > 0:
        processed_keywords = tuple((key, substitute_value(value))
                                   for key, value in keywords)
        return model.CreateKeywordScenario(processed_keywords)
    else:
        print(f'ERROR: No data specified in CreateKeyword action on row {row_index + 1}', file=sys.stderr)
        return None


def _parse_get_input(parameters: dict[str, str], request_sheet: Sheet) -> tuple[tuple[str, str]] | None:
    """
    Parses a get request sheet
    :param request_sheet: The sheet to parse
    :return: a tuple of pairs (scenario name, url) or None in case of error
    """
    request_header = parameters[model.PARAM_REQUEST_HEADER]
    url_param = parameters.get(model.PARAM_URL, None)
    if request_header and 'get' == request_header.lower() and url_param:
        inputs = []
        for column_index in range(1, request_sheet.columns):
            scenario_name = request_sheet.cell(0, column_index)
            if scenario_name:
                inputs.append((scenario_name.lower(), url_param))
    else:
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
    if 'rawstring' in json_template:
        return json_template.replace('rawstring', value)
    if 'string' in json_template:
        return json_template.replace('string', value.replace('"', '\\"'))
    if 'boolean' in json_template:
        return json_template.replace('boolean', value)
    last_number_index = json_template.rfind('number')
    if last_number_index >= 0:
        return json_template[:last_number_index] + value + json_template[last_number_index + len('number'):]
    return json_template


def _cleanup_json_template(json_template: str) -> str:
    if json_template:
        json_template = json_template.replace('String', 'string').replace('\u00a0', ' ')
        if '"enabjled":' in json_template:
            return json_template.replace('"enabjled":', '"enabled":')
        match = JSON_FIELD_REGEXP.search(json_template)
        if match:
            sub = f'"{match.group(1).lower()}{match.group(2)}":'
            return re.sub(JSON_FIELD_REGEXP, sub, json_template)
        if '"vin": ""' in json_template:
            return json_template.replace('"vin": ""', '"vin": "string"')
        if 'occurrenceDateRange:' in json_template:
            return json_template.replace('occurrenceDateRange:', '"occurrenceDateRange":')
        if 'salesGateway:' in json_template:
            return json_template.replace('salesGateway:', '"salesGateway":')
        if 'sessionId:' in json_template:
            return json_template.replace('sessionId:', '"sessionId":')
        if 'trackingKeys:' in json_template:
            return json_template.replace('trackingKeys:', '"trackingKeys":')
        if '"minimum": string"' in json_template:
            return json_template.replace('"minimum": string"', '"minimum": string')
        if 'registrationInfo:' in json_template:
            return json_template.replace('registrationInfo:', '"registrationInfo":')
    return json_template


def _parse_json_input(parameters: dict[str, str], request_sheet: Sheet) -> tuple[tuple[str, str]] | None:
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
                json_template = _cleanup_json_template(request_sheet.cell(row_index, 0))
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


def _parse_xml_input(parameters: dict[str, str], request_sheet: Sheet) -> tuple[tuple[str, str]] | None:
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


def _parse_request_type(parameters: dict[str, str], request_sheet: Sheet) -> str:
    for row_index in range(1, request_sheet.rows):
        cell = request_sheet.cell(row_index, 0)
        if cell and 'url' == cell.lower():
            return 'get'
    request_header = parameters[model.PARAM_REQUEST_HEADER]
    url = parameters.get(model.PARAM_URL, None)
    if request_header and 'get' == request_header.lower() and url:
        return 'get'
    return request_sheet.cell(0, 0)


def _apply_common_sheet(parsing_context: ParsingContext,
                        template: str,
                        inputs: tuple[tuple[str, str]],
                        outputs: dict[str, tuple[tuple[str, str]]],
                        variables: dict[str, tuple[tuple[str, str]]]) -> None:
    if parsing_context.common_sheet:
        for i in range(0, len(inputs)):
            input_name = inputs[i][0]
            existing_outputs = outputs[input_name] if input_name in outputs else ()
            existing_variables = variables[input_name] if input_name in variables else ()
            common_outputs, common_variables = parsing_context.common_sheet.get_data(template, input_name)
            new_outputs = []
            new_outputs.extend(existing_outputs)
            new_outputs.extend(common_outputs)
            outputs[input_name] = tuple(new_outputs)
            new_variables = []
            new_variables.extend(existing_variables)
            new_variables.extend(common_variables)
            variables[input_name] = tuple(new_variables)


def _transform_scenarios(parsing_context: ParsingContext, scenarios: [model.APIScenario]) -> [model.APIScenario]:
    """
    Transform the scenarios based on the selector
    :param parsing_context: The parsing context
    :param scenarios: The scenarios to transform
    :return: The transformed scenarios.
    In the case of SAPI, it replaces RequestHeaders and add a Default host key in urls.
    """
    selector = parsing_context.selector.lower() if parsing_context.selector else None
    if selector and 'sapi' in selector:
        variable_names = ('{partitionKey}', '{retentionKey}', '{sessionId}', '{versionId}')
        new_scenarios = []
        for scenario in scenarios:
            header_flag = False
            request_flag = False
            url_flag = False
            var_flag = False
            # Replacing request headers get with SAPIGET, post with SAPIPOST and, postcwb by SAPIPOSTCWB
            if scenario.request_header.lower() == 'get':
                request_header = 'SAPIGET'
                header_flag = True
            if scenario.request_header.lower() == 'post':
                request_header = 'SAPIPOST'
                header_flag = True
            if scenario.request_header.lower() == 'postcwb':
                request_header = 'SAPIPOSTCWB'
                header_flag = True
            # Replacing double braced variables in request
            request = scenario.request
            for variable_name in variable_names:
                double_braced = '{' + variable_name + '}'
                if double_braced in request:
                    request = request.replace(double_braced, variable_name)
                    request_flag = True
            # Default url app host to the parsing context
            if '[' not in scenario.url:
                url = f'[{parsing_context.selector.upper()}]{scenario.url}'
                url_flag = True
            # Replacing double braced variables in variables
            variables = []
            for expression, variable in scenario.variables:
                var_tuple = None
                for variable_name in variable_names:
                    double_braced = '{' + variable_name + '}'
                    if double_braced in variable:
                        var_tuple = (expression, variable.replace(double_braced, variable_name))
                        var_flag = True
                variables.append((expression, variable) if var_tuple is None else var_tuple)
            if header_flag or request_flag or url_flag or var_flag:
                new_scenarios.append(
                    model.APIScenario(scenario.name,
                                      scenario.outputs,
                                      request if request_flag else scenario.request,
                                      request_header if header_flag else scenario.request_header,
                                      scenario.request_type,
                                      scenario.response_code,
                                      url if url_flag else scenario.url,
                                      tuple(variables) if var_flag else scenario.variables))
            else:
                new_scenarios.append(scenario)
        return new_scenarios
    return scenarios


def parse_api_test(parsing_context: ParsingContext,
                   row_index: int) -> model.APITest | None:
    name = f'{row_index:0>2}'
    parameters = {name: value for name, value in parsing_context.sheet.name_value_pairs(row_index)}
    try:
        request_sheet = parsing_context.spread_sheet.sheet(parameters[model.PARAM_REQUEST_SHEET])
        validation_sheet = parsing_context.spread_sheet.sheet(parameters[model.PARAM_VALIDATION_SHEET]) \
            if model.PARAM_VALIDATION_SHEET in parameters else None
        get_sheet = parsing_context.spread_sheet.sheet(parameters[model.PARAM_GET_SHEET]) \
            if model.PARAM_GET_SHEET in parameters else None
    except KeyError as e:
        print(f'ERROR: Get, Request or Validation sheet {e.args[0]} not found on row {row_index + 1}', file=sys.stderr)
        return None
    request_type = _parse_request_type(parameters, request_sheet)
    if request_type not in INPUT_PARSERS.keys():
        print(
            f'ERROR: Unknown request type found request sheet {parameters[model.PARAM_REQUEST_SHEET]}',
            file=sys.stderr)
        return None
    inputs = INPUT_PARSERS[request_type](parameters, request_sheet)
    outputs = _parse_output(validation_sheet) if validation_sheet else {}
    variables = _parse_output(get_sheet) if get_sheet else {}
    _apply_common_sheet(parsing_context, parameters[model.PARAM_REQUEST_SHEET], inputs, outputs, variables)
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
                    expression = expression.replace('"', '\'') if request_type == 'Json' else expression
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
    return model.APITest(tuple(_transform_scenarios(parsing_context, scenarios)))


def parse_database_test(parsing_context: ParsingContext,
                        row_index: int) -> model.DatabaseTest | None:
    params = {name.lower(): value for name, value in parsing_context.sheet.name_value_pairs(row_index)}
    connection = parsing_context.selector \
        if parsing_context.selector \
        else parsing_context.sheet.object_name1()
    query = params.get(PARAM_DB_QUERY, None)
    validation = params.get(PARAM_DB_VALIDATION, None)
    if connection and query and validation:
        query = query.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        try:
            values = json.loads(validation)
        except Exception as e:
            print(f'ERROR: Exception while parsing validation for database test on row {row_index + 1}',
                  file=sys.stderr)
            print(e, file=sys.stderr)
            print(validation, file=sys.stderr)
            return None
        return model.DatabaseTest(connection, query, values)
    else:
        print(f'ERROR: Missing parameter for database test on row {row_index + 1}', file=sys.stderr)
        return None


def parse_shared_step(parsing_context: ParsingContext,
                      row_index: int) -> model.SharedStepTest:
    parameters = {name: value for name, value in parsing_context.sheet.name_value_pairs(row_index)}
    project_name = parameters['ProjectName']
    test_case_name = parameters['TestCaseName']
    if not (project_name and test_case_name):
        print(f'ERROR: Missing parameters for SharedStep on row {row_index + 1}',
              file=sys.stderr)
        return None
    return model.SharedStepTest(project_name.lower(), test_case_name.lower(), row_index)


def _parse_wait_scenario(parsing_context: ParsingContext,
                         row_index: int) -> model.WaitScenario:
    time = parse_time(parsing_context.sheet.object_value1(row_index))
    return model.WaitScenario(time)


TEST_PARSERS = {model.TAF_CREATE_KEYWORD: _parse_create_keyword,
                model.TAF_DATABASE_TEST: parse_database_test,
                model.TAF_SHARED_STEP: parse_shared_step,
                model.TAF_WAIT: _parse_wait_scenario,
                model.TAF_WEB_SERVICE: parse_api_test}


def _parse_test(parsing_context: ParsingContext,
                row_index: int) -> model.ScenarioSource | None:
    testing_action = parsing_context.sheet.action(row_index).lower()
    if testing_action in TEST_PARSERS.keys():
        return TEST_PARSERS[testing_action](parsing_context, row_index)
    else:
        print(f'ERROR: Unrecognized testing action {testing_action} on row {row_index}', file=sys.stderr)
        return None


def parse_file(filename: str, selector: str) -> tuple[model.ScenarioSource | None] | None:
    """
    Parses the tests in the given workbook
    :param filename: The file name
    :param selector: The optional selector
    :return: A tuple of ScenarioSource or None in case of error
    """
    try:
        parsing_context = create_parsing_context(filename, selector)
        tests = tuple(_parse_test(parsing_context, row_index)
                      for row_index in range(1, parsing_context.sheet.rows())
                      if parsing_context.sheet.action(row_index) and parsing_context.sheet.runnable(row_index))
        return None if None in tests else tests
    except Exception as e:
        print(f'ERROR: Exception while parsing API test file: {filename}', file=sys.stderr)
        print(e, file=sys.stderr)
        return None
