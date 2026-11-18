import json
import subprocess
import unittest
import math
from unittest.mock import patch, MagicMock

from src.behaviour.llm_interpreter import (
    LLM_ASSESSMENT_METRICS,
    interpret_interaction,
    generate_message,
    interpret_recipient_message,
    assess_communication_experience,
)

class TestLLMInterpreter(unittest.TestCase):

    def test_valid_response(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "interpretation": "The conversation was difficult to follow."
        })
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
            )

        self.assertEqual(result.status, "generated")
        self.assertEqual(
            result.text,
            "The conversation was difficult to follow.",
        )
        self.assertEqual(result.model, "qwen3:1.7b")
        self.assertIsNone(result.error)

    def test_timeout(self):
        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ollama", 60),
        ):
            result = interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "timeout")
        self.assertIsNone(result.text)

    def test_invalid_json(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "invalid_json_response")

    def test_ollama_execution_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Model unavailable"

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "Model unavailable")

    def test_invalid_agent_id_rejected(self):
        with self.assertRaises(ValueError):
            interpret_interaction(
                "",
                {"event": "family conversation"},
            )

    def test_invalid_context_rejected(self):
        with self.assertRaises(ValueError):
            interpret_interaction(
                "PERSON-001",
                "family conversation",
            )

    def test_invalid_model_rejected(self):
        with self.assertRaises(ValueError):
            interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
                model=" ",
            )

    def test_invalid_timeout_rejected(self):
        for timeout in (0, -1, True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    interpret_interaction(
                        "PERSON-001",
                        {"event": "family conversation"},
                        timeout=timeout,
                    )

    def test_invalid_response_structure(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(["unexpected", "list"])
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "invalid_response_structure")

    def test_missing_interpretation(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"other": "value"})
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_interaction(
                "PERSON-001",
                {"event": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "missing_interpretation")

    def test_unserializable_context(self):
        result = interpret_interaction(
            "PERSON-001",
            {"event": {"unsupported", "set"}},
        )

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.error,
            "context_serialization_failed",
        )
        self.assertIsNone(result.text)

    def test_generate_message_timeout(self):
        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ollama", 60),
        ):
            result = generate_message(
                "PERSON-001",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "timeout")
        self.assertIsNone(result.text)

    def test_generate_message_invalid_json(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = generate_message(
                "PERSON-001",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "invalid_json_response")

    def test_generate_message_missing_message(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"other": "value"})
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = generate_message(
                "PERSON-001",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "missing_message")

    def test_generate_message_valid_response(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "message": "I've been having difficulty following conversations."
        })
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = generate_message(
                "PERSON-001",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "generated")
        self.assertEqual(
            result.text,
            "I've been having difficulty following conversations.",
        )
        self.assertEqual(result.model, "qwen3:1.7b")
        self.assertIsNone(result.error)

    def test_recipient_interpretation_valid_response(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "perceived_message": "The speaker is having difficulty.",
            "interpretation": "They may be asking for understanding.",
            "comprehension_assessment": "understood",
        })
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_recipient_message(
                "PERSON-002",
                "I've been having difficulty following conversations.",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "interpreted")
        self.assertEqual(
            result.perceived_message,
            "The speaker is having difficulty.",
        )
        self.assertEqual(
            result.interpretation,
            "They may be asking for understanding.",
        )
        self.assertEqual(result.comprehension_assessment, "understood")
        self.assertEqual(result.model, "qwen3:1.7b")
        self.assertIsNone(result.error)

    def test_recipient_interpretation_rejects_invalid_comprehension(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "perceived_message": "The speaker needs help.",
            "interpretation": "They are asking for assistance.",
            "comprehension_assessment": "certain",
        })
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_recipient_message(
                "PERSON-002",
                "I've been having difficulty following conversations.",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "invalid_interpretation_fields")
        self.assertIsNone(result.comprehension_assessment)

    def test_recipient_interpretation_allows_not_established(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "perceived_message": "The speaker said something about conversations.",
            "interpretation": "The intended meaning is unclear.",
            "comprehension_assessment": "not_established",
        })
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = interpret_recipient_message(
                "PERSON-002",
                "I've been having difficulty following conversations.",
                {"situation": "family conversation"},
            )

        self.assertEqual(result.status, "interpreted")
        self.assertEqual(
            result.comprehension_assessment,
            "not_established",
        )

