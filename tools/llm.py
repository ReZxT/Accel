"""LLM tools — thin re-export layer from models package.

All callers import from here. The actual logic lives in models/backends.py
and dispatches based on the active model from the registry.
"""

from models.backends import chat_complete, curator_complete
from models.backends import embed_text as embed
