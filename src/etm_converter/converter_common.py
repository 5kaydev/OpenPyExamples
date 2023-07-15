import re
import sys
from dataclasses import dataclass

from etm_converter.excel_utils import Sheet

DEFAULT_WAIT_IN_SECONDS = 2
# regexp for substitution of values in api tests and create keyword actions
STRING_REGEXP = re.compile(r'^~string\("(.*)"\)$', re.IGNORECASE)
SUBSTRING1_REGEXP = re.compile(r'~csharp\(\s*"({[^{}]*})".substring\(\s*(\d+)\s*\)\)', re.IGNORECASE)
SUBSTRING2_REGEXP = re.compile(r'~csharp\(\s*"({[^{}]*})".substring\(\s*(\d+)\s*,\s*(\d+)\s*\)\)', re.IGNORECASE)

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
        envs = self.sheet.cell(row_index, self.header_map[THN_ENV])
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
    2. Check for substring functions given in csharp
    3. Add delimiter around remaining csharp
    4. Substitute the ~string("...") expressions
    :param value: The value to process
    :return: The processed value.
    """
    if value is None:
        return None
    lower = value.lower()
    if 'text(now()' in lower:
        return f'~concat[[{value}]]'
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
    return value
