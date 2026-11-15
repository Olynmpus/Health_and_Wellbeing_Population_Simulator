"""Local LLM interpretation of individual communication events."""

import json
import subprocess
import math
from dataclasses import dataclass
from pathlib import Path


OLLAMA_EXECUTABLE = Path(
    "/mnt/c/Users/geoge/AppData/Local/Programs/Ollama/ollama.exe"
)

DEFAULT_MODEL = "qwen3:1.7b"
DEFAULT_TIMEOUT = 60


@dataclass(frozen=True)
class InterpretationResult:
    text: str | None
    model: str
    status: str
    error: str | None = None

@dataclass(frozen=True)
class MessageGenerationResult:
    text: str | None
    model: str
    status: str
    error: str | None = None

@dataclass(frozen=True)
class RecipientInterpretationResult:
    perceived_message: str | None
    interpretation: str | None
    comprehension_assessment: str | None
    model: str
    status: str
    error: str | None = None

@dataclass(frozen=True)
class CommunicationExperienceAssessmentResult:
    assessment: dict | None
    model: str
    status: str
    error: str | None = None

def interpret_interaction(
    agent_id,
    interaction_context,
    model=DEFAULT_MODEL,
    timeout=DEFAULT_TIMEOUT,
):
    """
    Request an interpretation for one participant.

    This function does not modify participant state, relationships,
    simulation outcomes, or memory records.
    """

    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("agent_id must be a non-empty string.")

    if not isinstance(interaction_context, dict):
        raise ValueError("interaction_context must be a dictionary.")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite number greater than zero.")

    try:
        context_json = json.dumps(
            interaction_context,
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error="context_serialization_failed",
        )

    prompt = (
        'Return exactly this JSON structure: '
        '{"interpretation":"string"}. '
        f"Participant: {agent_id}. "

        "Interpret the interaction strictly from the perspective "
        "of the individual identified in the individual section. "

        "IMPORTANT CONTEXT RULES: "
        "The individual section describes the person being interpreted. "
        "The other_participant section describes a different person. "
        "Never transfer the other participant's characteristics, "
        "state or experiences to the individual. "

        "The current_interaction section describes the available "
        "evidence about the actual interaction. "
        "Do not invent events, dialogue, communication barriers "
        "or reactions that are not described there. "

        "Current state values are general model indicators. "
        "They are not direct observations of this interaction. "
        "Do not interpret numerical values as proof of a particular "
        "feeling, behaviour or experience. "

        "Relationship values describe the individual's relationship "
        "with the other participant. They do not establish what "
        "happened during this interaction. "

        "Previous experiences may provide context but do not prove "
        "that the same experience occurred again. "

        "Describe what the individual might have experienced, "
        "but distinguish available evidence from possible explanations. "
        "Use cautious language for inferred thoughts and feelings. "

        "Do not invent diagnoses, intentions, dialogue, events, "
        "causal relationships or outcomes. "

        "Keep the interpretation concise and specific to this interaction. "
        "If the available evidence does not support a useful interpretation, "
        'return "not_established". '

        f"Context: {context_json}"
    )

    command = [
        str(OLLAMA_EXECUTABLE),
        "run",
        model,
        "--think=false",
        "--hidethinking",
        "--format",
        "json",
        prompt,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error="timeout",
        )

    except FileNotFoundError:
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error="ollama_executable_not_found",
        )

    if result.returncode != 0:
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error=result.stderr.strip() or "ollama_execution_failed",
        )

    try:
        response = json.loads(result.stdout)

    except (json.JSONDecodeError, TypeError):
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error="invalid_json_response",
        )

    if not isinstance(response, dict):
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error="invalid_response_structure",
        )

    interpretation = response.get("interpretation")

    if not isinstance(interpretation, str) or not interpretation.strip():
        return InterpretationResult(
            text=None,
            model=model,
            status="failed",
            error="missing_interpretation",
        )
    return InterpretationResult(
        text=interpretation.strip(),
        model=model,
        status="generated",
    )

