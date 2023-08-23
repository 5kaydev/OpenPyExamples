import re
import sys
from dataclasses import dataclass

from etm_converter.excel_utils import load_excel, Sheet, SpreadSheet

DEFAULT_WAIT_IN_SECONDS = 2
# regexp for substitution of values in api tests and create keyword actions
GUID_REGEXP = re.compile(r'~csharp\(\s*"?\s*Guid.NewGuid\(\).ToString\(\)\s*"?\s*\)', re.IGNORECASE)
NOW_REGEXP = re.compile(r'~csharp\(\s*DateTime.(Now|Today)(.*)ToString\("(.*)"\)\)', re.IGNORECASE)
PHONE_REGEXP = re.compile(r'~csharp\(return string.Format\(.*201275.*new Random\(\).Next\(1000\s*,\s*9999\)\);\)',
                          re.IGNORECASE)
STRING_REGEXP = re.compile(r'^~string\("(.*)"\)$', re.IGNORECASE)
SUBSTRING1_REGEXP = re.compile(r'~csharp\(\s*"({[^{}]*})".substring\(\s*(\d+)\s*\)\)', re.IGNORECASE)
SUBSTRING2_REGEXP = re.compile(r'~csharp\(\s*"({[^{}]*})".substring\(\s*(\d+)\s*,\s*(\d+)\s*\)\)', re.IGNORECASE)
TO_TITLE_CASE_REGEXP = re.compile(
    r'~csharp\(\s*CultureInfo\.CurrentCulture\.TextInfo\.ToTitleCase\(\s*"({[^{}]*})"\s*\)\s*\)\s*$',
    re.IGNORECASE)

CO_MODE = 'mode'
CO_TEMPLATE = 'template'
CO_TYPE = 'type'

COMMON_COLUMN_NAMES_SET = {CO_MODE, CO_TEMPLATE, CO_TYPE}

THN_CONDITION = 'conditional/flag'
THN_ENV = 'environment'
THN_OBJECT_NAME_1 = 'objectname1'
THN_RUN_TYPE = 'runtype'
THN_TEST_ACTION = 'testingactionfunctionality'
THN_TEST_CASE_NAME = 'testcasename'
THN_TIME_OUT = 'timeout'

TEST_COLUMN_NAMES_SET = {THN_RUN_TYPE, THN_ENV, THN_OBJECT_NAME_1, THN_TEST_ACTION, THN_TEST_CASE_NAME, THN_TIME_OUT}

UIO_BROWSER_TITLE = 'browsertitle'
UIO_BROWSER_URL = 'browserurl'
UIO_CLASS_NAME = 'classname'
UIO_DESCRIPTIVE_PROGRAMMING = 'descriptiveprogramming'
UIO_ID = 'id'
UIO_INNER_TEXT = 'innertext'
UIO_FRAME = 'frame'
UIO_NAME = 'name'
UIO_OBJECT_NAME = 'objectname'
UIO_RECOVERY_SCENARIO = 'recoveryscenario'
UIO_TAG_NAME = 'tagname'
UIO_TIME_OUT = 'timeout'
UIO_TYPE = 'type'
UIO_XPATH = 'xpath'

UIO_COLUMN_NAMES_SET = {UIO_BROWSER_TITLE, UIO_BROWSER_URL, UIO_CLASS_NAME,
                        UIO_DESCRIPTIVE_PROGRAMMING, UIO_FRAME, UIO_ID, UIO_INNER_TEXT,
                        UIO_NAME, UIO_OBJECT_NAME, UIO_RECOVERY_SCENARIO,
                        UIO_TAG_NAME, UIO_TIME_OUT, UIO_TYPE, UIO_XPATH}


@dataclass(frozen=True)
class CommonSheet:
    header_map: dict[str, int]
    sheet: Sheet

    def get_data(self, template: str, scenario_name: str) -> tuple[tuple[tuple[str, str]], tuple[tuple[str, str]]]:
        template = template.lower()
        scenario_name = scenario_name.lower()
        scenario_column = None
        for column_index in range(0, self.sheet.columns):
            header = self.sheet.cell(0, column_index)
            if header and scenario_name == header.lower():
                scenario_column = column_index
                break
        if scenario_column is None:
            return ((), ())
        outputs = []
        variables = []
        for row_index in range(1, self.sheet.rows):
            current_template = self.sheet.cell(row_index, self.header_map[CO_TEMPLATE])
            if current_template and template == current_template.lower():
                expression = self.sheet.cell(row_index, self.header_map[CO_TYPE])
                value = self.sheet.cell(row_index, scenario_column)
                if expression and value is not None:
                    new_pair = (expression, substitute_value(value))
                    mode = self.sheet.cell(row_index, self.header_map[CO_MODE])
                    if mode and 'get' == mode.lower():
                        variables.append(new_pair)
                    else:
                        outputs.append(new_pair)
        return (tuple(outputs), tuple(variables))


