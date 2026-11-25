import unittest

from src.hearing_support.support_use import SupportUse


class TestSupportUse(unittest.TestCase):

    def make_record(self, **kwargs):
        values = {
            "agent_id": "PERSON-001",
            "assessment_month": 0,
        }
        values.update(kwargs)
        return SupportUse(**values)

    def test_default_record_is_valid(self):
        self.assertTrue(self.make_record().validate())

    def test_device_support_is_valid(self):
        record = self.make_record(
            support_type="hearing_aid",
            use_status="currently_using",
            evidence_status="user_reported",
        )
        self.assertTrue(record.validate())

    def test_consumer_hearable_is_valid(self):
        record = self.make_record(
            support_type="consumer_hearable",
            use_status="currently_using",
        )
        self.assertTrue(record.validate())

    def test_communication_strategy_is_valid(self):
        record = self.make_record(
            support_type="repetition_or_rephrasing",
            use_status="currently_using",
        )
        self.assertTrue(record.validate())

    def test_environmental_modification_is_valid(self):
        record = self.make_record(
            support_type="background_noise_reduction",
            use_status="currently_using",
        )
        self.assertTrue(record.validate())

    def test_previous_use_is_distinct_from_current_use(self):
        record = self.make_record(use_status="previously_used")
        self.assertTrue(record.validate())

    def test_ever_used_is_valid(self):
        record = self.make_record(use_status="ever_used")
        self.assertTrue(record.validate())

    def test_never_used_is_valid(self):
        record = self.make_record(use_status="never_used")
        self.assertTrue(record.validate())

    def test_negative_assessment_month_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_record(assessment_month=-1).validate()

    def test_boolean_assessment_month_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_record(assessment_month=True).validate()

    def test_invalid_support_type_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_record(support_type="hearing_loss").validate()

    def test_invalid_use_status_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_record(use_status="sometimes").validate()

    def test_invalid_evidence_status_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_record(evidence_status="verified").validate()

    def test_empty_agent_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.make_record(agent_id=" ").validate()

    def test_serialisation(self):
        record = self.make_record(
            assessment_month=3,
            support_type="consumer_hearable",
            use_status="currently_using",
            evidence_status="user_reported",
        )

        result = record.to_dict()

        self.assertEqual(result["agent_id"], "PERSON-001")
        self.assertEqual(result["assessment_month"], 3)
        self.assertEqual(result["support_type"], "consumer_hearable")
        self.assertEqual(result["use_status"], "currently_using")
        self.assertEqual(result["evidence_status"], "user_reported")


if __name__ == "__main__":
    unittest.main()
