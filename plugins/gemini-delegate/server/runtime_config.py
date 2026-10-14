"""Resolve only this plugin's runtime paths; never load account settings."""
import json
import os
from pathlib import Path

from host_tools import read_text

KEYS = ('GEMINI_DELEGATE_AGY', 'GEMINI_DELEGATE_STATE_DIR')


def runtime_environment(plugin_root, agy=None, state_dir=None, environ=None):
    """Explicit options > process environment > installed manifest > defaults."""
    environment = os.environ if environ is None else environ
    root = Path(plugin_root)
    configured = {}
    for name in ('mcp.json', '.mcp.json'):
        path = root / name
        if not path.is_file():
            continue
        try:
            document = json.loads(read_text(path, encoding='utf-8-sig'))
            entry = document['mcpServers']['gemini-delegate']
            if not isinstance(entry, dict):
                raise ValueError('Invalid server')
            configured = entry.get('env', {})
            if not isinstance(configured, dict):
                raise ValueError('Invalid environment')
            if any(key in configured and not isinstance(configured[key], str)
                   for key in KEYS):
                raise ValueError('Invalid runtime path')
        except (OSError, ValueError, KeyError, TypeError):
            raise ValueError('Invalid Gemini Delegate runtime configuration in ' + name) from None
        break
    explicit = dict(zip(KEYS, (agy, state_dir)))
    result = {}
    for key in KEYS:
        value = explicit[key] or environment.get(key) or configured.get(key)
        if value:
            result[key] = str(value)
    return result


def manager_options(plugin_root, agy=None, state_dir=None):
    environment = runtime_environment(plugin_root, agy, state_dir)
    return {'agy': environment.get(KEYS[0]), 'state_dir': environment.get(KEYS[1])}
