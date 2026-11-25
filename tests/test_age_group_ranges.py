from src.service_capacity.constants import AGE_GROUPS, AGE_GROUP_RANGES


def test_age_group_ranges_cover_all_existing_age_groups():
    assert set(AGE_GROUP_RANGES) == AGE_GROUPS


def test_age_group_ranges_match_agreed_boundaries():
    assert AGE_GROUP_RANGES == {
        "infant": (0, 1),
        "preschool": (2, 4),
        "school_age": (5, 11),
        "adolescent": (12, 17),
        "working_age_adult": (18, 64),
        "older_adult": (65, None),
    }


def test_age_group_ranges_are_contiguous():
    ranges = list(AGE_GROUP_RANGES.values())

    for current, following in zip(ranges, ranges[1:]):
        assert current[1] is not None
        assert following[0] == current[1] + 1


def test_age_group_ranges_start_at_zero_and_end_open():
    assert AGE_GROUP_RANGES["infant"][0] == 0
    assert AGE_GROUP_RANGES["older_adult"][1] is None