def generate_message(
    agent_id,
    interaction_context,
    model=DEFAULT_MODEL,
    timeout=DEFAULT_TIMEOUT,
):
    """Generate a context-dependent message for one simulated agent."""

    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValueError("agent_id must be a non-empty string.")

    if not isinstance(interaction_context, dict):
        raise ValueError("interaction_context must be a dictionary.")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite number greater than zero.")

    try:
        context_json = json.dumps(
            interaction_context,
            ensure_ascii=False,
        )
    except (TypeError, ValueError):
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error="context_serialization_failed",
        )

    prompt = (
        'Return exactly this JSON structure: {"message":"string"}. '
        f"Generate a realistic message spoken by agent {agent_id}. "
        "Use the individual's role, communication preferences, "
        "current state, relationship context and previous interaction "
        "history to guide the message. "
        "The message must be natural, specific and appropriate to "
        "the current situation. "
        "Do not describe internal numerical state values. "
        "Do not assume the other participant knows private information "
        "about this individual. "
        "Do not invent events, diagnoses, services or resources. "
        "Do not force a positive or negative outcome. "
        "The message should reflect the individual's current circumstances "
        "without guaranteeing any particular response. "
        f"Context: {context_json}"
    )

    command = [
        str(OLLAMA_EXECUTABLE),
        "run",
        model,
        "--think=false",
        "--hidethinking",
        "--format",
        "json",
        prompt,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error="timeout",
        )

    except FileNotFoundError:
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error="ollama_executable_not_found",
        )

    if result.returncode != 0:
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error=result.stderr.strip() or "ollama_execution_failed",
        )

    try:
        response = json.loads(result.stdout)

    except (json.JSONDecodeError, TypeError):
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error="invalid_json_response",
        )

    if not isinstance(response, dict):
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error="invalid_response_structure",
        )

    message = response.get("message")

    if not isinstance(message, str) or not message.strip():
        return MessageGenerationResult(
            text=None,
            model=model,
            status="failed",
            error="missing_message",
        )

    return MessageGenerationResult(
        text=message.strip(),
        model=model,
        status="generated",
    )

def interpret_recipient_message(
    recipient_id,
    message,
    interaction_context,
    model=DEFAULT_MODEL,
    timeout=DEFAULT_TIMEOUT,
):
    """Interpret a received message from the recipient's perspective."""

    if not isinstance(recipient_id, str) or not recipient_id.strip():
        raise ValueError("recipient_id must be a non-empty string.")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string.")

    if not isinstance(interaction_context, dict):
        raise ValueError("interaction_context must be a dictionary.")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite number greater than zero.")

    context = {
        "recipient_context": interaction_context,
        "received_message": message,
    }

    try:
        context_json = json.dumps(context, ensure_ascii=False)
    except (TypeError, ValueError):
        return RecipientInterpretationResult(
            perceived_message=None,
            interpretation=None,
            comprehension_assessment=None,
            model=model,
            status="failed",
            error="context_serialization_failed",
        )

    prompt = (
        'Return exactly this JSON structure: '
        '{"perceived_message":"string",'
        '"interpretation":"string",'
        '"comprehension_assessment":"understood|partially_understood|'
        'misunderstood|not_established"}. '
        f"You are interpreting a message received by agent {recipient_id}. "
        "Use only the recipient's context and the actual received message. "
        "Describe what the recipient appears to perceive and understand. "
        "Do not assume the recipient knows the sender's private thoughts, "
        "intentions, state or history. "
        "Do not invent missing information or infer a diagnosis. "
        "Do not treat communication preferences or hearing profiles "
        "as proof of comprehension. "
        "Use not_established when the available evidence is insufficient "
        "to assess comprehension. "
        "This is a tentative interpretation, not a verified measurement. "
        f"Context: {context_json}"
    )

    command = [
        str(OLLAMA_EXECUTABLE),
        "run",
        model,
        "--think=false",
        "--hidethinking",
        "--format",
        "json",
        prompt,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )

    except subprocess.TimeoutExpired:
        return RecipientInterpretationResult(
            None, None, None, model, "failed", "timeout"
        )

    except FileNotFoundError:
        return RecipientInterpretationResult(
            None, None, None, model, "failed",
            "ollama_executable_not_found",
        )

    if result.returncode != 0:
        return RecipientInterpretationResult(
            None, None, None, model, "failed",
            result.stderr.strip() or "ollama_execution_failed",
        )

    try:
        response = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return RecipientInterpretationResult(
            None, None, None, model, "failed", "invalid_json_response"
        )

    if not isinstance(response, dict):
        return RecipientInterpretationResult(
            None, None, None, model, "failed",
            "invalid_response_structure",
        )

    perceived_message = response.get("perceived_message")
    interpretation = response.get("interpretation")
    comprehension = response.get("comprehension_assessment")

    valid_assessments = {
        "understood",
        "partially_understood",
        "misunderstood",
        "not_established",
    }

    if (
        not isinstance(perceived_message, str)
        or not perceived_message.strip()
        or not isinstance(interpretation, str)
        or not interpretation.strip()
        or comprehension not in valid_assessments
    ):
        return RecipientInterpretationResult(
            None, None, None, model, "failed",
            "invalid_interpretation_fields",
        )

    return RecipientInterpretationResult(
        perceived_message=perceived_message.strip(),
        interpretation=interpretation.strip(),
        comprehension_assessment=comprehension,
        model=model,
        status="interpreted",
    )

