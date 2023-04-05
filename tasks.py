#!/usr/bin/env python3

import json
import os
import shlex
import subprocess
import toml as tomllib
from pathlib import Path

from invoke import task, Context
from dotenv import load_dotenv

load_dotenv()


NUA_ENV = "/home/nua/env"

DIM = "\033[2m"
RESET = "\033[0m"

# Default apps, but you can specify yours in the command-line
# (eg. `invoke build --apps=galene,etherpad-lite`)
APPS = [
    {"name": "galene", "hostname": "visio"},
    {"name": "hedgedoc", "hostname": "pad"},
    {"name": "ackee", "hostname": "stats"},
    {"name": "dolibarr", "hostname": "dolibarr"},
    {"name": "etherpad-lite", "hostname": "pad2"},
]
# APPS = []

DEFAULT_DOMAIN = "c17.abilian.com"
DEFAULT_HOST = "c17.abilian.com"
DEFAULT_APPS_ROOT = f"{os.getcwd()}/nua-apps"

# Read environment variables
domain = os.environ.get("NUA_DOMAIN", DEFAULT_DOMAIN)
host = os.environ.get("NUA_HOST", DEFAULT_HOST)
apps_root = os.environ.get("NUA_APPS_ROOT", DEFAULT_APPS_ROOT)


@task
def all(c: Context, apps=None):
    """Build and deploy all apps."""
    build(c, apps)
    deploy(c, apps)


@task
def build(c: Context, apps=None):
    """Build apps. Use --apps=app1,app2,... to only build selected apps."""
    if apps in ("all", None):
        for app in APPS:
            build_app(app)
    else:
        app_ids = apps.split(",")
        for app_id in app_ids:
            app = get_app(app_id)
            build_app(app)


@task
def deploy(c: Context, apps=None):
    """Deploy all apps."""
    sites = []
    if apps in ("all", None):
        for app in APPS:
            sites.append(generate_deploy_config(app))
    else:
        app_ids = apps.split(",")
        for app_id in app_ids:
            app = get_app(app_id)
            sites.append(generate_deploy_config(app))

    deployment = {"site": sites}
    Path("/tmp/nua-deployment.json").write_text(json.dumps(deployment, indent=2))

    if host == "localhost":
        sh(f"{NUA_ENV}/bin/nua-orchestrator deploy /tmp/nua-deployment.json")
    else:
        sh(f"rsync -az /tmp/nua-deployment.json root@{host}:/tmp/nua-deployment.json")
        ssh(f"{NUA_ENV}/bin/nua-orchestrator deploy /tmp/nua-deployment.json")


def build_app(app: str | dict[str, str]):
    """Build a single app."""
    app_name = app["name"]
    cwd = f"{apps_root}"
    print(f"Building {app_name}...")
    if host == "localhost":
        sh(f"{NUA_ENV}/bin/nua-build ./{app_name}", cwd=cwd)
    else:
        sh(f"rsync -e ssh -az ./{app_name} nua@{host}:/tmp/nua-apps/", cwd=cwd)
        ssh(f"{NUA_ENV}/bin/nua-build /tmp/nua-apps/{app_name}")

    # sh(f"nua-build .", cwd=cwd)
    print()


def generate_deploy_config(app: dict[str, str]):
    """Generate a nua-deployment.json file for a single app."""
    app_name = app["name"]
    config_data = get_config(app_name)
    app_id = tomllib.loads(config_data)["metadata"]["id"]
    app_hostname = app.get("hostname", app_id)
    app_domain = f"{app_hostname}.{domain}"
    app_deployment = {
        "image": app_id,
        "domain": app_domain,
    }
    return app_deployment


def get_config(app_name):
    config_file = Path(f"{apps_root}/{app_name}/nua-config.toml")
    if not config_file.exists():
        config_file = Path(f"{apps_root}/{app_name}/nua/nua-config.toml")
    config_data = config_file.read_text()
    return config_data


#
# Helpers
#
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


def get_app(app_name: str) -> dict[str, str]:
    """Get app info from app id."""
    for app in APPS:
        if app["name"] == app_name:
            return app
    else:
        return {"name": app_name}
