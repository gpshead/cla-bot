#!/usr/bin/env python3.7
# This file runs on Debian Buster and needs to be Python 3.7 compatible.
from __future__ import annotations

import pathlib
import edgedb


socket_dir = pathlib.Path("/run/edgedb")
admin_socket = socket_dir / ".s.EDGEDB.admin.5656"


async def healthcheck() -> None:
    if not socket_dir.is_dir():
        raise RuntimeError(f"{socket_dir} does not exist")

    if not admin_socket.is_socket():
        raise RuntimeError(f"Socket {admin_socket} not present")

    try:
        conn = None
        conn = await edgedb.async_connect(
            host=str(socket_dir),
            user="edgedb",
            database="edgedb",
            admin=True,
        )
    except Exception as e:
        raise RuntimeError(f"Connecting to {admin_socket} failed: {e}")

    try:
        await conn.execute("SELECT 1;")
        return
    except Exception as e:
        raise RuntimeError(f"Query failed: {type(e)} {e}")
    finally:
        if conn is not None:
            await conn.aclose()

    raise RuntimeError
