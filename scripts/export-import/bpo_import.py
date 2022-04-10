#!/usr/bin/env python3

"""
Import CLA information from a JSON file to EdgeDB.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
import edgedb
from rich.console import Console
from rich.progress import Progress


load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
EDGEDB_PASSWORD = urlparse(DATABASE_URL).password
AGREEMENT_VERSION_UUID = "ffdeda72-b8af-11ec-9afc-630f60eedf1d"
DATE_FORMAT = "<Date %Y-%m-%d.%H:%M:%S.000>"


console = Console()
print = console.print


print("Opening JSON file", end="... ")
with Path("out.json").open() as f:
    clas = json.load(f)
print("done.")


print("Connecting to EdgeDB", end="... ")
con = edgedb.create_client(
    host="localhost",
    user="edgedb",
    database="edgedb",
    password=EDGEDB_PASSWORD,
)
print("connected.")

new_clas = 0
cla_count_before = 0
with Progress(console=console) as progress:
    task = progress.add_task("Importing new CLAs", total=len(clas))

    result = con.query(
        "SELECT count(ContributorLicenseAgreement);"
    )
    cla_count_before = result[0]

    for cla in clas:
        progress.advance(task)

        email = cla["email"].lower().strip()
        username = cla["username"]
        cla_date = datetime.strptime(cla["cla_date"], DATE_FORMAT)
        cla_date = cla_date.replace(tzinfo=timezone.utc)

        result = con.query(
            "SELECT ContributorLicenseAgreement FILTER .normalized_email = <str>$email",
            email=email,
        )
        if result:
            print(f"Skipping existing CLA for email [bold blue]{email}[/bold blue]")
            continue

        new_clas += 1
        result = con.query(
            """
            INSERT ContributorLicenseAgreement {
                agreement_version := (
                    SELECT AgreementVersion filter AgreementVersion.id = <uuid>$avid),
                creation_time := <datetime>$cla_date,
                email := <str>$email,
                username := <str>$username,
                };
            """,
            avid=AGREEMENT_VERSION_UUID,
            cla_date=cla_date,
            email=email,
            username=username,
        )

print(f"Imported {new_clas} new CLAs.")
result = con.query(
    "SELECT count(ContributorLicenseAgreement);"
)
cla_count_after = result[0]

print(f"Database confirms {cla_count_after - cla_count_before} new CLAs.")
