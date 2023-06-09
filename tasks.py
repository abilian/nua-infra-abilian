#!/usr/bin/env python3

import json
import os
import shlex
import subprocess
from pathlib import Path

import toml as tomllib
from dotenv import load_dotenv
from invoke import Context, task

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

DEFAULT_HOST = "c17.abilian.com"
DEFAULT_DOMAIN = "c17.abilian.com"
DEFAULT_APPS_ROOT = f"{os.getcwd()}/nua-apps"


@task
def all(c: Context, apps=None, host="", domain="", apps_root=""):
    """Build and deploy all apps."""
    build(c, apps, host, domain, apps_root)
    deploy(c, apps, host, domain, apps_root)


@task
def build(c: Context, apps=None, host="", domain="", apps_root=""):
    """Build apps. Use --apps=app1,app2,... to only build selected apps."""
    engine = Engine(host, domain, apps_root)
    if apps in ("all", None):
        for app in APPS:
            engine.build_app(app)
    else:
        app_ids = apps.split(",")
        for app_id in app_ids:
            app = get_app(app_id)
            engine.build_app(app)


@task
def deploy(c: Context, apps=None, host="", domain="", apps_root=""):
    """Deploy all apps."""
    engine = Engine(host, domain, apps_root)
    sites = []
    if apps in ("all", None):
        for app in APPS:
            sites.append(engine.generate_deploy_config(app))
    else:
        app_ids = apps.split(",")
        for app_id in app_ids:
            app = get_app(app_id)
            sites.append(engine.generate_deploy_config(app))

    deployment = {"site": sites}
    Path("/tmp/nua-deployment.json").write_text(json.dumps(deployment, indent=2))

    if engine.host == "localhost":
        sh(f"{NUA_ENV}/bin/nua-orchestrator deploy /tmp/nua-deployment.json")
    else:
        sh(
            f"rsync -az /tmp/nua-deployment.json root@{engine.host}:/tmp/nua-deployment.json"
        )
        ssh(
            f"{NUA_ENV}/bin/nua-orchestrator deploy /tmp/nua-deployment.json",
            engine.host,
        )


class Engine:
    def __init__(self, host: str = "", domain: str = "", apps_root: str = ""):
        if host:
            self.host = host
        else:
            self.host = os.environ.get("NUA_HOST", DEFAULT_HOST)
        if domain:
            self.domain = domain
        else:
            self.domain = os.environ.get("NUA_DOMAIN", self.host)
        if apps_root:
            self.apps_root = apps_root
        else:
            self.apps_root = os.environ.get("NUA_APPS_ROOT", DEFAULT_APPS_ROOT)

    def build_app(self, app: str | dict[str, str]):
        """Build a single app."""
        app_name = app["name"]
        cwd = f"{self.apps_root}"
        print(f"Building {app_name}...")
        if self.host == "localhost":
            sh(f"{NUA_ENV}/bin/nua-build ./{app_name}", cwd=cwd)
        else:
            sh(f"rsync -e ssh -az ./{app_name} nua@{self.host}:/tmp/nua-apps/", cwd=cwd)
            ssh(f"{NUA_ENV}/bin/nua-build -vv /tmp/nua-apps/{app_name}", self.host)

        # sh(f"nua-build .", cwd=cwd)
        print()

    def generate_deploy_config(self, app: dict[str, str]):
        """Generate a nua-deployment.json file for a single app."""
        app_name = app["name"]
        config = self.get_config(app_name)
        app_id = config["metadata"]["id"]
        app_hostname = app.get("hostname", app_id)
        app_domain = f"{app_hostname}.{self.domain}"
        app_deployment = {
            "image": app_id,
            "domain": app_domain,
        }
        return app_deployment

    def get_config(self, app_name) -> dict:
        config_file = Path(f"{self.apps_root}/{app_name}/nua-config.toml")
        if not config_file.exists():
            config_file = Path(f"{self.apps_root}/{app_name}/nua/nua-config.toml")
        config_data = config_file.read_text()
        return tomllib.loads(config_data)


#
# Helpers
#
def sh(cmd: str, cwd: str = "."):
    """Run a shell command."""
    print(f'{DIM}Running "{cmd}" locally in "{cwd}"...{RESET}')
    subprocess.run(cmd, shell=True, cwd=cwd, check=True)


def ssh(cmd: str, host: str):
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
