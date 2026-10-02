"""Review what the agent may learn (same as `personagent learned`)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from persona_agent.ledger_admin import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
