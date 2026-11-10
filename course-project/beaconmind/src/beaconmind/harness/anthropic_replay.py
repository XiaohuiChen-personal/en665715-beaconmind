"""Compatibility module for the 2026-10-29 pilot's entry points (tools/pilot_replay.py, tools/pilot_trace.py, tests).

The pilot's Anthropic tool loop now lives in harness/providers/anthropic_messages.py and the replay loop in
harness/replay.py; this module keeps the old names and call signatures so the pilot tooling still runs. New runs
use tools/replay_run.py.

AI-assisted: Claude Opus 5.5 via Cursor, 2026-10-29: wrote the original replay harness here.
Claude Opus 5.5 via Claude Code, 2026-11-10: reduced it to this shim over the split modules.
"""
from beaconmind.harness import replay as _replay
from beaconmind.harness.providers import anthropic_messages as _am
from beaconmind.harness.replay import Budget, fallback_report  # noqa: F401  (re-exported)

SETTINGS = _am.SETTINGS
PRICE = _am.PRICE
MAX_TURNS = _am.MAX_TURNS
RETRY_STATUS = _am.RETRY_STATUS
turn_cost = _am.turn_cost
agent_step = _am.agent_step
_call = _am._call                      # used by tools/pilot_trace.py
_with_breakpoint = _am._with_breakpoint
_block = _am._block
_usage = _am._usage


def replay_seed(client, system_text, log_doc, out_path, budget, max_steps, log=print):
    """The pilot's signature: replay one episode with Claude Opus 5.5 (see harness/replay.py)."""
    return _replay.replay_seed(_am.AnthropicAgent(client), system_text, log_doc, out_path, budget, max_steps, log)
