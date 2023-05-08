import argparse
import copy
import logging
import os
import re
import shutil
import subprocess
import time

import requests

from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

logging.basicConfig(level=logging.WARNING)

GITLAB_BOT_NAME = os.environ["GITLAB_BOT_NAME"].strip()
GITLAB_BOT_EMAIL = os.environ["GITLAB_BOT_EMAIL"].strip()
GITLAB_BOT_TOKEN = os.environ["GITLAB_BOT_TOKEN"].strip()

# https://docs.gitlab.com/ee/api/#personal-access-tokens
GITLAB_API_AUTHORIZATION_HEADER = {"PRIVATE-TOKEN": GITLAB_BOT_TOKEN}
GITLAB_API_URL = f"https://git.gesis.org/api/v4/"
GITLAB_ORG_NAME = os.environ.get("GITLAB_ORG_NAME", "ilcm")
GITLAB_REPO_NAME = os.environ.get("GITLAB_REPO_NAME", "orc2")
GITLAB_PROJECT_ID_ENCODED = f"{GITLAB_ORG_NAME}%2F{GITLAB_REPO_NAME}"
GITLAB_REPO_URL = f"https://oauth2:{GITLAB_BOT_TOKEN}@git.gesis.org/{GITLAB_ORG_NAME}/{GITLAB_REPO_NAME}"

GITHUB_ORG_NAME = os.environ.get("GITHUB_ORG_NAME", "gesiscss")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME", "orc2")
GITHUB_REPO_RAW_URL = (
    f"https://raw.githubusercontent.com/{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/main/"
)

MYBINDER_REPO_URL = "https://github.com/jupyterhub/mybinder.org-deploy/"
MYBINDER_REPO_RAW_URL = (
    "https://raw.githubusercontent.com/jupyterhub/mybinder.org-deploy/"
)


class Bot:
    """
    Class for a bot that determines whether an upgrade is necessary
    for GESIS Binder depending on if repo2docker and BinderHub is updated on mybinder.org.
    If an upgrade is needed, it will checkout into <repo>_bump branch,
    edit files and create a PR.
    """

    def __init__(self):
        """
        Start by getting the latest commits of repo2docker, BinderHub and Jupyterhub in mybinder.org
        and the live ones in GESIS Binder.
        """
        self.chart_sync = {
            "binderhub": None,
            "prometheus": None,
            "grafana": None,
            "cryptnono": None,
        }
        self.config_sync = {
            "build_image": None,
        }

        response = requests.get(f"{GITHUB_REPO_RAW_URL}helm/charts/gesis/Chart.yaml")
        self.orc2_chart = load(response.text, Loader=Loader)
        self.orc2_chart_new = copy.deepcopy(self.orc2_chart)
        response = requests.get(f"{GITHUB_REPO_RAW_URL}helm/charts/gesis/values.yaml")
        self.orc2_config = load(response.text, Loader=Loader)
        self.orc2_config_new = copy.deepcopy(self.orc2_config)

        response = requests.get(f"{MYBINDER_REPO_RAW_URL}main/mybinder/Chart.yaml")
        self.mybinder_chart = load(response.text, Loader=Loader)
        response = requests.get(f"{MYBINDER_REPO_RAW_URL}main/mybinder/values.yaml")
        self.mybinder_config = load(response.text, Loader=Loader)

    def update_repo(self):
        """
        Main method to check/create upgrades
        """
        self.sync_chart()

        self.sync_config()

    def sync_chart(self):
        create_merge_request = False

        for dependency_name in self.chart_sync:
            orc2_version = None
            orc2_idx = None
            mybinder_version = None

            for idx, orc2_dependency in enumerate(self.orc2_chart["dependencies"]):
                if orc2_dependency["name"] == dependency_name:
                    orc2_version = orc2_dependency["version"]
                    orc2_idx = idx

            for mybinder_dependency in self.mybinder_chart["dependencies"]:
                if mybinder_dependency["name"] == dependency_name:
                    mybinder_version = mybinder_dependency["version"]

            if orc2_version == mybinder_version:
                logging.debug(f"{dependency_name} has the same version.")
                self.chart_sync[dependency_name] = True
            else:
                logging.debug(f"{dependency_name} need sync.")
                create_merge_request = True

                self.chart_sync[dependency_name] = False
                self.orc2_chart_new["dependencies"][orc2_idx][
                    "version"
                ] = mybinder_version

        if create_merge_request:
            logging.debug(f"Create new branch.")
            response = requests.post(
                f"{GITLAB_API_URL}/projects/{GITLAB_PROJECT_ID_ENCODED}/repository/branches?branch=chart-sync&ref=main",
                headers=GITLAB_API_AUTHORIZATION_HEADER,
            )
            logging.debug(response.text)

            logging.debug(f"Update file.")
            response = requests.post(
                f"{GITLAB_API_URL}/projects/{GITLAB_PROJECT_ID_ENCODED}/repository/files/helm/charts%2Fgesis%2FChart%2Eyaml",
                headers=GITLAB_API_AUTHORIZATION_HEADER,
                json={
                    "branch": "chart-sync",
                    "author_email": GITLAB_BOT_EMAIL,
                    "author_name": GITLAB_BOT_NAME,
                    "content": dump(self.orc2_chart_new, Dumper=Dumper),
                    "commit_message": "Sync Chart file",
                },
            )
            logging.debug(response.text)

            logging.debug(f"Create merge request.")
            response = requests.post(
                f"{GITLAB_API_URL}/projects/{GITLAB_PROJECT_ID_ENCODED}/merge_requests",
                headers=GITLAB_API_AUTHORIZATION_HEADER,
                json={
                    "source_branch": "chart-sync",
                    "target_branch": "main",
                    "title": "Sync Helm Chart with mybinder.org",
                },
            )
            logging.debug(response.text)

    def sync_config(self):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="GESIS Notebooks Sync Bot",
        description="Sync Helm Chart with mybinder.org",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-vv", "--debug", action="store_true")
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    b = Bot()
    b.update_repo()