def create_common_sheet(sheet: Sheet) -> CommonSheet:
    header_map = {}
    for i in range(0, sheet.columns):
        cell_value = sheet.cell(0, i)
        if cell_value is not None:
            header = cell_value.lower()
            if header in COMMON_COLUMN_NAMES_SET:
                header_map[header] = i
    return CommonSheet(header_map, sheet)


@dataclass(frozen=True)
class TestDataSheet:
    header_map: dict[str, int]
    sheet: Sheet

    def action(self, row_index: int) -> str | None:
        return self.sheet.cell(row_index, self.header_map[THN_TEST_ACTION])

    def rows(self) -> int:
        return self.sheet.rows

    def name_value_pairs(self, row_index: int) -> tuple[tuple[str, str]]:
        inputs = []
        i = self.header_map[THN_OBJECT_NAME_1]
        while i < self.sheet.columns - 1:
            object_name = self.sheet.cell(row_index, i)
            value = self.sheet.cell(row_index, i + 1)
            if object_name is not None and value is not None:
                inputs.append((object_name, value))
            i += 2
        return tuple(inputs)

    def object_name1(self, row_index: int) -> str | None:
        return self.sheet.cell(row_index, self.header_map[THN_OBJECT_NAME_1])

    def object_value1(self, row_index: int):
        return self.sheet.cell(row_index, self.header_map[THN_OBJECT_NAME_1] + 1)

    def runnable(self, row_index: int) -> bool:
        run_type = self.sheet.cell(row_index, self.header_map[THN_RUN_TYPE])
        runnable = run_type and run_type.strip().lower() == 'g'
        envs = self.sheet.cell(row_index, self.header_map[THN_ENV]) if THN_ENV in self.header_map else None
        valid_env = envs is None or 'in1' in envs.lower()
        return runnable and valid_env

    def test_case_name(self, row_index: int) -> str | None:
        return self.sheet.cell(row_index, self.header_map[THN_TEST_CASE_NAME])


def create_test_data_sheet(sheet: Sheet) -> TestDataSheet:
    header_map = {}
    for i in range(0, sheet.columns):
        cell_value = sheet.cell(0, i)
        if cell_value is not None:
            header = cell_value.lower()
            if header in TEST_COLUMN_NAMES_SET:
                header_map[header] = i
    return TestDataSheet(header_map, sheet)


@dataclass(frozen=True)
class ParsingContext:
    spread_sheet: SpreadSheet
    common_sheet: CommonSheet
    sheet: TestDataSheet
    selector: str


def create_parsing_context(filename: str, selector: str) -> ParsingContext | None:
    print(f'Parsing UI Test file: {filename}', file=sys.stderr)
    spread_sheet = load_excel(filename)
    try:
        test_data = spread_sheet.sheet('TestData')
    except KeyError:
        print(f'No TestData sheet found in file {filename}', file=sys.stderr)
        return None
    sheet = create_test_data_sheet(test_data)
    try:
        common = spread_sheet.sheet('CommonSheet')
    except KeyError:
        common = None
    common_sheet = create_common_sheet(common) if common else None
    return ParsingContext(spread_sheet, common_sheet, sheet, selector)


@dataclass(frozen=True)
class UIObject:
    browser_title: str
    browser_url: str
    class_name: str
    descriptive_programming: str
    frame: str
    id: str
    inner_text: str
    name: str
    object_name: str
    recovery_scenario: str
    tag_name: str
    time_out: str
    type: str
    xpath: str

    def reference(self):
        return '("{0}","{1}","{2}","{3}","{4}")'.format(self.xpath or '',
                                                        self.tag_name or '',
                                                        self.class_name or '',
                                                        self.id or '',
                                                        self.inner_text or '')


