AGE_VERIFICATION_SETTING_KEYS = frozenset(
    {
        "age_verified",
        "age_verified_at",
        "age_verification_method",
        "birth_year",
    }
)


def merge_user_settings(current: dict | None, updates: dict | None) -> dict:
    editable_updates = {
        key: value
        for key, value in (updates or {}).items()
        if key not in AGE_VERIFICATION_SETTING_KEYS
    }
    return {**(current or {}), **editable_updates}
