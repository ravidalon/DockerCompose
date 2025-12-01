import re

IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def validate_identifier(value: str, name: str = "identifier") -> tuple[bool, str | None]:
    """Validate Cypher identifier to prevent injection attacks"""
    if not value:
        return False, f"{name} cannot be empty"
    if not IDENTIFIER_PATTERN.match(value):
        return False, f"{name} must contain only alphanumeric characters and underscores, and start with a letter"
    if len(value) > 65535:  # Neo4j max identifier length
        return False, f"{name} is too long (max 65535 characters)"
    return True, None


def validate_identifiers(values: list[str], name: str = "identifiers") -> tuple[bool, str | None]:
    for value in values:
        is_valid, error = validate_identifier(value, name)
        if not is_valid:
            return False, error
    return True, None