@dataclass(frozen=True)
class RepositorySheet:
    header_map: dict[str, int]
    sheet: Sheet

    def rows(self) -> int:
        return self.sheet.rows

    def ui_object(self, row_index: int) -> UIObject | None:
        """
        Parses one ui object at the given row of this sheet
        :param row_index: The row index for the object to parse
        :return: A UIObject containing the data extracted from the row_index row of the sheet
        """

        def cell_value(column_name: str) -> str:
            return self.sheet.cell(row_index, self.header_map[column_name])

        object_name = cell_value(UIO_OBJECT_NAME)
        if object_name is None or object_name == '':
            print(f'WARNING: Missing Object Name on row {row_index}', file=sys.stderr)
            return None
        return UIObject(
            cell_value(UIO_BROWSER_TITLE),
            cell_value(UIO_BROWSER_URL),
            cell_value(UIO_CLASS_NAME),
            cell_value(UIO_DESCRIPTIVE_PROGRAMMING),
            cell_value(UIO_FRAME),
            cell_value(UIO_ID),
            cell_value(UIO_INNER_TEXT),
            cell_value(UIO_NAME),
            object_name.lower(),
            cell_value(UIO_RECOVERY_SCENARIO),
            cell_value(UIO_TAG_NAME),
            cell_value(UIO_TIME_OUT),
            cell_value(UIO_TYPE),
            cell_value(UIO_XPATH))


def create_repository_sheet(sheet: Sheet) -> RepositorySheet:
    header_map = {}
    for i in range(0, sheet.columns):
        cell_value = sheet.cell(0, i)
        if cell_value is not None:
            header = cell_value.lower()
            if header in UIO_COLUMN_NAMES_SET:
                header_map[header] = i
    return RepositorySheet(header_map, sheet)


def parse_time(time_string: str) -> int:
    """
    Parses the given string for a waiting time.
    :param time_string: The string to parse.
    :return: The wait time in seconds
    """
    if time_string is None:
        return DEFAULT_WAIT_IN_SECONDS
    try:
        return int(time_string)
    except ValueError:
        return DEFAULT_WAIT_IN_SECONDS


def substitute_value(value: str | None) -> str | None:
    """
    Substitution of values for api tests and create keyword actions
    1. Add the ~concat[[....]] around values containing potential concatenation.
    2. Generate ~guid for csharp guid function
    3. Check for substring functions given in csharp
    4. Substitute the ~string("...") expressions
    5. Substitute the value of ~email
    :param value: The value to process
    :return: The processed value.
    """
    if value is None:
        return None
    lower = value.lower()
    if 'text(now()' in lower:
        return f'~concat[[{value}]]'
    match = NOW_REGEXP.search(value)
    if match:
        adders = match.group(2)
        now_expr = '~now' \
                   + _parse_now('AddYears', 'y', adders) \
                   + _parse_now('AddMonths', 'm', adders) \
                   + _parse_now('AddDays', 'd', adders) \
                   + '{' + match.group(3) + '}'
        return re.sub(NOW_REGEXP, now_expr, value)
    match = PHONE_REGEXP.search(value)
    if match:
        phone = '201275~random{1000}'
        return re.sub(PHONE_REGEXP, phone, value)
    match = GUID_REGEXP.search(value)
    if match:
        return '~guid'
    match = SUBSTRING1_REGEXP.search(value)
    if match:
        exp = f'~substring({match.group(1)},{match.group(2)})'
        return SUBSTRING1_REGEXP.sub(exp, value)
    match = SUBSTRING2_REGEXP.search(value)
    if match:
        exp = f'~substring({match.group(1)},{match.group(2)},{match.group(3)})'
        return SUBSTRING2_REGEXP.sub(exp, value)
    match = STRING_REGEXP.search(value)
    if match:
        return match.group(1)
    match = TO_TITLE_CASE_REGEXP.search(value)
    if match:
        return f'~toTitleCase({match.group(1)})'
    if '~email' == lower:
        return 'bitbucket@geico.com'
    return value


def _parse_now(group: str, suffix: str, value: str) -> str:
    match = re.compile(group + r'\(\s*([^)]*)\s*\)').search(value)
    if match:
        try:
            count = int(match.group(1))
            if count == 0:
                return ''
            return ('+' if count > 0 else '') + str(count) + suffix
        except ValueError:
            return ''
    return ''
