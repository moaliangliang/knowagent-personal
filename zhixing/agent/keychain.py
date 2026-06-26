"""macOS Keychain integration for secure credential storage.

Uses the `security` CLI to interface with the system Keychain.
"""

import subprocess
import sys

from zhixing.config import Config


# ── Core Keychain Operations ────────────────────────────────


def keychain_set(service: str, account: str, password: str) -> bool:
    """Store a password in the macOS Keychain.

    Uses ``security add-generic-password -a ACCOUNT -s SERVICE -w PASSWORD -U``
    (``-U`` updates an existing item if one already exists).

    Returns ``True`` on success.
    """
    try:
        r = subprocess.run(
            [
                "security", "add-generic-password",
                "-a", account,
                "-s", service,
                "-w", password,
                "-U",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def keychain_get(service: str, account: str) -> str | None:
    """Retrieve a password from the macOS Keychain.

    Uses ``security find-generic-password -a ACCOUNT -s SERVICE -w``.

    Returns the password string, or ``None`` if the item does not exist
    or an error occurred.
    """
    try:
        r = subprocess.run(
            [
                "security", "find-generic-password",
                "-a", account,
                "-s", service,
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode == 0:
            return r.stdout.strip() or None
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def keychain_delete(service: str, account: str) -> bool:
    """Delete a password from the macOS Keychain.

    Uses ``security delete-generic-password -a ACCOUNT -s SERVICE``.

    Returns ``True`` on success (or if the item did not exist).
    """
    try:
        r = subprocess.run(
            [
                "security", "delete-generic-password",
                "-a", account,
                "-s", service,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ── Service name constant ───────────────────────────────────

_ZHIXING_SERVICE = "zhixing"


# ── cmd_credential ──────────────────────────────────────────


def cmd_credential(params: dict) -> str:
    """Manage credentials stored in the macOS Keychain.

    Actions:
      - **get**: retrieve a credential by name
      - **set**: store a credential (password read from ``password`` param,
        or prompted interactively via ``read -s``)
      - **delete**: remove a credential
      - **list**: list all credential names for the zhixing service

    Parameters:
        action (str): ``get`` | ``set`` | ``delete`` | ``list``
        name (str): credential name (account). Required for get/set/delete.
        password (str, optional): password value (for ``set``; prompted if omitted).
        service (str, optional): Keychain service name. Default ``"zhixing"``.
    """
    action = params.get("action", "").strip().lower()
    account = params.get("name", "").strip()
    service = params.get("service", _ZHIXING_SERVICE).strip()
    password = params.get("password", "")

    if action == "list":
        return _cmd_credential_list(service)

    if action == "get":
        if not account:
            return "❌ credential: 'name' parameter is required for action=get"
        pwd = keychain_get(service, account)
        if pwd is None:
            return f"❌ credential '{account}' not found in service '{service}'"
        return f"✅ credential '{account}': {pwd}"

    if action == "set":
        if not account:
            return "❌ credential: 'name' parameter is required for action=set"
        if not password:
            password = _prompt_password(f"Password for '{account}': ")
        if not password:
            return "❌ credential: no password provided"
        ok = keychain_set(service, account, password)
        if ok:
            return f"✅ credential '{account}' stored in service '{service}'"
        return f"❌ credential: failed to store '{account}'"

    if action == "delete":
        if not account:
            return "❌ credential: 'name' parameter is required for action=delete"
        ok = keychain_delete(service, account)
        if ok:
            return f"✅ credential '{account}' deleted from service '{service}'"
        return f"❌ credential: failed to delete '{account}'"

    valid_actions = "get / set / delete / list"
    return (
        f"❌ credential: unknown action '{action}'. "
        f"Valid actions: {valid_actions}"
    )


def _cmd_credential_list(service: str) -> str:
    """List all credential account names for a given service.

    Uses ``security dump-keychain`` and filters entries belonging to *service*.
    This is an approximation -- the ``security`` CLI does not expose a direct
    "list accounts for service" command.
    """
    try:
        r = subprocess.run(
            ["security", "dump-keychain"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0:
            return f"📋 credentials for '{service}': (could not read keychain)"

        accounts: list[str] = []
        lines = r.stdout.splitlines()
        # dump-keychain output includes lines like:
        #   "acct"<blob> = "account_name"
        #   "svce"<blob> = "service_name"
        current_service = ""
        current_account = ""
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"svce"<blob>') and '"' in stripped:
                val = stripped.split("=", 1)[-1].strip().strip('"')
                current_service = val
            elif stripped.startswith('"acct"<blob>') and '"' in stripped:
                val = stripped.split("=", 1)[-1].strip().strip('"')
                current_account = val
            elif stripped.startswith("keychain:"):
                # New entry starts; flush previous
                if current_service == service and current_account:
                    accounts.append(current_account)
                current_service = ""
                current_account = ""

        # Flush last entry
        if current_service == service and current_account:
            accounts.append(current_account)

        if not accounts:
            return f"📋 credentials for '{service}': (empty)"
        lines_out = [f"📋 credentials for '{service}':"]
        for i, acct in enumerate(sorted(accounts), 1):
            lines_out.append(f"  {i}. {acct}")
        return "\n".join(lines_out)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return f"❌ credential list failed: {e}"


def _prompt_password(prompt: str = "Password: ") -> str:
    """Prompt for a password interactively via ``/dev/tty`` with echo suppressed.

    Uses ``bash read -s`` for consistent behavior. Returns the password string,
    or empty string on EOF / error.
    """
    try:
        r = subprocess.run(
            ["bash", "-c", f'read -s -p "{prompt}" pwd && echo "$pwd"'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        sys.stderr.write("\n")
        sys.stderr.flush()
        if r.returncode == 0:
            return r.stdout.strip()
        return ""
    except Exception:
        return ""


# ── Migration Helper ────────────────────────────────────────

_SENSITIVE_KEYS = [
    ("llm", "api_key"),
    ("proxy", "fortinet", "password"),
]


def migrate_plaintext_to_keychain(config: Config | None = None) -> str:
    """Check ``config.yaml`` for plain-text secrets and offer to migrate them
    to the macOS Keychain.

    Scans keys listed in ``_SENSITIVE_KEYS``. If any hold a non-empty value,
    prompts the user once (via ``/dev/tty``) before moving each value to the
    Keychain and blanking it in the config file.

    Returns a human-readable summary string.
    """
    if config is None:
        config = Config()

    secrets_found: list[tuple[str, str, str]] = []

    for key_path in _SENSITIVE_KEYS:
        val = config.get(".".join(key_path), "")
        if val and isinstance(val, str) and val.strip():
            display_name = ".".join(key_path)
            secrets_found.append((display_name, ".".join(key_path), val))

    if not secrets_found:
        return "No plain-text secrets found in config."

    prompt_text = (
        "The following secrets are stored in plain text in config.yaml:\n"
        + "\n".join(f"  - {s[0]}" for s in secrets_found)
        + "\n\nMigrate them to macOS Keychain? (y/N) "
    )

    try:
        r = subprocess.run(
            ["bash", "-c", f'read -p "{prompt_text}" ans && echo "$ans"'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        answer = r.stdout.strip().lower()
        if answer not in ("y", "yes"):
            return "Skipped migration (user declined)."
    except Exception:
        return "Skipped migration (no tty available)."

    migrated = []
    failed = []
    for display_name, key_path_str, val in secrets_found:
        # Store in keychain using the full key path as account name
        account = f"config.{key_path_str}"
        ok = keychain_set(_ZHIXING_SERVICE, account, val)
        if ok:
            config.set(key_path_str, "")
            migrated.append(display_name)
        else:
            failed.append(display_name)

    config.save()

    lines = []
    if migrated:
        lines.append(
            "Migrated to Keychain:\n"
            + "\n".join(f"  ✅ {s}" for s in migrated)
        )
    if failed:
        lines.append(
            "Failed to migrate:\n"
            + "\n".join(f"  ❌ {s}" for s in failed)
        )
    if not lines:
        lines.append("No changes made.")

    return "\n".join(lines)


# ── Command Registration (for daily_tools import) ───────────

COMMANDS: dict = {
    "credential": cmd_credential,
}

TOOL_SCHEMAS: dict = {
    "credential": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "Operation: get (retrieve), set (store), delete (remove), list (all names)",
                "enum": ["get", "set", "delete", "list"],
            },
            "name": {
                "type": "string",
                "description": "Credential name (account). Required for get/set/delete.",
            },
            "password": {
                "type": "string",
                "description": "Password value (for action=set; prompted if omitted)",
            },
            "service": {
                "type": "string",
                "description": "Keychain service name, default 'zhixing'",
            },
        },
        "required": ["action"],
    },
}
