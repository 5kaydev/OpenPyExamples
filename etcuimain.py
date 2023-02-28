import argparse
import os
import sys

import etmuitestconverter

parser = argparse.ArgumentParser(prog='etcuimain',
                                 description='Generate Gherkin test scenarios from excel files',
                                 usage='etcuimain input_dir output_dir ui_objects_filename')
parser.add_argument('input_dir')
parser.add_argument('output_dir')
parser.add_argument('ui_objects_filename')
args = parser.parse_args()
input_path = args.input_dir
output_path = args.output_dir
ui_objects_filename = args.ui_objects_filename
# input_path = '/home/viseem/src/specflow/XLSX_to_Specflow_Feature'
# output_path = '/home/viseem/src/specflow/XLSX_to_Specflow_Feature_Output'

ui_objects_map = etmuitestconverter.parse_ui_objects(os.path.join(input_path, ui_objects_filename))
if ui_objects_map is not None:
    print(ui_objects_map)
    with os.scandir(input_path) as input_dir:
        for entry in input_dir:
            if entry.is_file() and entry.name.endswith('.xlsx') and entry.name != ui_objects_filename:
                file_name = entry.name[:-5]
                print(entry.name)
                scenarios = etmuitestconverter.parse_scenarios(os.path.join(input_path, entry.name), ui_objects_map)
                print(scenarios)
                if None in scenarios:
                    print('An error happened while parsing {0}'.format(entry.name), file=sys.stderr)
                else:
                    os.makedirs(output_path, exist_ok=True)
                    feature_file = os.path.join(output_path, file_name + '.feature')
                    with open(feature_file, "w", encoding='UTF-8') as feature_file:
                        print(etmuitestconverter.feature(file_name, scenarios, ui_objects_map), file=feature_file)
