import abc
import json
import os
import sys

from etm_converter.model import APITest, ScenarioSource

REQUESTS_MAX_SIZE = 20480


class FeatureGenerator(abc.ABC):
    @abc.abstractmethod
    def feature(self, feature_name: str) -> [str]:
        pass

    @abc.abstractmethod
    def report(self) -> None:
        pass


class DefaultFeatureGenerator(FeatureGenerator):

    def feature(self, feature_name: str) -> [str]:
        return [f'Feature: {feature_name}', '']

    def report(self) -> None:
        # Nothing to report in default implementation
        pass


class SAPIFeatureGenerator(FeatureGenerator):
    test_cases: dict[str, tuple[str, list[str]]]
    unused_test_cases: dict[str, str]

    def __init__(self, input_path: str):
        with open(os.path.join(input_path, 'Suite.json'), 'r') as file:
            lines = file.readlines()
        json_body = '\n'.join(lines)
        try:
            parsed_json = json.loads(json_body)
        except Exception as e:
            print('ERROR: Unable to parse Suite.json', file=sys.stderr)
            print(e, file=sys.stderr)
            print(json, file=sys.stderr)
            raise e
        self.test_cases = {}
        self.unused_test_cases = {}
        for test_case_id, description in parsed_json.items():
            name = description["title"]
            tags = description["tags"]
            self.test_cases[name] = (test_case_id, tags)
            self.unused_test_cases[test_case_id] = name

    def feature(self, feature_name: str) -> [str]:
        if feature_name in self.test_cases:
            test_case_id, tags = self.test_cases[feature_name]
            if test_case_id in self.unused_test_cases:
                del (self.unused_test_cases[test_case_id])
            result = []
            for tag in tags:
                result.append('@' + tag)
            result.sort()
            result.append(f'Feature: {feature_name}')
            result.append('')
            result.append(f'Generated from ETM Test Case Id {test_case_id}')
            result.append('')
            return result
        return [f'Feature: {feature_name}', '', 'ETM Test Case Id Unknown', '']

    def report(self) -> None:
        print('List of Test cases not found in the input', file=sys.stderr)
        for test_case_id, name in self.unused_test_cases.items():
            print(f'{test_case_id} - {name}', file=sys.stderr)


def feature_generator_factory(input_path: str, selector: str) -> FeatureGenerator:
    """
    Creates a FeatureGenerator.
    :param input_path The input folder path.
    :param selector: The selector.
    :return: The feature generator to use.
    """
    if selector and 'sapi' in selector.lower():
        return SAPIFeatureGenerator(input_path)
    return DefaultFeatureGenerator()


def generate_feature(feature_name: str,
                     sources: tuple[ScenarioSource],
                     feature_generator: FeatureGenerator) -> tuple[str, str | None]:
    """
    Generates the content of a feature file for the given scenario sources
    :param feature_name: The feature name.
    :param sources: The scenario sources in the feature.
    :param feature_generator: The feature generator to use.
    :return: A tuple containing the feature and the Optional request file.
    """
    requests = []
    feature_declaration = '\n'.join(feature_generator.feature(feature_name)) + '\n'
    sections = []
    size = sum(source.size() for source in sources if isinstance(source, APITest))
    big_request = size > REQUESTS_MAX_SIZE
    scenario_number = 1
    for source in sources:
        scenarios = source.api_scenarios(big_request)
        for scenario in scenarios:
            sections.append(scenario.replace('Scenario: ', f'Scenario: {scenario_number:0>4}_'))
            scenario_number = scenario_number + 1
        if big_request and isinstance(source, APITest):
            requests.extend(source.request_data())
    return feature_declaration + '\n\n'.join(sections), '\n'.join(requests) if big_request else None
