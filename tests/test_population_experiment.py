import unittest
from pathlib import Path
from types import SimpleNamespace

from src.hearing_support.support_use import SupportUse
from src.simulation.population_experiment import (
    RELATIONSHIP_FREQUENCY_RANGES,
    create_household_relationships,
    run_population_experiment,
    run_population_experiment_repetitions,
    summarise_population_experiment_repetitions,
    compare_population_experiments,
    calibrate_hearing_aid_use,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CalibrationTestRecord:
    def __init__(self, agent_id, age, any_impairment, moderate_or_worse):
        self.agent_id = agent_id
        self.agent = SimpleNamespace(
            profile=SimpleNamespace(
                age_years=age,
                measured_any_hearing_impairment=any_impairment,
                measured_moderate_or_worse_hearing_impairment=moderate_or_worse,
            )
        )
        self.support_use_records = []

    def add_support_use(self, support_use):
        self.support_use_records.append(support_use)


class TestHearingAidUseCalibration(unittest.TestCase):

    CALIBRATION = {
        "evidence_status": "evidence_supported",
        "conditional_probabilities": {
            "mild_bilateral_impairment": 0.269,
            "moderate_or_worse_bilateral_impairment": 0.691,
        },
    }

    def make_records(self, count, age, any_impairment, moderate_or_worse):
        return [
            CalibrationTestRecord(
                f"AGENT-{index}",
                age,
                any_impairment,
                moderate_or_worse,
            )
            for index in range(count)
        ]

    def test_sampled_hearing_aid_use_matches_aeehs_rates(self):
        mild = self.make_records(10000, 65, True, False)
        moderate = self.make_records(10000, 75, True, True)

        calibrate_hearing_aid_use(mild, self.CALIBRATION, random_seed=42)
        calibrate_hearing_aid_use(
            moderate, self.CALIBRATION, random_seed=42
        )

        mild_rate = sum(bool(r.support_use_records) for r in mild) / len(mild)
        moderate_rate = (
            sum(bool(r.support_use_records) for r in moderate)
            / len(moderate)
        )

        self.assertAlmostEqual(mild_rate, 0.269, delta=0.015)
        self.assertAlmostEqual(moderate_rate, 0.691, delta=0.015)

    def test_under_50_and_unknown_measurement_are_not_calibrated(self):
        records = (
            self.make_records(100, 45, True, False)
            + self.make_records(100, 65, None, None)
            + self.make_records(100, 65, False, False)
        )

        calibrate_hearing_aid_use(
            records, self.CALIBRATION, random_seed=42
        )

        self.assertTrue(
            all(not record.support_use_records for record in records)
        )

    def test_calibration_is_reproducible(self):
        first = self.make_records(1000, 70, True, False)
        second = self.make_records(1000, 70, True, False)

        calibrate_hearing_aid_use(first, self.CALIBRATION, random_seed=123)
        calibrate_hearing_aid_use(second, self.CALIBRATION, random_seed=123)

        self.assertEqual(
            [bool(r.support_use_records) for r in first],
            [bool(r.support_use_records) for r in second],
        )


class TestPopulationExperiment(unittest.TestCase):

    def setUp(self):
        self.experiment = run_population_experiment(
            PROJECT_ROOT / "config" / "HH-EXP-001.json",
            PROJECT_ROOT / "config" / "population_baseline.synthetic.json",
        )

    def test_repeated_runs_use_sequential_seeds(self):
        runs = run_population_experiment_repetitions(
            PROJECT_ROOT / "config" / "HH-EXP-001.json",
            PROJECT_ROOT / "config" / "population_baseline.synthetic.json",
            repetitions=3,
            base_seed=100,
        )

        self.assertEqual(
            [run.random_seed for run in runs],
            [100, 101, 102],
        )

    def test_repeated_runs_are_reproducible(self):
        config = PROJECT_ROOT / "config" / "HH-EXP-001.json"
        distribution = (
            PROJECT_ROOT / "config" / "population_baseline.synthetic.json"
        )

        first = run_population_experiment_repetitions(
            config, distribution, repetitions=2, base_seed=200
        )
        second = run_population_experiment_repetitions(
            config, distribution, repetitions=2, base_seed=200
        )

        self.assertEqual(
            [run.summary() for run in first],
            [run.summary() for run in second],
        )

    def test_repetition_summary_reports_mean_and_variability(self):
        runs = run_population_experiment_repetitions(
            PROJECT_ROOT / "config" / "HH-EXP-001.json",
            PROJECT_ROOT / "config" / "population_baseline.synthetic.json",
            repetitions=2,
            base_seed=300,
        )

        summary = summarise_population_experiment_repetitions(runs)

        self.assertEqual(summary["run_count"], 2)
        self.assertEqual(summary["seeds"], [300, 301])
        self.assertIn("total_demands", summary["metrics"])
        self.assertIn("mean", summary["metrics"]["total_demands"])
        self.assertIn(
            "standard_deviation",
            summary["metrics"]["total_demands"],
        )

    def test_comparison_requires_matching_seed_sequences(self):
        config = PROJECT_ROOT / "config" / "HH-EXP-001.json"
        distribution = (
            PROJECT_ROOT / "config" / "population_baseline.synthetic.json"
        )

        baseline = run_population_experiment_repetitions(
            config, distribution, repetitions=2, base_seed=400
        )
        intervention = run_population_experiment_repetitions(
            config, distribution, repetitions=2, base_seed=401
        )

        with self.assertRaisesRegex(ValueError, "matching seed sequences"):
            compare_population_experiments(baseline, intervention)

    def test_population_size_matches_configuration(self):
        self.assertEqual(self.experiment.population_size, 1000)

    def test_one_support_record_per_agent(self):
        self.assertEqual(
            len(self.experiment.support_records),
            len(self.experiment.agents),
        )

    def test_agent_identifiers_are_unique(self):
        identifiers = [
            agent.agent_id for agent in self.experiment.agents
        ]
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_support_records_preserve_agent_identifiers(self):
        agent_ids = [
            agent.agent_id for agent in self.experiment.agents
        ]
        record_ids = [
            record.agent_id for record in self.experiment.support_records
        ]
        self.assertEqual(agent_ids, record_ids)

    def test_experiment_metadata(self):
        self.assertEqual(self.experiment.experiment_id, "HH-EXP-001")
        self.assertEqual(self.experiment.duration_months, 12)
        self.assertEqual(self.experiment.random_seed, 42)
        self.assertEqual(
            self.experiment.evidence_status,
            "simulation_assumption",
        )

    def test_country_profile_metadata(self):
        self.assertEqual(
            self.experiment.country_profile_id,
            "AU-REFERENCE-001",
        )
        self.assertEqual(
            self.experiment.country_name,
            "Australia",
        )

    def test_summary_reports_country_profile(self):
        summary = self.experiment.summary()

        self.assertEqual(
            summary["country_profile_id"],
            "AU-REFERENCE-001",
        )
        self.assertEqual(
            summary["country_name"],
            "Australia",
        )


    def test_summary_reports_population_counts(self):
        summary = self.experiment.summary()

        self.assertEqual(summary["agent_count"], 1000)
        self.assertEqual(summary["support_record_count"], 1000)

    def test_summary_reports_support_use_separately(self):
        first, second = self.experiment.support_records[:2]

        first.add_support_use(
            SupportUse(
                agent_id=first.agent_id,
                assessment_month=0,
                support_type="hearing_aid",
                use_status="ever_used",
                evidence_status="evidence_supported",
            )
        )
        first.add_support_use(
            SupportUse(
                agent_id=first.agent_id,
                assessment_month=1,
                support_type="hearing_aid",
                use_status="currently_using",
                evidence_status="user_reported",
            )
        )
        first.add_support_use(
            SupportUse(
                agent_id=first.agent_id,
                assessment_month=2,
                support_type="hearing_aid",
                use_status="previously_used",
                evidence_status="user_reported",
            )
        )
        second.add_support_use(
            SupportUse(
                agent_id=second.agent_id,
                assessment_month=0,
                support_type="lip_reading",
                use_status="currently_using",
                evidence_status="user_reported",
            )
        )

        support_use = self.experiment.summary()["support_use"]

        self.assertEqual(
            support_use["people_with_any_support_use_record"], 2
        )
        self.assertEqual(
            support_use["people_without_support_use_record"], 998
        )
        self.assertEqual(support_use["support_use_record_count"], 4)
        self.assertEqual(support_use["hearing_aid"]["people_ever_used"], 1)
        self.assertEqual(
            support_use["hearing_aid"]["people_currently_using"], 1
        )
        self.assertEqual(
            support_use["by_support_type"]["hearing_aid"]["people_with_record"],
            1,
        )
        self.assertEqual(
            support_use["by_support_type"]["lip_reading"]["people_with_record"],
            1,
        )


    def test_summary_contains_all_population_distributions(self):
        summary = self.experiment.summary()

        distributions = summary["population_distributions"]

        self.assertEqual(
            set(distributions.keys()),
            {
                "age_group",
                "hearing_profile",
                "measured_hearing_status",
                "self_reported_hearing_status",
                "geography",
                "functional_status",
            },
        )

    def test_functional_status_distribution_totals_population(self):
        summary = self.experiment.summary()

        distribution = summary["population_distributions"][
            "functional_status"
        ]

        total = sum(
            item["count"] for item in distribution.values()
        )

        self.assertEqual(total, self.experiment.population_size)
        self.assertAlmostEqual(
            sum(item["percentage"] for item in distribution.values()),
            100.0,
            places=1,
        )

class TestRelationshipFrequencies(unittest.TestCase):

    def test_reciprocal_relationships_share_valid_frequency(self):
        agents = [
            SimpleNamespace(agent_id="PERSON-001", household_id="HOME-001"),
            SimpleNamespace(agent_id="PERSON-002", household_id="HOME-001"),
            SimpleNamespace(agent_id="PERSON-003", household_id="HOME-002"),
            SimpleNamespace(agent_id="PERSON-004", household_id="HOME-003"),
            SimpleNamespace(agent_id="PERSON-005", household_id="HOME-004"),
        ]

        relationships = create_household_relationships(
            agents,
            random_seed=42,
        )

        relationship_lookup = {
            (item.agent_id, item.contact_id): item
            for item in relationships
        }

        for relationship in relationships:
            with self.subTest(
                relationship=(
                    relationship.agent_id,
                    relationship.contact_id,
                )
            ):
                reciprocal = relationship_lookup[
                    (relationship.contact_id, relationship.agent_id)
                ]

                self.assertEqual(
                    relationship.relationship_type,
                    reciprocal.relationship_type,
                )
                self.assertEqual(
                    relationship.interactions_per_month,
                    reciprocal.interactions_per_month,
                )

                minimum, maximum = RELATIONSHIP_FREQUENCY_RANGES[
                    relationship.relationship_type
                ]

                self.assertGreaterEqual(
                    relationship.interactions_per_month,
                    minimum,
                )
                self.assertLessEqual(
                    relationship.interactions_per_month,
                    maximum,
                )
if __name__ == "__main__":
    unittest.main()
