"""CLI entry point for the Reims Web service.

    reims-web [--host 0.0.0.0] [--port 8006] [--mock] [--password-from FILE]

In production (ReimsOS) this is started by the `reims-web.service` systemd unit
listening on :8006, mirroring Proxmox VE's web port.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

import uvicorn

from reims_web.app import create_app
from reims_web.auth import AuthManager, read_password_from_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="reims-web", description="Reims Web VM manager")
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8006, help="bind port (default: 8006)")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="run against the in-memory mock ctl (development without KVM/Vulkan)",
    )
    parser.add_argument(
        "--password-from",
        dest="password_from",
        default=None,
        help="file containing the admin password (also: REIMS_WEB_PASSWORD_FILE)",
    )
    parser.add_argument("--dev", action="store_true", help="development mode: reload and open auth")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_parser().parse_args(argv)

    if args.password_from:
        os.environ["REIMS_WEB_PASSWORD_FILE"] = args.password_from

    password = read_password_from_sources()
    if password is None and not args.mock and not args.dev:
        logging.getLogger(__name__).warning(
            "No admin password configured (REIMS_WEB_PASSWORD or --password-from): "
            "running in open mode. Do not expose this service beyond localhost."
        )
    auth = AuthManager(password)

    app = create_app(mock=args.mock, auth_manager=auth)

    logger = logging.getLogger("reims-web")
    logger.info("Reims Web listening on http://%s:%s (mock=%s, auth=%s)",
                args.host, args.port, args.mock, auth.enabled)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.dev,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
