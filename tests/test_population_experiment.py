import unittest
from pathlib import Path
from types import SimpleNamespace

from src.simulation.population_experiment import (
    RELATIONSHIP_FREQUENCY_RANGES,
    create_household_relationships,
    run_population_experiment,
    run_population_experiment_repetitions,
    summarise_population_experiment_repetitions,
    compare_population_experiments,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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

    def test_summary_contains_all_population_distributions(self):
        summary = self.experiment.summary()

        distributions = summary["population_distributions"]

        self.assertEqual(
            set(distributions.keys()),
            {
                "age_group",
                "hearing_profile",
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
