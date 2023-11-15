import argparse
import re
from decimal import Decimal

from etm_converter.excel_utils import load_excel, SpreadSheet

NEG_REGEXP = re.compile(r'\^s*\((\d+)\)\s*$')
INTEGER_REGEXP = re.compile(r'^\s*(-?\d+)\s*$')


def pre_process(spread_sheet: SpreadSheet) -> None:
    for sheet_name in spread_sheet.sheet_names():
        sheet = spread_sheet.sheet(sheet_name)
        for row_index in range(0, sheet.rows):
            for column_index in range(0, sheet.columns):
                cell = sheet.cell(row_index, column_index)
                print(f'{row_index}-{column_index}: {cell}')
                match = NEG_REGEXP.search(cell)
                if match:
                    cell = '-' + match.group(1)
                    sheet.set_cell(row_index, column_index, cell)
                match = INTEGER_REGEXP.search(cell)
                if match:
                    cell = str(Decimal(match.group(1)) / Decimal(100))
                    sheet.set_cell(row_index, column_index, cell)
                print(f'{row_index}-{column_index}: {cell}')


def diff(spread_sheet1: SpreadSheet, spread_sheet2: SpreadSheet) -> None:
    for sheet_name in spread_sheet1.sheet_names():
        print(f'Sheet: {sheet_name}')
        sheet1 = spread_sheet1.sheet(sheet_name)
        try:
            sheet2 = spread_sheet2.sheet(sheet_name)
        except KeyError:
            print("Sheet not found in second file")
            continue
        if sheet1.rows != sheet2.rows or sheet1.columns != sheet2.columns:
            print(
                f'Expected dimensions differ. file1 ({sheet1.rows},{sheet1.columns}) file2 ({sheet2.rows},{sheet2.columns})')
            return
        for row_index in range(0, sheet1.rows):
            row_result = f'row {row_index + 1} |'
            for column_index in range(0, sheet1.columns):
                cell1 = sheet1.cell(row_index, column_index)
                cell2 = sheet2.cell(row_index, column_index)
                if (cell1 is None and cell2 is None) or (cell1 and cell2 and cell1 == cell2):
                    row_result += ' |'
                else:
                    row_result += f' {cell1}/{cell2} |'
            print(row_result)


def diff_main():
    parser = argparse.ArgumentParser(prog='exceldiff',
                                     description='Generate an excel diff report',
                                     usage='exceldiff file1 file2')
    parser.add_argument('file1')
    parser.add_argument('file2')
    args = parser.parse_args()
    spread_sheet1 = load_excel(args.file1)
    spread_sheet2 = load_excel(args.file2)
    pre_process(spread_sheet2)
    diff(spread_sheet1, spread_sheet2)


if __name__ == '__main__':
    diff_main()
