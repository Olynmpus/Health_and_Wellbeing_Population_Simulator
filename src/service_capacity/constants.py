"""Shared constants for service capacity models."""

AGE_GROUPS = {
    "infant",
    "preschool",
    "school_age",
    "adolescent",
    "working_age_adult",
    "older_adult",
}

AGE_GROUP_RANGES = {
    "infant": (0, 1),
    "preschool": (2, 4),
    "school_age": (5, 11),
    "adolescent": (12, 17),
    "working_age_adult": (18, 64),
    "older_adult": (65, None),
}
