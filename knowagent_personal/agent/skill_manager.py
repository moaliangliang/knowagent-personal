"""Skill management module — install, list, search, remove, and load skills.

Skills are Python files placed in ~/.knowagent/skills/ that define a Skill subclass
(see knowagent_personal.plugins.Skill). This manager handles the lifecycle:
  - Installing from GitHub shorthand, local files, or remote URLs
  - Listing / searching / removing installed skills
  - Discovering and loading all skills into the agent's command registry
"""

import importlib.util
import inspect
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

from knowagent_personal.plugins import Skill, Plugin, auto_register_skill

SKILL_DIR = os.path.expanduser("~/.knowagent/skills")


class SkillManager:
    """Manage skills: install, list, search, remove, load."""

    def __init__(self):
        self._loaded_skills: list[Skill] = []

    # ── query ──────────────────────────────────────────────────────────

    def list_skills(self) -> list[dict]:
        """List all installed skills with metadata."""
        os.makedirs(SKILL_DIR, exist_ok=True)
        results: list[dict] = []
        for fname in sorted(os.listdir(SKILL_DIR)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(SKILL_DIR, fname)
            stat = os.stat(fpath)
            results.append({
                "name": fname[:-3],
                "file": fname,
                "path": fpath,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        return results

    def search_skills(self, query: str) -> list[dict]:
        """Search installed skills by name/description."""
        query_lower = query.lower().strip()
        if not query_lower:
            return self.list_skills()

        os.makedirs(SKILL_DIR, exist_ok=True)
        results: list[dict] = []
        for fname in sorted(os.listdir(SKILL_DIR)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(SKILL_DIR, fname)
            name = fname[:-3]
            # Match against file name
            if query_lower in name.lower():
                stat = os.stat(fpath)
                results.append({
                    "name": name,
                    "file": fname,
                    "path": fpath,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                })
                continue
            # Match against first-line description in the file
            try:
                with open(fpath, encoding="utf-8") as fh:
                    first_lines = [fh.readline() for _ in range(5)]
                for line in first_lines:
                    if query_lower in line.lower():
                        stat = os.stat(fpath)
                        results.append({
                            "name": name,
                            "file": fname,
                            "path": fpath,
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                        })
                        break
            except (OSError, UnicodeDecodeError):
                continue
        return results

    def get_skill(self, name: str) -> dict | None:
        """Get skill details by name (without .py suffix)."""
        if name.endswith(".py"):
            name = name[:-3]
        fpath = os.path.join(SKILL_DIR, f"{name}.py")
        if not os.path.isfile(fpath):
            return None
        stat = os.stat(fpath)
        return {
            "name": name,
            "file": f"{name}.py",
            "path": fpath,
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

    # ── mutation ───────────────────────────────────────────────────────

    def remove_skill(self, name: str) -> str:
        """Uninstall a skill by name."""
        if name.endswith(".py"):
            name = name[:-3]
        fpath = os.path.join(SKILL_DIR, f"{name}.py")
        if not os.path.isfile(fpath):
            raise FileNotFoundError(f"Skill '{name}' not found in {SKILL_DIR}")
        os.remove(fpath)
        return f"Removed skill '{name}'"

    def install_skill(self, source: str) -> str:
        """Install a skill from source.

        Supported source formats:
          - ``gh:user/repo``       → GitHub shorthand, downloads skill.py
          - ``/path/to/file.py``    → local file copy
          - ``https://raw.githubusercontent.com/...`` → remote URL download
          - any ``http(s)://`` URL  → remote download
        """
        os.makedirs(SKILL_DIR, exist_ok=True)

        # GitHub shorthand: gh:user/repo
        if source.startswith("gh:") or source.startswith("gh："):
            url = self._parse_gh_source(source)
            return self._download_skill(url)

        # Local file
        if os.path.isfile(source):
            return self._copy_local_skill(source)

        # Remote URL
        if source.startswith("http://") or source.startswith("https://"):
            return self._download_skill(source)

        raise ValueError(
            f"Unrecognised skill source: {source!r}. "
            f"Use gh:user/repo, a local .py path, or a raw GitHub URL."
        )

    def _copy_local_skill(self, src_path: str) -> str:
        """Copy a local .py file into SKILL_DIR."""
        if not src_path.endswith(".py"):
            raise ValueError(f"Skill file must end with .py: {src_path}")
        dst_name = os.path.basename(src_path)
        dst_path = os.path.join(SKILL_DIR, dst_name)
        if os.path.exists(dst_path):
            raise FileExistsError(
                f"Skill '{dst_name}' already exists at {dst_path}. "
                f"Remove it first or rename your file."
            )
        shutil.copy2(src_path, dst_path)
        return f"Installed skill '{dst_name[:-3]}' from {src_path}"

    def _download_skill(self, url: str) -> str:
        """Download a .py file from URL into SKILL_DIR."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "KnowAgentSkillManager/1.0"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Failed to download skill (HTTP {exc.code}): {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Failed to download skill: {exc.reason}"
            ) from exc

        # Determine filename from Content-Disposition or URL
        filename = self._extract_filename(url, resp)

        if not filename.endswith(".py"):
            filename += ".py"

        dst_path = os.path.join(SKILL_DIR, filename)
        if os.path.exists(dst_path):
            raise FileExistsError(
                f"Skill '{filename}' already exists at {dst_path}. "
                f"Remove it first."
            )

        with open(dst_path, "wb") as fh:
            fh.write(content)

        name = filename[:-3]
        return f"Installed skill '{name}' from {url}"

    @staticmethod
    def _extract_filename(url: str, response: Any) -> str:
        """Extract a sensible filename from the response or URL."""
        # Try Content-Disposition header
        cd = response.headers.get("Content-Disposition") if hasattr(response, "headers") else None
        if cd:
            import re
            m = re.search(r'filename=["\']?([^"\';]+)', cd)
            if m:
                return m.group(1).strip()
        # Fall back to last path segment
        path = urllib.parse.urlparse(url).path
        name = os.path.basename(path)
        if not name:
            name = "skill.py"
        return name

    # ── GitHub shorthand ───────────────────────────────────────────────

    @staticmethod
    def _parse_gh_source(source: str) -> str:
        """Parse 'gh:user/repo' into a raw GitHub download URL.

        Downloads from: https://raw.githubusercontent.com/user/repo/main/skill.py
        """
        # Strip "gh:" prefix
        rest = source[3:].strip().strip("/")
        if "/" not in rest:
            raise ValueError(
                f"Invalid GitHub shorthand '{source}'. Expected gh:user/repo"
            )
        parts = rest.split("/", 1)
        user, repo = parts[0], parts[1]

        # Remove trailing .git if present
        if repo.endswith(".git"):
            repo = repo[:-4]

        if not user or not repo:
            raise ValueError(
                f"Invalid GitHub shorthand '{source}'. Expected gh:user/repo"
            )

        return f"https://raw.githubusercontent.com/{user}/{repo}/main/skill.py"

    # ── discovery & registration ───────────────────────────────────────

    def discover_skills(self) -> list[Skill]:
        """Scan SKILL_DIR and load all skills.

        Returns a list of Skill (or Plugin) instances.
        Previously loaded instances are discarded — each call re-scans.
        """
        os.makedirs(SKILL_DIR, exist_ok=True)
        skills: list[Skill] = []

        if not os.path.isdir(SKILL_DIR):
            return skills

        for fname in sorted(os.listdir(SKILL_DIR)):
            if not fname.endswith(".py") or fname.startswith("__"):
                continue
            fpath = os.path.join(SKILL_DIR, fname)
            skill = self._load_skill_from_file(fpath)
            if skill is not None:
                skills.append(skill)

        self._loaded_skills = skills
        return skills

    @staticmethod
    def _load_skill_from_file(fpath: str) -> Skill | Plugin | None:
        """Load a single Python file as a Skill (or Plugin) instance."""
        module_name = os.path.splitext(os.path.basename(fpath))[0]

        try:
            spec = importlib.util.spec_from_file_location(module_name, fpath)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            # Avoid polluting sys.modules with duplicate loads
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 1. Prefer Skill subclass (more specific)
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Skill) and obj is not Skill:
                    instance: Skill = obj()
                    instance.on_load()
                    return instance

            # 2. Fall back to Plugin subclass
            for _name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Plugin) and obj is not Plugin:
                    instance = obj()
                    instance.on_load()
                    return instance

            return None
        except Exception as exc:
            print(f"  [skill_manager] Warning: failed to load {os.path.basename(fpath)}: {exc}")
            return None

    def register_all(self, target_commands: dict, target_schemas: dict):
        """Register all loaded skills into the provided command/schema dictionaries.

        Each skill's ``cmd_*`` methods are added to *target_commands* and
        their corresponding OpenAI-compatible tool schemas are added to
        *target_schemas*.

        Call :meth:`discover_skills` first to populate the internal skill list.
        """
        if not self._loaded_skills:
            self.discover_skills()

        for skill in self._loaded_skills:
            commands, schemas = auto_register_skill(skill)
            target_commands.update(commands)
            target_schemas.update(schemas)
