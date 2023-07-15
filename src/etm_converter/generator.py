from etm_converter.model import APITest, ScenarioSource, SharedStepTest

REQUESTS_MAX_SIZE = 20480


def generate_feature(feature_name: str, sources: tuple[ScenarioSource]) -> tuple[str, str | None]:
    """
    Generates the content of a feature file for the given scenario sources
    :param feature_name: The feature name
    :param sources: The scenario sources in the feature
    :return: A tuple containing the feature and the Optional request file.
    """
    requests = []
    sections = [f'Feature: {feature_name}']
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