def assess_communication_experience(
    participant_id,
    interaction_context,
    interaction,
    model=DEFAULT_MODEL,
    timeout=DEFAULT_TIMEOUT,
):
    """Tentatively assess one participant's experience of an interaction."""

    if not isinstance(participant_id, str) or not participant_id.strip():
        raise ValueError("participant_id must be a non-empty string.")

    if not isinstance(interaction_context, dict):
        raise ValueError("interaction_context must be a dictionary.")

    if not isinstance(interaction, dict):
        raise ValueError("interaction must be a dictionary.")

    if not isinstance(model, str) or not model.strip():
        raise ValueError("model must be a non-empty string.")

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite number greater than zero.")

    context = {
        "participant_context": interaction_context,
        "completed_interaction": interaction,
    }

    try:
        context_json = json.dumps(context, ensure_ascii=False)
    except (TypeError, ValueError):
        return CommunicationExperienceAssessmentResult(
            None, model, "failed", "context_serialization_failed"
        )

    metric_names = [
        "communication_breakdown",
        "understanding_difficulty",
        "listening_effort",
        "repetition_required",
        "clarification_required",
        "conversational_repair",
        "missed_information",
        "listening_fatigue",
        "cognitive_fatigue",
        "concentration_demand",
        "frustration",
        "disappointment",
        "embarrassment",
        "anxiety",
        "stress",
        "satisfaction",
        "communication_confidence",
        "willingness_to_participate",
        "social_withdrawal",
        "sense_of_inclusion",
        "independence",
        "interaction_completion",
        "goal_achievement",
        "participation_disruption",
        "unresolved_communication_need",
    ]

    prompt = (
        "Return exactly one JSON object with these fields: "
        '{"metrics":{<each requested metric>:<valid value>},'
        '"evidence":"brief evidence from the interaction",'
        '"assessment_confidence":"low|moderate|high"}. '
        f"Assess the experience of participant {participant_id} only. "
        f"Include every metric in this list: {metric_names}. "
        "For the first 21 metrics use 0=none, 1=low, 2=moderate, "
        "3=high, 4=very high, or not_established. For "
        "interaction_completion use completed, partially_completed, "
        "not_completed, or not_established. For goal_achievement use "
        "achieved, partially_achieved, not_achieved, or not_established. "
        "For participation_disruption and unresolved_communication_need "
        "use yes, no, or not_established. Use not_established when "
        "there is insufficient evidence. Do not infer fatigue, emotions, "
        "confidence, satisfaction, inclusion or independence merely "
        "from a communication difficulty or hearing profile. "
        "Do not treat an attempted clarification or repair as proof "
        "that communication succeeded. Assess interaction outcomes "
        "only when the available evidence supports them. "
        "The assessment_confidence field describes your confidence "
        "in this assessment, not the participant's confidence. "
        "Do not invent events, feelings or outcomes. "
        "This is a tentative LLM assessment, not a verified measurement. "
        f"Context: {context_json}"
    )

    command = [
        str(OLLAMA_EXECUTABLE),
        "run",
        model,
        "--think=false",
        "--hidethinking",
        "--format",
        "json",
        prompt,
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CommunicationExperienceAssessmentResult(
            None, model, "failed", "timeout"
        )
    except FileNotFoundError:
        return CommunicationExperienceAssessmentResult(
            None, model, "failed", "ollama_executable_not_found"
        )

    if result.returncode != 0:
        return CommunicationExperienceAssessmentResult(
            None,
            model,
            "failed",
            result.stderr.strip() or "ollama_execution_failed",
        )

    try:
        response = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return CommunicationExperienceAssessmentResult(
            None, model, "failed", "invalid_json_response"
        )

    if not isinstance(response, dict):
        return CommunicationExperienceAssessmentResult(
            None, model, "failed", "invalid_response_structure"
        )

    metrics = response.get("metrics")
    evidence = response.get("evidence")
    confidence = response.get("assessment_confidence")

    ordinal_values = {"0", "1", "2", "3", "4", "not_established"}

    categorical_values = {
        "interaction_completion": {
            "completed",
            "partially_completed",
            "not_completed",
            "not_established",
        },
        "goal_achievement": {
            "achieved",
            "partially_achieved",
            "not_achieved",
            "not_established",
        },
        "participation_disruption": {
            "yes",
            "no",
            "not_established",
        },
        "unresolved_communication_need": {
            "yes",
            "no",
            "not_established",
        },
    }

    valid_confidence = {"low", "moderate", "high"}

    if (
        not isinstance(metrics, dict)
        or set(metrics) != set(metric_names)
        or any(
            not isinstance(value, str)
            or value not in (
                categorical_values[key]
                if key in categorical_values
                else ordinal_values
            )
            for key, value in metrics.items()
        )
        or not isinstance(evidence, str)
        or not evidence.strip()
        or not isinstance(confidence, str)
        or confidence not in valid_confidence
    ):
        return CommunicationExperienceAssessmentResult(
            None, model, "failed", "invalid_assessment_fields"
        )

    assessment = {
        "metrics": metrics,
        "evidence": evidence.strip(),
        "assessment_confidence": confidence,
        "evidence_status": "llm_assessed_not_verified",
        "verification_status": "not_verified",
        "assessment_source": "local_llm",
    }

    return CommunicationExperienceAssessmentResult(
        assessment=assessment,
        model=model,
        status="assessed",
    )
