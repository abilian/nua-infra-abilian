#!/usr/bin/env python3

import json
import os
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

from invoke import task, Context

DIM = "\033[2m"
RESET = "\033[0m"

apps = [
    {"id": "galene", "name": "visio"},
    {"id": "hedgedoc", "name": "pad"},
    {"id": "ackee", "name": "stats"},
    {"id": "dolibarr-wrap", "name": "dolibarr"},
    {"id": "etherpad-lite", "name": "pad2"},
]

DEFAULT_DOMAIN = "c17.abilian.com"
DEFAULT_HOST = "c17.abilian.com"
DEFAULT_APPS_ROOT = f"{os.getcwd()}/nua-apps"

domain = os.environ.get("NUA_DOMAIN", DEFAULT_DOMAIN)
host = os.environ.get("NUA_HOST", DEFAULT_HOST)
apps_root = os.environ.get("NUA_APPS_ROOT", DEFAULT_APPS_ROOT)


@task
def all(c: Context):
    """Build and deploy all apps."""
    build(c)
    deploy(c)


@task
def build(c: Context, _apps=None):
    """Build apps. Use --apps=app1,app2,... to only build selected apps."""
    if _apps in ("all", None):
        for app in apps:
            build_app(app)
    else:
        app_ids = _apps.split(",")
        for app_id in app_ids:
            app = get_app(app_id)
            build_app(app)


@task
def deploy(c: Context):
    """Deploy all apps."""
    sites = []
    for app in apps:
        config_file = Path(f"{apps_root}/{app['id']}/nua-config.toml")
        if not config_file.exists():
            config_file = Path(f"{apps_root}/{app['id']}/nua/nua-config.toml")
        config_data = config_file.read_text()
        real_app_id = tomllib.loads(config_data)["metadata"]["id"]
        app_deployment = {
            "image": real_app_id,
            "domain": f"{app['name']}.{domain}",
        }
        sites.append(app_deployment)

    deployment = {"site": sites}
    Path("/tmp/nua-deployment.json").write_text(json.dumps(deployment, indent=2))

    if host == "localhost":
        sh(f"/home/nua/nua310/bin/nua-orchestrator deploy /tmp/nua-deployment.json")
    else:
        sh(f"rsync -az /tmp/nua-deployment.json root@{host}:/tmp/nua-deployment.json")
        ssh(f"/home/nua/nua310/bin/nua-orchestrator deploy /tmp/nua-deployment.json")


def build_app(app: dict[str, str]):
    """Build a single app."""
    app_id = app["id"]
    cwd = f"{apps_root}"
    print(f"Building {app_id}...")
    if host == "localhost":
        sh(f"/home/nua/nua310/bin/nua-build ./{app_id}", cwd=cwd)
    else:
        sh(f"rsync -e ssh -az ./{app_id} nua@{host}:/tmp/nua-apps/", cwd=cwd)
        ssh(f"/home/nua/nua310/bin/nua-build /tmp/nua-apps/{app_id}")

    # sh(f"nua-build .", cwd=cwd)
    print()


def sh(cmd: str, cwd: str = "."):
    """Run a shell command."""
    print(f"{DIM}Running {cmd} in {cwd}...{RESET}")
    subprocess.run(cmd, shell=True, cwd=cwd, check=True)


def ssh(cmd: str):
    """Run a ssh command."""
    print(f'{DIM}Running "{cmd}" on server...{RESET}')
    args = shlex.split(cmd)
    cmd = f'ssh nua@{host} "{shlex.join(args)}"'
    subprocess.run(cmd, shell=True, check=True)


def get_app(app_id: str) -> dict[str, str]:
    """Get app info from app id."""
    for app in apps:
        if app["id"] == app_id:
            return app
    raise ValueError(f"Unknown app {app_id}")
