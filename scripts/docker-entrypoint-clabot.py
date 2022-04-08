#!/usr/bin/env python3.7
# This file runs on Debian Buster and needs to be Python 3.7 compatible.

from __future__ import annotations

import asyncio
import asyncio.subprocess
import ctypes
import ctypes.util
import os
import signal
import sys
from urllib.parse import urlparse

from edb_healthcheck import healthcheck
from mv import Minivisor


def ensure_dead_with_parent():
    """A last resort measure to make sure this process dies with its parent.
    Defensive programming for unhandled errors.
    """
    PR_SET_PDEATHSIG = 1  # include/uapi/linux/prctl.h
    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)


def untangle_github_rsa_private_key() -> None:
    """Heroku sort of supports multiline config vars. Docker .env does not."""

    GITHUB_RSA_PRIVATE_KEY_SOURCE = os.environ["GITHUB_RSA_PRIVATE_KEY_SOURCE"]
    GITHUB_RSA_KEY_PATH = "/home/github-private-key.pem"
    os.environ["GITHUB_RSA_PRIVATE_KEY"] = GITHUB_RSA_KEY_PATH

    with open(GITHUB_RSA_KEY_PATH, "w") as key_file:
        source = GITHUB_RSA_PRIVATE_KEY_SOURCE
        if source[0] == '"':
            import ast
            parsed = ast.parse(source, mode="eval").body
            if isinstance(parsed, ast.Constant):
                # Python 3.9+
                source = parsed.value
            elif isinstance(parsed, ast.Str):
                # Python 3.7
                source = parsed.s
            else:
                raise TypeError(f"{type(parsed)}")
        key_file.write(source)


async def main() -> None:
    PORT = os.environ["PORT"]
    DATABASE_URL = os.environ["DATABASE_URL"]
    EDGEDB_PASSWORD = urlparse(DATABASE_URL).password
    mv = Minivisor()

    new_release = False
    if len(sys.argv) > 1:
        if sys.argv[1] == "deployment":
            await mv.out.put(b"Running deployment tasks for a new release...")
            new_release = True
        elif sys.argv[1] != "default":
            await mv.out.put(b"Invalid entrypoint sub-command: " + sys.argv[1].encode())
            await mv.shutdown()
            return

    if new_release:
        import deployment
        await deployment.main(mv)
        return

    await mv.spawn(
        "edgedb-server",
        "--bind-address=0.0.0.0",
        "--emit-server-status=fd://1",
        "--tls-cert-mode=generate_self_signed",
        f"--backend-dsn={DATABASE_URL}",
        with_healthcheck=healthcheck,
        grace_period=20.0,
    )

    os.environ["EDGEDB_HOST"] = "127.0.0.1"
    os.environ["EDGEDB_PORT"] = "5656"
    os.environ["EDGEDB_PASSWORD"] = EDGEDB_PASSWORD
    os.environ["ORGANIZATION_NAME"] = "python"
    os.environ["ORGANIZATION_DISPLAY_NAME"] = "Python Software Foundation"

    untangle_github_rsa_private_key()

    await mv.spawn("yarn", "next", "start", "-p", PORT)
    await mv.wait_until_any_terminates()


if __name__ == "__main__":
    ensure_dead_with_parent()
    asyncio.run(main())
