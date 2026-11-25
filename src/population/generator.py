"""Generate synthetic individuals for hearing-health simulations.

Generated distributions are scenario assumptions, not population estimates.
Communication preferences are not inferred from age or hearing profile.
"""

import math
import random

from src.service_capacity.constants import AGE_GROUP_RANGES

from src.agents.agent import (
    Agent,
    AgentProfile,
    AgentCommunicationProfile,
)


def _validate_categories(name, categories):
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"{name} must be a non-empty list.")

    if any(not isinstance(item, str) or not item.strip()
           for item in categories):
        raise ValueError(f"{name} must contain non-empty strings.")

    if len(categories) != len(set(categories)):
        raise ValueError(f"{name} contains duplicate categories.")


def _validate_weights(name, categories, weights):
    if not isinstance(weights, dict):
        raise ValueError(f"Weights for {name} must be a dictionary.")

    if set(weights) != set(categories):
        raise ValueError(
            f"Weights for {name} must match its configured categories."
        )

    values = []

    for category in categories:
        value = weights[category]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(
                f"Invalid weight for {name}.{category}: {value}"
            )

        values.append(value)

    if sum(values) <= 0:
        raise ValueError(f"At least one {name} weight must be positive.")

    return values

def _assign_households(agents, household_config, seed):
    """Assign agents to synthetic households using explicit assumptions."""

    if household_config.get("evidence_status") != "simulation_assumption":
        raise ValueError(
            "Household settings must be labelled simulation_assumption."
        )

    size_weights = household_config.get("size_weights")

    if not isinstance(size_weights, dict) or not size_weights:
        raise ValueError("Household size weights must be a dictionary.")

    categories = list(size_weights.keys())
    _validate_categories("household sizes", categories)

    weights = _validate_weights(
        "household sizes",
        categories,
        size_weights,
    )

    sizes = [int(size) for size in categories]

    if any(size <= 0 for size in sizes):
        raise ValueError("Household sizes must be positive integers.")

    rng = random.Random(None if seed is None else seed + 1)
    shuffled_agents = list(agents)
    rng.shuffle(shuffled_agents)

    remaining = len(shuffled_agents)
    position = 0
    household_number = 1

    while remaining > 0:
        household_size = rng.choices(
            sizes,
            weights=weights,
            k=1,
        )[0]

        assigned_size = min(household_size, remaining)
        household_id = f"HOUSEHOLD-{household_number:06d}"

        for agent in shuffled_agents[position:position + assigned_size]:
            agent.household_id = household_id

        position += assigned_size
        remaining -= assigned_size
        household_number += 1


