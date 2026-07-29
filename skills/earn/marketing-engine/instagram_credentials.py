"""Pure credential-shape validation for the Instagram runtime adapter."""


def credential_password(creds):
    value = creds.get("pw") or creds.get("password")
    if not isinstance(value, str) or not value:
        raise ValueError("Instagram credential file has no password")
    return value
