#!/usr/bin/env python3

"""
Export CLA information from bugs.python.org to a JSON file.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
import xmlrpc.client

from dotenv import load_dotenv
from rich.progress import track

try:
    import certifi
except ModuleNotFoundError:
    raise ImportError("Install certifi first for SSL to work.")
else:
    del certifi


load_dotenv()

BPO_AUTH = os.environ["BPO_AUTH"]
DATE_FORMAT = "<Date %Y-%m-%d.%H:%M:%S.000>"

bpo = xmlrpc.client.ServerProxy(
    f"https://{BPO_AUTH}@bugs.python.org/xmlrpc", allow_none=True
)
schema = bpo.schema()
assert "user" in schema
user_schema = schema["user"]
assert "contrib_form" in user_schema
assert "contrib_form_date" in user_schema

users = bpo.filter("user", None, {"contrib_form": True})

result = []
for uid in track(users):
    u = bpo.display(
        f"user{uid}",
        "username",
        "address",
        "alternate_addresses",
        "github",
        "contrib_form_date",
        "contrib_form",
        "iscommitter",
    )

    if not u.get("contrib_form") or not u.get("github"):
        # No GitHub account and/or no contrib form signed
        continue

    addresses = [u["address"]]
    for alt in (u.get("alternate_addresses") or "").split():
        if "," in alt or ";" in alt:
            raise ValueError(f", or ; used in split for user{uid}")
        addresses.append(alt)

    dt = datetime.now()
    if u.get("contrib_form_date"):
        dt = datetime.strptime(u["contrib_form_date"], DATE_FORMAT)

    for address in addresses:
        result.append(
            {
                "username": u["github"],
                "email": address,
                "bpo": u["username"],
                "cla_date": dt.strftime(DATE_FORMAT),
                "committer": u["iscommitter"],
            }
        )

with open("out.json", "w") as f:
    json.dump(result, f, indent=2)
