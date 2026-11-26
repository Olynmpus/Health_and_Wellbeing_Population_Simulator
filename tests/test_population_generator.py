import json
import unittest

from pathlib import Path

from src.config_loader import load_experiment_config
from src.population.generator import generate_population


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestPopulationGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.experiment = load_experiment_config(
            PROJECT_ROOT / "config" / "HH-EXP-001.json"
        )
        cls.experiment["population"]["size"] = 1000

        with open(
            PROJECT_ROOT / "config" / "population_baseline.synthetic.json",
            encoding="utf-8",
        ) as file:
            cls.distribution = json.load(file)

    def test_generates_configured_population_size(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        self.assertEqual(len(agents), 1000)

    def test_agent_identifiers_are_unique(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        identifiers = [agent.agent_id for agent in agents]

        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_same_seed_produces_same_population(self):
        first = generate_population(
            self.experiment,
            self.distribution,
        )

        second = generate_population(
            self.experiment,
            self.distribution,
        )

        first_profiles = [
            (
                agent.profile.age_group,
                agent.profile.hearing_profile,
                agent.profile.geography,
                agent.profile.onset_type,
                agent.profile.progression_type,
            )
            for agent in first
        ]

        second_profiles = [
            (
                agent.profile.age_group,
                agent.profile.hearing_profile,
                agent.profile.geography,
                agent.profile.onset_type,
                agent.profile.progression_type,
            )
            for agent in second
        ]

        self.assertEqual(first_profiles, second_profiles)

    def test_legacy_hearing_profile_matches_measured_status(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        for agent in agents:
            self.assertEqual(
                agent.profile.hearing_profile,
                agent.profile.measured_hearing_status,
            )

    def test_generated_agents_pass_validation(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        for agent in agents:
            self.assertTrue(agent.validate())

    def test_communication_preferences_are_not_inferred(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        for agent in agents:
            self.assertEqual(
                agent.profile.communication_profile.modalities,
                [],
            )

    def test_invalid_weight_is_rejected(self):
        distribution = json.loads(json.dumps(self.distribution))
        distribution["weights"]["hearing_profiles"]["normal"] = -1

        with self.assertRaises(ValueError):
            generate_population(self.experiment, distribution)

    def test_missing_weight_is_rejected(self):
        distribution = json.loads(json.dumps(self.distribution))
        del distribution["weights"]["age_groups"]["infant"]

        with self.assertRaises(ValueError):
            generate_population(self.experiment, distribution)

    def test_unlabelled_distribution_is_rejected(self):
        distribution = json.loads(json.dumps(self.distribution))
        distribution["evidence_status"] = "unknown"

        with self.assertRaises(ValueError):
            generate_population(self.experiment, distribution)
    def test_normal_audiometry_can_have_reported_difficulty(self):
        experiment = json.loads(json.dumps(self.experiment))
        distribution = json.loads(json.dumps(self.distribution))

        experiment["population"]["size"] = 1

        distribution["weights"]["hearing_profiles"] = {
            "normal": 1,
            "mild": 0,
            "moderate": 0,
            "severe": 0,
            "profound": 0,
        }

        distribution["weights"]["auditory_functional_status"] = {
            "no_identified_difficulty": 0,
            "difficulty_reported": 1,
            "functional_difficulty_confirmed": 0,
            "unknown": 0,
        }

        agents = generate_population(experiment, distribution)

        self.assertEqual(agents[0].profile.hearing_profile, "normal")
        self.assertEqual(
            agents[0].profile.auditory_functional_status,
            "difficulty_reported",
        )

    def test_normal_audiometry_can_have_confirmed_functional_difficulty(self):
        experiment = json.loads(json.dumps(self.experiment))
        distribution = json.loads(json.dumps(self.distribution))

        experiment["population"]["size"] = 1

        distribution["weights"]["hearing_profiles"] = {
            "normal": 1,
            "mild": 0,
            "moderate": 0,
            "severe": 0,
            "profound": 0,
        }

        distribution["weights"]["auditory_functional_status"] = {
            "no_identified_difficulty": 0,
            "difficulty_reported": 0,
            "functional_difficulty_confirmed": 1,
            "unknown": 0,
        }

        agents = generate_population(experiment, distribution)

        self.assertEqual(agents[0].profile.hearing_profile, "normal")
        self.assertEqual(
            agents[0].profile.auditory_functional_status,
            "functional_difficulty_confirmed",
        )

    def test_invalid_functional_status_is_rejected(self):
        from src.agents.agent import AgentProfile

        profile = AgentProfile(
            age_group="working_age_adult",
            hearing_profile="normal",
            geography="metropolitan",
            auditory_functional_status="hidden_hearing_loss",
        )

        with self.assertRaises(ValueError):
            profile.validate()

    def test_measured_hearing_indicators_default_to_none_and_appear_in_summary(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        for agent in agents:
            self.assertIsNone(
                agent.profile.measured_any_hearing_impairment
            )
            self.assertIsNone(
                agent.profile.measured_moderate_or_worse_hearing_impairment
            )
            self.assertIsNone(
                agent.profile.self_reported_hearing_loss
            )
            self.assertIsNone(
                agent.summary()["measured_any_hearing_impairment"]
            )
            self.assertIsNone(
                agent.summary()["self_reported_hearing_loss"]
            )
            self.assertIsNone(
                agent.summary()["measured_moderate_or_worse_hearing_impairment"]
            )

    def test_measured_hearing_indicators_reject_invalid_values(self):
        from src.agents.agent import AgentProfile

        for field_name in (
            "measured_any_hearing_impairment",
            "measured_moderate_or_worse_hearing_impairment",
            "self_reported_hearing_loss",
        ):
            profile = AgentProfile(
                age_group="working_age_adult",
                hearing_profile="normal",
                geography="metropolitan",
            )
            setattr(profile, field_name, "unknown")

            with self.assertRaises(ValueError):
                profile.validate()

    def test_functional_status_is_in_agent_summary(self):
        agents = generate_population(
            self.experiment,
            self.distribution,
        )

        for agent in agents:
            self.assertIn(
                "auditory_functional_status",
                agent.summary(),
            )

    def test_australian_measured_hearing_prevalence_by_age_band(self):
        with open(
            PROJECT_ROOT / "config" / "population_australia_2025.json",
            encoding="utf-8",
        ) as file:
            distribution = json.load(file)

        experiment = json.loads(json.dumps(self.experiment))
        experiment["population"]["size"] = 10000

        expected_rates = {
            50: (0.195, 0.047),
            60: (0.370, 0.081),
            70: (0.591, 0.189),
            80: (0.839, 0.478),
        }

        for age in (49, 50, 60, 70, 80):
            age_distribution = json.loads(json.dumps(distribution))
            age_weights = age_distribution["weights"]["age_years"]

            for key in age_weights:
                age_weights[key] = 0

            age_weights[str(age)] = 1

            agents = generate_population(experiment, age_distribution)

            if age == 49:
                self.assertTrue(
                    all(
                        agent.profile.measured_any_hearing_impairment is None
                        and agent.profile.measured_moderate_or_worse_hearing_impairment is None
                        for agent in agents
                    )
                )
                continue

            any_results = [
                agent.profile.measured_any_hearing_impairment
                for agent in agents
            ]
            moderate_results = [
                agent.profile.measured_moderate_or_worse_hearing_impairment
                for agent in agents
            ]

            expected_any, expected_moderate = expected_rates[age]

            self.assertAlmostEqual(
                sum(any_results) / len(any_results),
                expected_any,
                delta=0.02,
            )
            self.assertAlmostEqual(
                sum(moderate_results) / len(moderate_results),
                expected_moderate,
                delta=0.02,
            )

            self.assertTrue(
                all(
                    not moderate or any_impairment
                    for any_impairment, moderate in zip(
                        any_results,
                        moderate_results,
                    )
                )
            )

    def test_australian_binary_self_reported_hearing_loss_calibration(self):
        with open(
            PROJECT_ROOT / "config" / "population_australia_2025.json",
            encoding="utf-8",
        ) as file:
            distribution = json.load(file)

        experiment = json.loads(json.dumps(self.experiment))
        experiment["population"]["size"] = 20000

        age_distribution = json.loads(json.dumps(distribution))
        age_weights = age_distribution["weights"]["age_years"]

        for key in age_weights:
            age_weights[key] = 0

        age_weights["55"] = 1

        agents = generate_population(experiment, age_distribution)

        impaired_reports = [
            agent.profile.self_reported_hearing_loss
            for agent in agents
            if agent.profile.measured_any_hearing_impairment is True
        ]
        unimpaired_reports = [
            agent.profile.self_reported_hearing_loss
            for agent in agents
            if agent.profile.measured_any_hearing_impairment is False
        ]

        self.assertTrue(impaired_reports)
        self.assertTrue(unimpaired_reports)

        self.assertAlmostEqual(
            sum(impaired_reports) / len(impaired_reports),
            0.519,
            delta=0.02,
        )
        self.assertAlmostEqual(
            sum(unimpaired_reports) / len(unimpaired_reports),
            0.126,
            delta=0.02,
        )

        under_50_distribution = json.loads(json.dumps(distribution))
        under_50_weights = under_50_distribution["weights"]["age_years"]

        for key in under_50_weights:
            under_50_weights[key] = 0

        under_50_weights["49"] = 1

        under_50_agents = generate_population(
            experiment,
            under_50_distribution,
        )

        self.assertTrue(
            all(
                agent.profile.self_reported_hearing_loss is None
                for agent in under_50_agents
            )
        )

    def test_australian_profile_assigns_exact_ages_and_matching_age_groups(self):
        with open(
            PROJECT_ROOT / "config" / "population_australia_2025.json",
            encoding="utf-8",
        ) as file:
            distribution = json.load(file)

        agents = generate_population(self.experiment, distribution)

        self.assertTrue(all(agent.profile.age_years is not None for agent in agents))
        self.assertTrue(all(0 <= agent.profile.age_years <= 100 for agent in agents))

        from src.service_capacity.constants import AGE_GROUP_RANGES

        for agent in agents:
            age = agent.profile.age_years
            expected_group = next(
                group
                for group, (minimum, maximum) in AGE_GROUP_RANGES.items()
                if age >= minimum and (maximum is None or age <= maximum)
            )
            self.assertEqual(agent.profile.age_group, expected_group)
            self.assertEqual(agent.summary()["age_years"], age)

    def test_australian_exact_age_sampling_is_reproducible(self):
        with open(
            PROJECT_ROOT / "config" / "population_australia_2025.json",
            encoding="utf-8",
        ) as file:
            distribution = json.load(file)

        first = generate_population(self.experiment, distribution)
        second = generate_population(self.experiment, distribution)

        self.assertEqual(
            [agent.profile.age_years for agent in first],
            [agent.profile.age_years for agent in second],
        )

    def test_profiles_without_exact_age_weights_keep_age_years_unset(self):
        agents = generate_population(self.experiment, self.distribution)

        self.assertTrue(all(agent.profile.age_years is None for agent in agents))
        self.assertTrue(all(agent.profile.age_group for agent in agents))

    def test_generates_population_for_different_country_geographies(self):
        country_profile = {
            "service_context": {
                "geographies": ["urban", "rural"],
            }
        }

        experiment = self.experiment.copy()
        experiment["population"] = self.experiment["population"].copy()
        experiment["population"]["geography"] = {
            "urban": 70,
            "rural": 30,
        }

        agents = generate_population(
            experiment,
            self.distribution,
            country_profile=country_profile,
        )

        self.assertEqual(len(agents), 1000)
        self.assertTrue(
            all(
                agent.profile.geography in ["urban", "rural"]
                for agent in agents
            )
        )

    def test_rejects_geographies_not_matching_country_profile(self):
        country_profile = {
            "service_context": {
                "geographies": ["urban", "rural"],
            }
        }

        with self.assertRaisesRegex(
            ValueError,
            "must match the country profile geographies",
        ):
            generate_population(
                self.experiment,
                self.distribution,
                country_profile=country_profile,
            )
if __name__ == "__main__":
    unittest.main()
