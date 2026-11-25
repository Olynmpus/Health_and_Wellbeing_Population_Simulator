"""Records an individual's use of hearing-related support."""

from dataclasses import dataclass


SUPPORT_TYPES = {
    "hearing_aid",
    "cochlear_implant",
    "other_implantable_hearing_device",
    "consumer_hearable",
    "personal_sound_amplification",
    "remote_microphone",
    "tv_listening_system",
    "other_assistive_listening_device",
    "lip_reading",
    "repetition_or_rephrasing",
    "face_to_face_communication",
    "background_noise_reduction",
    "room_acoustic_modification",
    "lighting_or_seating_adjustment",
    "other_communication_strategy",
    "other_environmental_modification",
    "other",
    "unknown",
}

USE_STATUSES = {
    "currently_using",
    "previously_used",
    "ever_used",
    "never_used",
    "unknown",
}

EVIDENCE_STATUSES = {
    "policy_supported",
    "user_reported",
    "simulation_assumption",
    "evidence_supported",
    "unknown",
}


@dataclass
class SupportUse:
    """A time-specific record of one type of support."""

    agent_id: str
    assessment_month: int
    support_type: str = "unknown"
    use_status: str = "unknown"
    evidence_status: str = "unknown"

    def validate(self):
        if not isinstance(self.agent_id, str) or not self.agent_id.strip():
            raise ValueError("agent_id must be a non-empty string.")

        if (
            isinstance(self.assessment_month, bool)
            or not isinstance(self.assessment_month, int)
            or self.assessment_month < 0
        ):
            raise ValueError(
                "assessment_month must be a non-negative integer."
            )

        if self.support_type not in SUPPORT_TYPES:
            raise ValueError(f"Invalid support type: {self.support_type}")

        if self.use_status not in USE_STATUSES:
            raise ValueError(f"Invalid support use status: {self.use_status}")

        if self.evidence_status not in EVIDENCE_STATUSES:
            raise ValueError(
                f"Invalid evidence status: {self.evidence_status}"
            )

        return True

    def to_dict(self):
        self.validate()

        return {
            "agent_id": self.agent_id,
            "assessment_month": self.assessment_month,
            "support_type": self.support_type,
            "use_status": self.use_status,
            "evidence_status": self.evidence_status,
        }
