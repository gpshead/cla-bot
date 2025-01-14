#!/usr/bin/env python3.7
# This file runs on Debian Buster and needs to be Python 3.7 compatible.

from __future__ import annotations
from typing import Dict, Union, Any, Optional

import os
import shutil
import subprocess
import sys
import tempfile

import boto3


def get_secrets_manager(region_name: str):
    session = boto3.session.Session()
    return session.client(
        service_name="secretsmanager",
        region_name=region_name,
    )


def get_secret(secrets_manager, secret_name: str) -> str:
    # a prefix is used to enable multiple instances of the CLA-Bot
    # inside the same collection of secrets.
    if os.environ.get("CUSTOMER") and os.environ.get("INSTANCE"):
        prefix = (
            f'edbcloud/app/{os.environ["CUSTOMER"]}'
            f'/{os.environ["INSTANCE"]}/'
        )
    else:
        prefix = os.environ.get("SECRETS_PREFIX", "CLABOT_")
    data = secrets_manager.get_secret_value(SecretId=prefix + secret_name)
    return data.get("SecretString")


def get_optional_secret(
    secrets_manager,
    secret_name: str,
    default_value: str = "",
) -> str:
    try:
        return get_secret(secrets_manager, secret_name)
    except Exception:
        return default_value


def write_pem_file(pem: str):
    with open("private-key.pem", mode="wt") as key_file:
        key_file.write(pem)


def get_env_variables(
    edgedb_host: str,
    edgedb_password: str,
    edgedb_tls_ca: str,
    github_application_id: str,
    oauth_application_id: str,
    oauth_application_secret: str,
    server_url: str,
    application_secret: str,
    webhook_secret: str,
    organization_name: str,
    organization_display_name: Optional[str],
) -> Dict[str, str]:
    """
    Returns a dictionary of all environmental variables
    handled by the web service.
    """
    return {
        "EDGEDB_HOST": edgedb_host or "127.0.0.1",
        "EDGEDB_USER": "edgedb",
        "EDGEDB_PASSWORD": edgedb_password,
        "EDGEDB_TLS_CA": edgedb_tls_ca,
        "GITHUB_RSA_PRIVATE_KEY": "private-key.pem",
        "GITHUB_APPLICATION_ID": github_application_id,
        "GITHUB_OAUTH_APPLICATION_ID": oauth_application_id,
        "GITHUB_OAUTH_APPLICATION_SECRET": oauth_application_secret,
        "SERVER_URL": server_url,
        "SECRET": application_secret,
        "GITHUB_WEBHOOK_SECRET": webhook_secret or "",
        "ORGANIZATION_NAME": organization_name,
        "ORGANIZATION_DISPLAY_NAME": organization_display_name or "edgedb",
    }


def edgedb(
    *args: Union[str, bytes, os.PathLike],
    settings: Dict[str, str],
    check: bool = True,
    **kwargs: Any,
) -> subprocess.CompletedProcess:

    edgedb_cli = shutil.which("edgedb")
    if not edgedb_cli:
        raise RuntimeError('missing edgedb-cli executable')

    cli_args = [
        '--user', settings['EDGEDB_USER'],
        '--host', settings['EDGEDB_HOST'],
        '--password-from-stdin',
    ]

    ca_file = settings.get('EDGEDB_TLS_CA_FILE')
    if ca_file:
        cli_args.extend([
            '--tls-ca-file', ca_file
        ])

    try:
        return subprocess.run(
            [
                edgedb_cli,
                *cli_args,
                *args,
            ],
            input=settings['EDGEDB_PASSWORD'],
            text=True,
            check=check,
            **kwargs,
        )
    except subprocess.CalledProcessError as e:
        print(f'edgedb failed with exit code {e.returncode}', file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        sys.exit(1)


def edgedb_output(
    *args: Union[str, bytes, os.PathLike],
    settings: Dict[str, str],
    **kwargs: Any,
) -> str:
    try:
        return edgedb(
            *args,
            settings=settings,
            capture_output=True,
            **kwargs,
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f'edgedb failed with exit code {e.returncode}', file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def main() -> None:
    # Collect secrets and configure them as environmental variables
    # read by the Next.js application
    region = os.environ["REGION"]

    secrets_manager = get_secrets_manager(region)

    private_rsa_key = get_secret(secrets_manager, "GITHUB_RSA_PRIVATE_KEY")

    # store the private RSA key on file system: the next.js app will read it
    write_pem_file(private_rsa_key)

    env_variables = get_env_variables(
        get_secret(secrets_manager, "EDGEDB_HOST"),
        get_secret(secrets_manager, "EDGEDB_PASSWORD"),
        get_secret(secrets_manager, "EDGEDB_TLS_CA"),
        get_secret(secrets_manager, "GITHUB_APPLICATION_ID"),
        get_secret(secrets_manager, "GITHUB_OAUTH_APPLICATION_ID"),
        get_secret(secrets_manager, "GITHUB_OAUTH_APPLICATION_SECRET"),
        get_secret(secrets_manager, "SERVER_URL"),
        get_secret(secrets_manager, "SECRET"),
        get_secret(secrets_manager, "GITHUB_WEBHOOK_SECRET"),
        get_secret(secrets_manager, "ORGANIZATION_NAME"),
        get_optional_secret(secrets_manager, "ORGANIZATION_DISPLAY_NAME")
    )

    for key, value in env_variables.items():
        os.environ[key] = value

    ca = env_variables["EDGEDB_TLS_CA"]
    with tempfile.NamedTemporaryFile("wt") as ca_file:
        ca_file.write(ca)
        ca_file.flush()
        env_variables["EDGEDB_TLS_CA_FILE"] = ca_file.name
        os.environ["EDGEDB_TLS_CA_FILE"] = ca_file.name

        # Create the "cla" database if not exists
        # TODO: replace this with `create-database --if-not-exists`
        # once supported.
        databases = set(edgedb_output(
            'list', 'databases',
            settings=env_variables,
        ).split('\n'))

        if 'cla' not in databases:
            edgedb(
                'create-database', 'cla',
                settings=env_variables,
                check=True)

        os.environ["EDGEDB_DATABASE"] = "cla"

        # Apply migrations
        edgedb('-d', 'cla', 'migrate', settings=env_variables)

        # start the next application
        yarn_executable = shutil.which("yarn")

        if not yarn_executable:
            raise RuntimeError("Missing yarn executable")

        os.execv(yarn_executable, ("yarn", "next", "start", "-p", "80"))


if __name__ == "__main__":
    main()