def generate_population(
    experiment_config,
    distribution_config,
    vocabulary=None,
    country_profile=None,
):
    """Generate agents from experiment and synthetic distribution settings.

    Returns:
        list[Agent]: Generated individual agents.

    The same configured random seed and inputs produce the same population.
    """

    if not isinstance(experiment_config, dict):
        raise ValueError("experiment_config must be a dictionary.")

    if not isinstance(distribution_config, dict):
        raise ValueError("distribution_config must be a dictionary.")

    if distribution_config.get("evidence_status") != "simulation_assumption":
        raise ValueError(
            "This generator requires an explicitly labelled "
            "simulation_assumption distribution."
        )

    population_config = experiment_config.get("population", {})
    hearing_config = experiment_config.get("hearing_profiles", {})
    auditory_function_config = experiment_config.get("auditory_function", {})
    simulation_config = experiment_config.get("simulation", {})

    population_size = population_config.get("size")

    if (
        isinstance(population_size, bool)
        or not isinstance(population_size, int)
        or population_size <= 0
    ):
        raise ValueError("Population size must be a positive integer.")

    seed = simulation_config.get("random_seed")

    if seed is not None and (
        isinstance(seed, bool) or not isinstance(seed, int)
    ):
        raise ValueError("random_seed must be an integer or None.")

    geography_weights = population_config.get("geography", {})

    if not isinstance(geography_weights, dict):
        raise ValueError("Population geography must be a dictionary.")

    if country_profile is not None:
        if not isinstance(country_profile, dict):
            raise ValueError("country_profile must be a dictionary.")

        service_context = country_profile.get("service_context")

        if not isinstance(service_context, dict):
            raise ValueError(
                "Country profile must contain a service_context object."
            )

        country_geographies = service_context.get("geographies")

        _validate_categories(
            "country geographies",
            country_geographies,
        )

        if set(geography_weights) != set(country_geographies):
            raise ValueError(
                "Experiment geography categories must match "
                "the country profile geographies."
            )

    categories = {
        "age_groups": population_config.get("age_groups"),
        "hearing_profiles": hearing_config.get("categories"),
        "measured_hearing_status": hearing_config.get("measured_statuses"),
        "self_reported_hearing_status": (
            auditory_function_config.get("self_reported_statuses")
        ),
        "geography": list(geography_weights.keys()),
        "onset_types": hearing_config.get("onset_types"),
        "progression_types": hearing_config.get("progression_types"),
        "auditory_functional_status": (
            auditory_function_config.get("functional_statuses")
        ),
    }

    weights_config = distribution_config.get("weights", {})
    validated_weights = {}

    for name, values in categories.items():
        _validate_categories(name, values)

        if name == "geography":
            # Geography weights are already specified in the experiment file.
            weights = geography_weights
        else:
            weights = weights_config.get(name)

        validated_weights[name] = _validate_weights(
            name,
            values,
            weights,
        )

    rng = random.Random(seed)

    age_year_weights = weights_config.get("age_years")
    if age_year_weights is not None:
        age_year_categories = list(age_year_weights.keys())
        expected_ages = {str(age) for age in range(100)} | {"100+"}

        if set(age_year_categories) != expected_ages:
            raise ValueError(
                "age_years weights must contain ages 0-99 and 100+."
            )

        age_year_values = [
            100 if age == "100+" else int(age)
            for age in age_year_categories
        ]
        age_year_validated_weights = _validate_weights(
            "age_years",
            age_year_categories,
            age_year_weights,
        )
        sampled_ages = rng.choices(
            age_year_values,
            weights=age_year_validated_weights,
            k=population_size,
        )

        def age_group_for_years(age):
            for group, (minimum, maximum) in AGE_GROUP_RANGES.items():
                if age >= minimum and (
                    maximum is None or age <= maximum
                ):
                    return group
            raise ValueError(f"No age group configured for age {age}.")

        sampled_age_groups = [
            age_group_for_years(age) for age in sampled_ages
        ]
    else:
        sampled_ages = [None] * population_size
        sampled_age_groups = rng.choices(
            categories["age_groups"],
            weights=validated_weights["age_groups"],
            k=population_size,
        )

    sampled_values = {
        name: rng.choices(
            categories[name],
            weights=validated_weights[name],
            k=population_size,
        )
        for name in categories
        if name not in {"hearing_profiles", "age_groups"}
    }
    sampled_values["age_groups"] = sampled_age_groups

    # Apply age-specific measured hearing prevalence where evidence exists.
    prevalence_config = distribution_config.get(
        "measured_hearing_prevalence"
    )
    sampled_any_impairment = [None] * population_size
    sampled_moderate_or_worse = [None] * population_size

    if prevalence_config is not None and age_year_weights is not None:
        age_bands = prevalence_config.get("age_bands", {})

        for index, age in enumerate(sampled_ages):
            if age is None:
                continue

            matching_band = next(
                (
                    band
                    for band in age_bands.values()
                    if age >= band["minimum_age"]
                    and (
                        band["maximum_age"] is None
                        or age <= band["maximum_age"]
                    )
                ),
                None,
            )

            if matching_band is None:
                continue

            any_rate = matching_band["any_impairment"]
            moderate_rate = matching_band["moderate_or_worse"]

            if not (
                0 <= moderate_rate <= any_rate <= 1
            ):
                raise ValueError(
                    "Measured hearing prevalence rates must satisfy "
                    "0 <= moderate_or_worse <= any_impairment <= 1."
                )

            draw = rng.random()
            sampled_any_impairment[index] = draw < any_rate
            sampled_moderate_or_worse[index] = draw < moderate_rate

    # Apply binary self-reported hearing loss calibration where evidence exists.
    self_report_config = distribution_config.get(
        "self_reported_hearing_prevalence"
    )
    sampled_self_reported_hearing_loss = [None] * population_size

    if self_report_config is not None:
        conditional_rates = self_report_config[
            "conditional_probabilities"
        ]["measured_any_hearing_impairment"]

        for index, age in enumerate(sampled_ages):
            measured_impairment = sampled_any_impairment[index]

            if age is None or age < 50 or measured_impairment is None:
                continue

            probability = conditional_rates[
                "true" if measured_impairment else "false"
            ]

            if not 0 <= probability <= 1:
                raise ValueError(
                    "Self-reported hearing prevalence probabilities "
                    "must be between 0 and 1."
                )

            sampled_self_reported_hearing_loss[index] = (
                rng.random() < probability
            )

    agents = []

    for index in range(population_size):
        profile = AgentProfile(
            age_group=sampled_values["age_groups"][index],
            age_years=sampled_ages[index],
            measured_any_hearing_impairment=(
                sampled_any_impairment[index]
            ),
            measured_moderate_or_worse_hearing_impairment=(
                sampled_moderate_or_worse[index]
            ),
            self_reported_hearing_loss=(
                sampled_self_reported_hearing_loss[index]
            ),
            hearing_profile=sampled_values["measured_hearing_status"][index],
            measured_hearing_status=(
                sampled_values["measured_hearing_status"][index]
            ),
            self_reported_hearing_status=(
                sampled_values["self_reported_hearing_status"][index]
            ),
            auditory_functional_status=(
                sampled_values["auditory_functional_status"][index]
            ),
            geography=sampled_values["geography"][index],
            onset_type=sampled_values["onset_types"][index],
            progression_type=sampled_values["progression_types"][index],
            communication_profile=AgentCommunicationProfile(),
        )

        agent = Agent(
            agent_id=f"PERSON-{index + 1:06d}",
            profile=profile,
        )

        agent.validate(vocabulary)
        agents.append(agent)

    household_config = population_config.get("households")

    if household_config is not None:
        _assign_households(agents, household_config, seed)

    return agents