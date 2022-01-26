#!/usr/bin/env python3.7
# This file runs on Debian Buster and needs to be Python 3.7 compatible.

from __future__ import annotations

import asyncio
import asyncio.subprocess
import ctypes
import ctypes.util
import os
import signal

from edb_healthcheck import healthcheck
from mv import Minivisor


def ensure_dead_with_parent():
    """A last resort measure to make sure this process dies with its parent.
    Defensive programming for unhandled errors.
    """
    PR_SET_PDEATHSIG = 1  # include/uapi/linux/prctl.h
    libc = ctypes.CDLL(ctypes.util.find_library("c"))
    libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL)


async def main() -> None:
    PORT = os.environ["PORT"]
    DATABASE_URL = os.environ["DATABASE_URL"]
    mv = Minivisor()
    await mv.spawn(
        "edgedb-server",
        "--bind-address=0.0.0.0",
        "--emit-server-status=fd://1",
        "--tls-cert-mode=generate_self_signed",
        f"--backend-dsn={DATABASE_URL}",
        with_healthcheck=healthcheck,
        grace_period=120.0,  # some grace for bootstrapping
    )

    # await mv.spawn("yarn", "next", "start", "-p", PORT)
    await mv.wait_until_any_terminates()


if __name__ == "__main__":
    ensure_dead_with_parent()
    asyncio.run(main())
