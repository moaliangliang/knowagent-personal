"""Tool module registry -- aggregates COMMANDS and TOOL_SCHEMAS from all tool modules.

Provides:
  ALL_COMMANDS        -- merged dict of all command handlers
  ALL_TOOL_SCHEMAS    -- merged dict of all tool parameter schemas
  ALL_COMMAND_NAMES   -- list of all registered command names
  register_all()      -- function that populates a target COMMANDS / TOOL_SCHEMAS dict
"""

from .ai_tools import COMMANDS as _AI_COMMANDS, TOOL_SCHEMAS as _AI_SCHEMAS
from .clipboard_daemon import COMMANDS as _CLIPBOARD_COMMANDS, TOOL_SCHEMAS as _CLIPBOARD_SCHEMAS
from .daily_tools import COMMANDS as _DAILY_COMMANDS, TOOL_SCHEMAS as _DAILY_SCHEMAS
from .dev_tools import COMMANDS as _DEV_COMMANDS, TOOL_SCHEMAS as _DEV_SCHEMAS
from .file_tools import COMMANDS as _FILE_COMMANDS, TOOL_SCHEMAS as _FILE_SCHEMAS
from .media_tools import COMMANDS as _MEDIA_COMMANDS, TOOL_SCHEMAS as _MEDIA_SCHEMAS
from .monitor_tools import COMMANDS as _MONITOR_COMMANDS, TOOL_SCHEMAS as _MONITOR_SCHEMAS
from .network_tools import COMMANDS as _NETWORK_COMMANDS, TOOL_SCHEMAS as _NETWORK_SCHEMAS
from .system_tools import COMMANDS as _SYSTEM_COMMANDS, TOOL_SCHEMAS as _SYSTEM_SCHEMAS

# ── Aggregated registries ──────────────────────────────────

ALL_COMMANDS: dict = {}
ALL_COMMANDS.update(_AI_COMMANDS)
ALL_COMMANDS.update(_CLIPBOARD_COMMANDS)
ALL_COMMANDS.update(_DAILY_COMMANDS)
ALL_COMMANDS.update(_DEV_COMMANDS)
ALL_COMMANDS.update(_FILE_COMMANDS)
ALL_COMMANDS.update(_MEDIA_COMMANDS)
ALL_COMMANDS.update(_MONITOR_COMMANDS)
ALL_COMMANDS.update(_NETWORK_COMMANDS)
ALL_COMMANDS.update(_SYSTEM_COMMANDS)

ALL_TOOL_SCHEMAS: dict = {}
ALL_TOOL_SCHEMAS.update(_AI_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_CLIPBOARD_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_DAILY_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_DEV_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_FILE_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_MEDIA_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_MONITOR_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_NETWORK_SCHEMAS)
ALL_TOOL_SCHEMAS.update(_SYSTEM_SCHEMAS)

ALL_COMMAND_NAMES: list = sorted(ALL_COMMANDS.keys())


def register_all(
    target_commands: dict | None = None,
    target_schemas: dict | None = None,
) -> None:
    """Merge all tool-module commands and schemas into *target_commands* and
    *target_schemas* (typically the ``COMMANDS`` and ``TOOL_SCHEMAS`` dicts
    from ``tools.py``).  Either dict may be ``None`` to skip that registration.
    """
    if target_commands is not None:
        target_commands.update(ALL_COMMANDS)
    if target_schemas is not None:
        target_schemas.update(ALL_TOOL_SCHEMAS)
