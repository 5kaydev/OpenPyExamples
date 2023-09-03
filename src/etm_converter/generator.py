import abc
from dataclasses import dataclass

from etm_converter.model import APITest, ScenarioSource

REQUESTS_MAX_SIZE = 20480


class FeatureGenerator(abc.ABC):
    @abc.abstractmethod
    def feature(self, feature_name: str) -> [str]:
        pass


@dataclass(frozen=True)
class DefaultFeatureGenerator(FeatureGenerator):

    def feature(self, feature_name: str) -> [str]:
        return [f'Feature: {feature_name}']


@dataclass(frozen=True)
class SAPIFeatureGenerator(FeatureGenerator):

    def feature(self, feature_name: str) -> [str]:
        return [f'Feature: {feature_name}', '', 'This is a SAPI feature file']


def feature_generator_factory(input_path: str, selector: str) -> FeatureGenerator:
    """
    Creates a FeatureGenerator.
    :param input_path The input folder path.
    :param selector: The selector.
    :return: The feature generator to use.
    """
    if selector and 'sapi' in selector.lower():
        return SAPIFeatureGenerator()
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
    sections = feature_generator.feature(feature_name)
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
    return '\n\n'.join(sections), '\n'.join(requests) if big_request else None
