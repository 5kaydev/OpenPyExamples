import argparse
import os

from etm_converter import utils
from etm_converter.api_converter import parse_file
from etm_converter.generator import generate_feature


def api_main():
    parser = argparse.ArgumentParser(prog='etcmain',
                                     description='Generate Gherkin test scenarios from excel files',
                                     usage='etcmain input_dir output_dir selector')
    parser.add_argument('input_dir')
    parser.add_argument('output_dir')
    parser.add_argument('selector', nargs='?')
    args = parser.parse_args()
    input_path = args.input_dir
    output_path = args.output_dir
    selector = args.selector
    success_path = os.path.join(input_path, 'success')
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(success_path, exist_ok=True)
    paths = utils.scan_dir(input_path, '*.xlsx')
    paths.sort()
    for path in paths:
        input_filename = os.path.join(input_path, path.name)
        sources = parse_file(input_filename, selector)
        if sources is not None:
            file_name = path.name[:-5]
            feature, requests = generate_feature(file_name, sources)
            utils.save_file(os.path.join(output_path, file_name + '.feature'), feature)
            request_file = os.path.join(output_path, file_name + '.req')
            if requests is None:
                utils.delete_file(request_file)
            else:
                utils.save_file(request_file, requests)
            utils.move_file(input_filename, os.path.join(success_path, path.name))


if __name__ == '__main__':
    api_main()
