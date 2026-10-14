"""Stable-identity delivery wiring; never bypasses the explicit send gate."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .composio_transport import ComposioTransport
from .composio_upload import stage_pdf
from .delivery_runtime import deliver_prepared
from .platform_client import PlatformClient, verify_stable_connections


def deliver_with_stable_connections(config: dict, prepared: dict, workdir: str | Path, *,
                                    client: PlatformClient, channel_name: str,
                                    request_upload: Callable[[dict], dict],
                                    put_bytes: Callable[[str, bytes, str], None],
                                    download: Callable[[str], bytes], subject: str) -> str:
    """Preflight the owner's Gmail/Slack, then stage and verify exactly one email."""
    delivery = config["delivery"]
    if delivery.get("send_enabled") is not True:
        raise ValueError("delivery disabled")
    if prepared.get("status") != "dry-run" or prepared.get("source_errors") != 0:
        raise ValueError("only a healthy prepared report may be delivered")
    verify_stable_connections(client, delivery["sender"],
                              delivery["slack_channel_id"], channel_name)
    transport = ComposioTransport(execute=lambda slug, args: client.execute("gmail", slug, args),
                                  download=download)
    return deliver_prepared(config, prepared, workdir,
                            stage=lambda name, data: stage_pdf(name, data,
                                request_upload=request_upload, put_bytes=put_bytes),
                            send=transport.send, fetch=transport.fetch, subject=subject)
