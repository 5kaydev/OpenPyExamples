import argparse
import os

import etmtestconverter

parser = argparse.ArgumentParser(prog='etcmain',
                                 description='Generate Gherkin test scenarios from excel files',
                                 usage='etcmain input_dir output_dir')
parser.add_argument('input_dir')
parser.add_argument('output_dir')
args = parser.parse_args()
input_path = args.input_dir
output_path = args.output_dir
# input_path = '/home/viseem/src/specflow/XLSX_to_Specflow_Feature'
# output_path = '/home/viseem/src/specflow/XLSX_to_Specflow_Feature_Output'
with os.scandir(input_path) as input_dir:
    for entry in input_dir:
        if entry.is_file() and entry.name.endswith('.xlsx'):
            file_name = entry.name[:-5]
            for testcase in etmtestconverter.parse_workbook(os.path.join(input_path, entry.name)):
                if testcase is not None:
                    testcase_dir = os.path.join(output_path, file_name)
                    os.makedirs(testcase_dir, exist_ok=True)
                    print(file_name, testcase.name)
                    feature_file = os.path.join(testcase_dir, testcase.name + '.feature')
                    with open(feature_file, "w", encoding='UTF-8') as feature_file:
                        print(testcase.feature(), file=feature_file)
