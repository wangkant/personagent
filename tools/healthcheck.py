"""Check the configuration and every upstream service (same as `personagent doctor`)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from persona_agent.doctor import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
