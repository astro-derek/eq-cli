---
description: "Use when writing or refactoring Python code. Covers PEP 8 style, type hints, docstrings, error handling, and testing patterns."
applyTo: "**/*.py"
---

# Python Coding Standards

## Style & Formatting

- **PEP 8**: Follow all PEP 8 guidelines; use Ruff for automatic checking
- **Line length**: 88 characters (Black/Ruff standard)
- **Indentation**: 4 spaces (never tabs)
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **No emoji**: Avoid emoji and unicode emojis (✓, ✗) except in tests for multibyte testing

Example:
```python
def calculate_total(items: list[dict], tax_rate: float = 0.0) -> float:
    """Calculate total cost including tax."""
    return sum(item["price"] for item in items) * (1 + tax_rate)
```

## Type Hints

- **Required**: All function signatures (parameters and return values)
- **Never use `Any`** unless absolutely unavoidable
- **Run mypy**: Resolve all type errors before committing
- **Nullable types**: Use `T | None` or `Optional[T]`

Example:
```python
def fetch_user(user_id: int) -> User | None:
    """Fetch user by ID or return None if not found."""
    ...
```

## Docstrings & Comments

- **All public functions, classes, methods** must have docstrings
- Document parameters, return values, exceptions raised
- Avoid redundant comments (e.g., `x = 5  # set x to 5`)
- Include examples in docstrings for complex functions

Example:
```python
def validate_email(email: str) -> bool:
    """Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
        
    Raises:
        ValueError: If email is empty
    """
    if not email:
        raise ValueError("Email cannot be empty")
    return "@" in email
```

## Error Handling

- **Never silently swallow exceptions**: Always log or re-raise
- **No bare `except:`**: Catch specific exceptions
- **Use context managers** (`with` statements) for resource cleanup
- **Meaningful error messages**: Help future debuggers

Example:
```python
try:
    with open(filepath) as f:
        data = json.load(f)
except FileNotFoundError:
    logger.error(f"Config file not found: {filepath}")
    raise
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in {filepath}: {e}")
    raise ValueError(f"Config parse error: {e}")
```

## Functions & Classes

- **One responsibility**: Single-purpose functions are easier to test and reuse
- **No mutable defaults**: Never use `[]` or `{}` as default arguments
- **≤5 parameters**: Refactor if a function needs more
- **Return early**: Reduce nesting
- **Classes**: Keep simple; use dataclasses for data containers; prefer composition over inheritance
- **`@property`**: For computed attributes, not additional methods

Example (good):
```python
@dataclass
class User:
    name: str
    email: str
    
    @property
    def display_name(self) -> str:
        return f"{self.name} <{self.email}>"
```

## Testing

- **All new functions**: Write unit tests
- **Mock external dependencies**: APIs, databases, file systems
- **Framework**: pytest only
- **Pattern**: Arrange-Act-Assert
- **Save tests in discrete files**: Never commit commented-out tests

Example:
```python
def test_calculate_total():
    # Arrange
    items = [{"price": 10.0}, {"price": 20.0}]
    
    # Act
    result = calculate_total(items, tax_rate=0.1)
    
    # Assert
    assert result == 33.0
```

## Imports

- **No wildcards**: Never `from module import *`
- **Explicit imports**: List all used symbols
- **Order**: Standard library, third-party, local imports
- **isort-compatible**: Use Ruff to autoformat
- **Document in `pyproject.toml`** (not `setup.py`)

Example:
```python
import json
import logging
from pathlib import Path

import requests

from src.models import User
from src.utils import format_date
```

## Python Best Practices

- **`is` for None/bool**: Never `== None` or `== True`
- **f-strings**: For string formatting (not `.format()` or `%`)
- **Comprehensions**: Use list/dict/set comprehensions where readable
- **`enumerate()`**: Instead of manual counters
- **Context managers**: For all file/resource access

Example:
```python
# Good
names = [f"{user.name} ({user.id})" for user in users if user.active]

# Bad
names = []
for i in range(len(users)):
    if users[i].active:
        names.append("%s (%s)" % (users[i].name, users[i].id))
```

## Security & Secrets

- **Never hardcode secrets**: Use `.env` environment variables only
- **Ensure `.env` in `.gitignore`**
- **Don't log URLs with API keys**: Strip sensitive data before logging
- **Use environment variables** for all configuration

## Before Committing

- [ ] All tests pass: `pytest`
- [ ] Type checking passes: `mypy`
- [ ] Formatting & linting pass: `ruff check . && ruff format .`
- [ ] All functions have docstrings and type hints
- [ ] No commented-out code or debug statements
- [ ] No hardcoded credentials
