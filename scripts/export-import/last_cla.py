#!/usr/bin/env python3

"""
Tail last CLAs signed.
"""

from __future__ import annotations

import os
import time
from urllib.parse import urlparse

from dotenv import load_dotenv
import edgedb
from rich.console import Console
from rich.progress import Progress


load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
EDGEDB_PASSWORD = urlparse(DATABASE_URL).password


console = Console()
print = console.print


print("Connecting to EdgeDB", end="... ")
con = edgedb.create_client(
    host="localhost",
    user="edgedb",
    database="edgedb",
    password=EDGEDB_PASSWORD,
)
print("connected.")


seen = set()

while True:
    result = con.query(
        """
        SELECT ContributorLicenseAgreement {
            email, username, creation_time
        }
        ORDER BY .creation_time DESC LIMIT 10;
        """,
    )
    for elem in result:
        if elem.email in seen:
            continue
        print(f"{elem.email} - {elem.username} on {elem.creation_time}")
        seen.add(elem.email)
    with Progress(console=console, transient=True) as progress:
        task = progress.add_task("Waiting", total=60)
        for _ in range(60):
            progress.advance(task)
            time.sleep(1)
