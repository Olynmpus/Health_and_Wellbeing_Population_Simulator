import copy
import json
import unittest
from pathlib import Path

from src.config_loader import validate_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestServiceAllocationConfig(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(
            PROJECT_ROOT / "config" / "HH-EXP-001.json",
            encoding="utf-8",
        ) as file:
            cls.base_config = json.load(file)

    def test_accepts_default_configuration_without_allocation_section(self):
        config = copy.deepcopy(self.base_config)
        config.pop("service_allocation")

        self.assertTrue(validate_config(config))

    def test_accepts_first_come_first_served_policy(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["policy"] = (
            "first_come_first_served"
        )

        self.assertTrue(validate_config(config))

    def test_accepts_need_based_policy(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["policy"] = "need_based"

        self.assertTrue(validate_config(config))

    def test_accepts_random_policy(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["policy"] = "random"

        self.assertTrue(validate_config(config))

    def test_rejects_unknown_allocation_policy(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["policy"] = "priority_by_age"

        with self.assertRaises(ValueError):
            validate_config(config)

    def test_rejects_incomplete_need_priority(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["policy"] = "need_based"
        config["service_allocation"]["need_priority"] = [
            "functional_difficulty_confirmed",
            "difficulty_reported",
            "unknown",
        ]

        with self.assertRaises(ValueError):
            validate_config(config)

    def test_rejects_duplicate_need_priority(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["policy"] = "need_based"
        config["service_allocation"]["need_priority"] = [
            "functional_difficulty_confirmed",
            "difficulty_reported",
            "unknown",
            "unknown",
        ]

        with self.assertRaises(ValueError):
            validate_config(config)

    def test_rejects_invalid_allocation_section(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"] = "need_based"

        with self.assertRaises(ValueError):
            validate_config(config)

    def test_rejects_empty_allocation_evidence_status(self):
        config = copy.deepcopy(self.base_config)
        config["service_allocation"]["evidence_status"] = " "

        with self.assertRaises(ValueError):
            validate_config(config)


if __name__ == "__main__":
    unittest.main()
