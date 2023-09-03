import argparse
import os
import sys

from etm_converter import utils
from etm_converter.generator import feature_generator_factory, generate_feature
from etm_converter.ui_converter import parse_file, parse_ui_objects


def ui_main():
    parser = argparse.ArgumentParser(prog='etcui',
                                     description='Generate Gherkin test scenarios from excel files',
                                     usage='etcui input_dir output_dir ui_objects_filename [selector]')
    parser.add_argument('input_dir')
    parser.add_argument('output_dir')
    parser.add_argument('ui_objects_filename')
    parser.add_argument('selector', nargs='?')
    args = parser.parse_args()
    input_path = args.input_dir
    output_path = args.output_dir
    ui_objects_filename = args.ui_objects_filename
    selector = args.selector
    success_path = os.path.join(input_path, 'success')
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(success_path, exist_ok=True)
    ui_objects_map = parse_ui_objects(os.path.join(input_path, ui_objects_filename))
    if ui_objects_map is not None:
        #    print(ui_objects_map)
        paths = utils.scan_dir(input_path, '*.xlsx')
        paths.sort()
        feature_generator = feature_generator_factory(input_path, selector)
        for path in paths:
            if path.name != ui_objects_filename:
                file_name = path.name[:-5]
                # print(entry.name)
                input_filename = os.path.join(input_path, path.name)
                print(f'Parsing file {input_filename}')
                sources = parse_file(input_filename, ui_objects_map, selector)
                #                print(sources)
                if sources is None or None in sources:
                    print('An error happened while parsing {0}'.format(path.name), file=sys.stderr)
                else:
                    feature, requests = generate_feature(file_name, sources, feature_generator)
                    feature_file = os.path.join(output_path, file_name + '.feature')
                    utils.save_file(feature_file, feature)
                    request_file = os.path.join(output_path, file_name + '.req')
                    if requests is None:
                        utils.delete_file(request_file)
                    else:
                        utils.save_file(request_file, requests)
                    utils.move_file(input_filename, os.path.join(success_path, path.name))


if __name__ == '__main__':
    ui_main()
