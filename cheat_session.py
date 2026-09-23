"""Runtime-only cheat session shared by the desktop backend and CLI worker.

The production activation phrases are represented by one-way digests.  The
human-readable catalog is an obfuscated easter egg, not a security boundary:
an open-source binary that can display a secret cannot make it unrecoverable.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import urllib.request
from typing import Any


EFFECT_DIGESTS = {
    "49e86472520c6883e527b655f25d5e21089fe258e8b4d8431fe909d09a47dfc9": "god_mode",
    "48f743de849d1af2956792d86b699dcf69468cab12adc1974fbdcfe914a1631c": "unkillable",
    "bbd6f73b8063bc4e570f6e744fd96bbe182397c0cf33a7da20ea2ba6ce471326": "infinite_health",
    "e5b2b791acdd64f8428729308bdb8d842c901ebc97f6a3f722cf1231b3e8a7d9": "max_health",
    "8a84cf69967d7cbd5ff2531c22a9ca4819e30348931f55a486369da8bdf250fb": "max_cs",
    "88d6ae1105d3dcbf9d235c3449820a82011d7ba24f1665aecdb716b9f62ca3e3": "infinite_gold",
    "b3d8e9f8788a2629818dce96dd0f7b8c931c416bc8affe8242f341633c93b230": "infinite_meals",
    "bc13c6e5c5072bcd9ef4fdf4179c8279d311b7f21c440d7ffce75a478f7b4a68": "bottomless_inventory",
    "95b7114a9d23ad61f851dcf845f3d5931e7420c9e9d65cb15b4370e4e48ceba4": "one_round_combat",
    "9680d4a775fa82264c5aa07df483aa1f248aac89b19b190a054380fe3641be6b": "force_nine",
    "0f70dc2419ec77c1bf52e9d4f43591a89b1d5b1308386ca71936e596ca3be133": "force_zero",
    "8f204afc327e211bc5c0fd1a5539e374d78e0b178f4837bf38072e289b048d5e": "all_disciplines",
    "cf05a99cc269fe42b0f6bb7432314318be82cb309b987a3ea68bfe65c268d5fe": "developer_sight",
}

CATALOG_DIGEST = "768c5aebaedd7dd4a97bf64af5f26067d75e4e61e884bdbca3742ccc7c4ceecc"
CATALOG_BLOB = "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"

MUTUALLY_EXCLUSIVE = {"force_nine": "force_zero", "force_zero": "force_nine"}
MAX_END_EFFECTS = {"god_mode", "max_health"}


def normalize_code(value: str) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def digest_code(value: str) -> str:
    return hashlib.sha256(normalize_code(value).encode("utf-8")).hexdigest()


def is_catalog_code(value: str) -> bool:
    return secrets.compare_digest(digest_code(value), CATALOG_DIGEST)


def decrypt_catalog(value: str) -> list[dict[str, str]]:
    normalized = normalize_code(value).encode("utf-8")
    if not secrets.compare_digest(hashlib.sha256(normalized).hexdigest(), CATALOG_DIGEST):
        raise ValueError("Catalog phrase was not recognized.")
    key = hashlib.sha256(b"lw-saa-3.1.7-catalog:" + normalized).digest()
    encrypted = base64.b64decode(CATALOG_BLOB)
    plain = bytearray()
    for index, byte in enumerate(encrypted):
        block = hashlib.sha256(key + (index // 32).to_bytes(4, "big")).digest()
        plain.append(byte ^ block[index % 32])
    catalog = json.loads(plain.decode("utf-8"))
    if not isinstance(catalog, list):
        raise ValueError("Catalog payload is invalid.")
    return catalog


class CheatSession:
    """Authoritative desktop-lifetime state; never serialized with a save."""

    def __init__(self, digest_map: dict[str, str] | None = None) -> None:
        self.digest_map = dict(EFFECT_DIGESTS if digest_map is None else digest_map)
        self.token = secrets.token_urlsafe(32)
        self._lock = threading.RLock()
        self._active: set[str] = set()
        self._achievement_locked = False
        self._runtime: dict[str, Any] = {}
        self._developer_snapshot: dict[str, Any] | None = None

    def is_active(self, effect: str) -> bool:
        with self._lock:
            return effect in self._active

    def achievements_locked(self) -> bool:
        with self._lock:
            return self._achievement_locked

    def forced_digit(self) -> int | None:
        with self._lock:
            if "force_nine" in self._active:
                return 9
            if "force_zero" in self._active:
                return 0
            return None

    def runtime_value(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._runtime.get(key, default)

    def set_runtime_value(self, key: str, value: Any) -> None:
        with self._lock:
            if value is None:
                self._runtime.pop(key, None)
            else:
                self._runtime[key] = value

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": sorted(self._active),
                "achievementLocked": self._achievement_locked,
                "runtime": dict(self._runtime),
                "hasDeveloperSnapshot": self._developer_snapshot is not None,
            }

    def toggle_digest(self, digest: str, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            effect = self.digest_map.get(str(digest).lower())
            if not effect:
                return {"recognized": False, **self.status()}
            enabled = effect not in self._active
            restored_snapshot = None
            if enabled:
                other = MUTUALLY_EXCLUSIVE.get(effect)
                if other:
                    self._active.discard(other)
                self._active.add(effect)
                self._achievement_locked = True
                if effect == "developer_sight" and isinstance(snapshot, dict):
                    self._developer_snapshot = json.loads(json.dumps(snapshot))
                if effect in MAX_END_EFFECTS:
                    self._runtime["endurance"] = 99
            else:
                self._active.discard(effect)
                if effect == "developer_sight":
                    restored_snapshot = self._developer_snapshot
                    self._developer_snapshot = None
                if effect in MAX_END_EFFECTS and not self._active.intersection(MAX_END_EFFECTS):
                    self._runtime.pop("endurance", None)
            return {
                "recognized": True,
                "effect": effect,
                "enabled": enabled,
                "restoredSnapshot": restored_snapshot,
                **self.status(),
            }

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = str(payload.get("operation") or "status").lower()
        if operation == "toggle":
            return self.toggle_digest(str(payload.get("digest") or ""), payload.get("snapshot"))
        if operation == "runtime_set":
            self.set_runtime_value(str(payload.get("key") or ""), payload.get("value"))
            return self.status()
        return self.status()


class RemoteCheatClient:
    """CLI-side view of the desktop-owned session."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url
        self.token = token
        self._status: dict[str, Any] = {}
        self.refresh()

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-LoneWolf-Session": self.token},
            method="POST",
        )
        # A cheat-session hiccup (stale token after a restart, a 403 from a
        # zombie instance, a timeout) must never take down the CLI. The remote
        # cheat sync is an optional easter-egg feature, so degrade to the last
        # known status instead of raising.
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                result = json.load(response)
        except Exception as exc:
            close = getattr(exc, "close", None)
            if callable(close):
                close()
            return self._status
        if not isinstance(result, dict):
            return self._status
        self._status = result
        return result

    def refresh(self) -> dict[str, Any]:
        return self._request({"operation": "status"})

    def is_active(self, effect: str) -> bool:
        return effect in self._status.get("active", [])

    def achievements_locked(self) -> bool:
        return bool(self._status.get("achievementLocked"))

    def forced_digit(self) -> int | None:
        if self.is_active("force_nine"):
            return 9
        if self.is_active("force_zero"):
            return 0
        return None

    def runtime_value(self, key: str, default: Any = None) -> Any:
        return self._status.get("runtime", {}).get(key, default)

    def set_runtime_value(self, key: str, value: Any) -> None:
        self._request({"operation": "runtime_set", "key": key, "value": value})

    def status(self) -> dict[str, Any]:
        return dict(self._status)

    def toggle_digest(self, digest: str, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request({"operation": "toggle", "digest": digest, "snapshot": snapshot})


def _cheat_config_from_environment(environment: dict[str, str]) -> tuple[str, str]:
    """Resolve the cheat endpoint url and token.

    A live-token file (written by the desktop app on start) is preferred over
    the process environment so a CLI worker always talks to the currently
    running server, even if it inherited a stale token from a previous
    instance. The environment is the fallback.
    """
    path = str(environment.get("LONEWOLF_SAA_CHEAT_FILE") or "").strip()
    if path:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            url = str(data.get("url") or "").strip()
            token = str(data.get("token") or "").strip()
            if url and token:
                return url, token
        except Exception:
            pass
    url = str(environment.get("LONEWOLF_SAA_CHEAT_URL") or "").strip()
    token = str(environment.get("LONEWOLF_SAA_CHEAT_TOKEN") or "").strip()
    return url, token


def provider_from_environment(environment: dict[str, str]) -> CheatSession | RemoteCheatClient:
    url, token = _cheat_config_from_environment(environment)
    if url and token:
        try:
            return RemoteCheatClient(url, token)
        except Exception:
            # Never let cheat-session setup abort the CLI; run a local session.
            return CheatSession()
    return CheatSession()
