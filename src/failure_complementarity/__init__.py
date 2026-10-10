"""Failure-conditioned recovery experiments on SWE-bench Pro V2 with mini-SWE-agent."""

import os

# mini-swe-agent prints a banner on import unless this is set; keep logs machine-readable.
os.environ.setdefault("MSWEA_SILENT_STARTUP", "1")

__version__ = "0.1.0"
