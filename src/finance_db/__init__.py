# Re-exported so the pyproject.toml console script can call finance_db:main.
from finance_db.main import main

__all__ = ["main"]
