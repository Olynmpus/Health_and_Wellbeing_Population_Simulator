import json
import math
from pathlib import Path

def validate_currency_conversion(config):
    """Validate the experiment's currency conversion settings."""

    conversion = config.get("currency_conversion")

    if not isinstance(conversion, dict):
        raise ValueError(
            "Missing or invalid currency_conversion section."
        )

    for field in ("source_currency", "target_currency"):
        code = conversion.get(field)

        if (
            not isinstance(code, str)
            or len(code) != 3
            or not code.isascii()
            or not code.isalpha()
            or not code.isupper()
        ):
            raise ValueError(
                f"{field} must be a three-letter uppercase currency code."
            )

    if conversion["target_currency"] != "AUD":
        raise ValueError(
            "Target currency must be AUD."
        )

    rate = conversion.get("aud_per_unit")

    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not math.isfinite(rate)
        or rate <= 0
    ):
        raise ValueError(
            "aud_per_unit must be a finite positive number."
        )

    evidence = conversion.get("evidence_status")

    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError(
            "Currency conversion evidence_status must be a non-empty string."
        )

    return True

def validate_service_allocation(config):
    """Validate configurable service allocation settings."""

    settings = config.get("service_allocation")

    if settings is None:
        return True

    if not isinstance(settings, dict):
        raise ValueError(
            "service_allocation must be an object."
        )

    valid_policies = {
        "first_come_first_served",
        "need_based",
        "random",
    }

    policy = settings.get(
        "policy",
        "first_come_first_served",
    )

    if policy not in valid_policies:
        raise ValueError(
            f"Invalid service allocation policy: {policy}"
        )

    if policy == "need_based":
        priority = settings.get("need_priority")

        expected = {
            "functional_difficulty_confirmed",
            "difficulty_reported",
            "unknown",
            "no_identified_difficulty",
        }

        if (
            not isinstance(priority, list)
            or len(priority) != 4
            or set(priority) != expected
        ):
            raise ValueError(
                "need_priority must contain each recognised "
                "functional status exactly once."
            )

    evidence = settings.get(
        "evidence_status",
        "simulation_assumption",
    )

    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError(
            "Service allocation evidence_status must be "
            "a non-empty string."
        )

    return True

def load_experiment_config(config_path):
    """
    Load an experiment configuration from a JSON file.
    """

    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8-sig") as file:
        config = json.load(file)

    validate_config(config)

    return config


def validate_config(config):
    """
    Check the basic validity of the experiment configuration.
    """

    required_sections = [
        "experiment_id",
        "population",
        "awareness",
        "access",
        "simulation"
    ]

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing configuration section: {section}")

    validate_currency_conversion(config)
    validate_service_allocation(config)
    population_size = config["population"]["size"]

    if population_size <= 0:
        raise ValueError("Population size must be greater than zero.")

    geography = config["population"]["geography"]

    if sum(geography.values()) != 100:
        raise ValueError("Geographic percentages must add up to 100.")

    awareness = config["awareness"]["initial_awareness_rate"]

    if not 0 <= awareness <= 1:
        raise ValueError("Awareness rate must be between 0 and 1.")

    duration = config["simulation"]["duration_months"]

    if duration <= 0:
        raise ValueError("Simulation duration must be greater than zero.")

    return True


if __name__ == "__main__":

    config_file = Path(__file__).parent.parent / "config" / "HH-EXP-001.json"

    experiment = load_experiment_config(config_file)

    print("Experiment configuration loaded successfully.")
    print("---------------------------------------------")
    print("Experiment:", experiment["experiment_id"])
    print("Population:", experiment["population"]["size"])
    print("Awareness:", experiment["awareness"]["initial_awareness_rate"])
    print("Duration:", experiment["simulation"]["duration_months"], "months")
    print("Repetitions:", experiment["simulation"]["number_of_repetitions"])