class TestCommunicationExperienceAssessment(unittest.TestCase):

    def test_event_metrics_are_not_assessed_by_llm(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            self.valid_assessment_response()
        )
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            result = assess_communication_experience(
                "PERSON-001",
                {"situation": "family conversation"},
                {"messages": ["Hello", "Hi"]},
            )

        self.assertEqual(result.status, "assessed")

        for metric in (
            "communication_breakdown",
            "understanding_difficulty",
            "repetition_required",
            "clarification_required",
            "conversational_repair",
            "missed_information",
            "concentration_demand",
        ):
            self.assertEqual(
                result.assessment["metrics"][metric],
                "not_established",
            )

        prompt = mock_run.call_args.args[0][-1]

        for metric in (
            "communication_breakdown",
            "repetition_required",
            "missed_information",
        ):
            self.assertNotIn(metric, prompt)
            
    def valid_assessment_response(self):
        metric_names = list(LLM_ASSESSMENT_METRICS)

        return {
            "metrics": {
                name: "not_established"
                for name in metric_names
            },
            "evidence": "Insufficient evidence to assess subjective experience.",
            "assessment_confidence": "low",
        }

    def test_valid_assessment_response(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(
            self.valid_assessment_response()
        )
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {"situation": "family conversation"},
                {"messages": ["Hello", "Hi"]},
            )

        self.assertEqual(result.status, "assessed")
        self.assertEqual(
            result.assessment["evidence_status"],
            "llm_assessed_not_verified",
        )
        self.assertEqual(
            result.assessment["verification_status"],
            "not_verified",
        )
        self.assertTrue(
            all(
                value == "not_established"
                for value in result.assessment["metrics"].values()
            )
        )

    def test_rejects_invalid_metric_value(self):
        response = self.valid_assessment_response()
        response["metrics"]["listening_effort"] = "extreme"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(response)
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {},
                {"messages": ["Hello"]},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.error,
            "invalid_assessment_fields",
        )

    def test_rejects_non_string_metric_value(self):
        response = self.valid_assessment_response()
        response["metrics"]["listening_effort"] = []

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(response)
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {},
                {"messages": ["Hello"]},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.error,
            "invalid_assessment_fields",
        )

    def test_accepts_categorical_outcome_values(self):
        response = self.valid_assessment_response()
        response["metrics"].update({
            "interaction_completion": "partially_completed",
            "goal_achievement": "achieved",
            "participation_disruption": "yes",
            "unresolved_communication_need": "no",
        })

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(response)
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {},
                {"messages": ["Hello"]},
            )

        self.assertEqual(result.status, "assessed")

    def test_rejects_ordinal_value_for_categorical_outcome(self):
        response = self.valid_assessment_response()
        response["metrics"]["interaction_completion"] = "2"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(response)
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {},
                {"messages": ["Hello"]},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.error,
            "invalid_assessment_fields",
        )

    def test_handles_invalid_json(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_result.stderr = ""

        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            return_value=mock_result,
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {},
                {"messages": ["Hello"]},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "invalid_json_response")

    def test_handles_timeout(self):
        with patch(
            "src.behaviour.llm_interpreter.subprocess.run",
            side_effect=subprocess.TimeoutExpired("ollama", 60),
        ):
            result = assess_communication_experience(
                "PERSON-001",
                {},
                {"messages": ["Hello"]},
            )

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error, "timeout")
if __name__ == "__main__":
    unittest.main()
