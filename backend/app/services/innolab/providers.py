"""Provider abstraction for the Innovation AI Lab.

Every external-data touchpoint in the Lab goes through a Provider so that
production behaviour is never accidentally wired straight to a proprietary
endpoint.  All providers ship in two modes:

  * mock  (default, always works offline — used by tests and demos)
  * live  (only if configured via env key AND the global innolab live-mode
          feature flag is enabled)

Providers are feature-flagged; unstamped external calls are refused so a
"provider not configured" state is never silently treated as data.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from app.agents.registry import get_registry


@dataclass(frozen=True)
class ProviderCapability:
    name: str
    kind: str  # statutes|patents|examiner|litigation|clinical|label|documents|export
    requires_live: bool = False


PROVIDER_CAPABILITIES: dict[str, list[ProviderCapability]] = {
    # Local / public-registry mock data — always available.
    "datapatt": [
        ProviderCapability("patent_public_search", "patents"),
        ProviderCapability("statutory_text", "statutes"),
    ],
    # Indian statutory & regulatory mock archive.
    "bharatcode": [
        ProviderCapability("act_text", "statutes"),
        ProviderCapability("schedule_lookup", "regulatory"),
    ],
    # Live providers — off by default.
    "uspto_patents": [ProviderCapability("public_bulk", "patents", requires_live=True)],
    "wipo_patentscope": [ProviderCapability("intl_family", "patents", requires_live=True)],
    "patentscope_data": [ProviderCapability("patent_graph", "patents", requires_live=True)],
    "dpdp_grievance": [ProviderCapability("grievance_pipeline", "regulatory")],
    "clin_trials_gateway": [ProviderCapability("clinical_evidence", "clinical")],
    "label_compliance": [ProviderCapability("label_audit", "label")],
    "export_dossier": [ProviderCapability("dossier_bundle", "export")],
}


class ProviderNotConfiguredError(RuntimeError):
    pass


@dataclass
class ProviderStatus:
    slug: str
    label: str
    available: bool
    live_mode_enabled: bool
    capabilities: list[ProviderCapability]
    configured: bool  # has the required env key when live
    notes: list[str]


class ProviderHub:
    """Mock-first provider registry with optional live escalation.

    In live mode a provider reports `configured=False` and raises
    ProviderNotConfiguredError whenever a mock is expected in its stead, so
    callers can surface the honest "external data source not configured"
    message instead of fabricating citations.
    """

    def __init__(self, live_mode_flag: bool = False) -> None:
        self._live_mode_flag = live_mode_flag
        self._registry = get_registry()

    def list_providers(self) -> list[ProviderStatus]:
        out: list[ProviderStatus] = []
        for slug in sorted(PROVIDER_CAPABILITIES):
            caps = PROVIDER_CAPABILITIES[slug]
            live = any(c.requires_live for c in caps)
            configured = self._check_configured(slug)
            notes: list[str] = []
            if live and not self._live_mode_flag:
                notes.append("Live mode disabled via feature flag — mock data in use.")
            if live and self._live_mode_flag and not configured:
                notes.append(
                    f"Live provider {slug} not configured — surface 'provider not configured' instead of mock."
                )
            out.append(
                ProviderStatus(
                    slug=slug,
                    label=slug.replace("_", " ").title(),
                    available=True,
                    live_mode_enabled=self._live_mode_flag and configured,
                    capabilities=caps,
                    configured=configured,
                    notes=notes,
                )
            )
        return out

    def provider_ready(self, slug: str) -> None:
        """Raises if a live-required provider cannot legally serve data."""
        if slug not in PROVIDER_CAPABILITIES:
            raise ProviderNotConfiguredError(f"Unknown provider: {slug}")
        live_req = [c for c in PROVIDER_CAPABILITIES[slug] if c.requires_live]
        if live_req and self._live_mode_flag and not self._check_configured(slug):
            raise ProviderNotConfiguredError(
                f"Provider '{slug}' requires live configuration; it is currently NOT "
                "configured. Innovation-Lab will not fabricate provider data."
            )

    @staticmethod
    def _check_configured(slug: str) -> bool:
        # Each live provider maps to its own env var; absence = not configured.
        env_map = {
            "uspto_patents": "USPTO_API_KEY",
            "wipo_patentscope": "WIPO_PATENTSCOPE_API_KEY",
            "patentscope_data": "WIPO_PATENTSCOPE_API_KEY",
        }
        env_var = env_map.get(slug)
        if env_var is None:
            return False
        return bool(os.getenv(env_var))


def require_mock_ok(provider_slug: str, live_mode_flag: bool) -> None:
    """Belt-and-braces: assert a provider may be used in mock mode right now."""
    hub = ProviderHub(live_mode_flag=live_mode_flag)
    hub.provider_ready(provider_slug)
