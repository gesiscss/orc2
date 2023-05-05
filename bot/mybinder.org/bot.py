"""
Derived from henchbot.py script: https://github.com/henchbot/mybinder.org-upgrades/blob/master/src/mybinder-upgrades/henchbot.py
"""

import argparse
import copy
import logging
import os
import re
import shutil
import subprocess
import time

import requests

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
    f"https://raw.githubusercontent.com/{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/master/"
)

BHUB_RAW_URL = "https://raw.githubusercontent.com/jupyterhub/binderhub/"

MYBINDER_REPO_URL = f"https://github.com/jupyterhub/mybinder.org-deploy/"
MYBINDER_REPO_RAW_URL = (
    f"https://raw.githubusercontent.com/jupyterhub/mybinder.org-deploy/"
)


# https://github.com/henchbot/mybinder.org-upgrades/commit/5222ba1466c6005221fdc9e641b32910b381b7a3
def normalize_r2d_tags(old, new):
    if "dirty" in old or ".g" in old:
        # it is a version string from which we can get a SHA
        old = old.split(".dirty")[0].split(".")[-1][1:]
    else:
        # it is (probably) a tag, use it direcctly
        old = old

    if "dirty" in new or ".g" in new:
        # it is a version string from which we can get a SHA
        new = new.split(".dirty")[0].split(".")[-1][1:]
    else:
        # it is (probably) a tag, use it direcctly
        new = new
    return old, new


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

        response = requests.get(
            "https://raw.githubusercontent.com/gesiscss/orc2/main/helm/charts/gesis/Chart.yaml"
        )
        self.orc2_chart = load(response.text, Loader=Loader)
        self.orc2_chart_new = copy.deepcopy(self.orc2_chart)
        response = requests.get(
            "https://raw.githubusercontent.com/gesiscss/orc2/main/helm/charts/gesis/values.yaml"
        )
        self.orc2_config = load(response.text, Loader=Loader)
        self.orc2_config_new = copy.deepcopy(self.orc2_config)

        response = requests.get(
            "https://raw.githubusercontent.com/jupyterhub/mybinder.org-deploy/main/mybinder/Chart.yaml"
        )
        self.mybinder_chart = load(response.text, Loader=Loader)
        response = requests.get(
            "https://raw.githubusercontent.com/jupyterhub/mybinder.org-deploy/main/mybinder/values.yaml"
        )
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

    def set_gitlab_project_id(self, repo_name):
        projects = requests.get(
            f"{GITLAB_API_URL}projects?search={repo_name}",
            headers=GITLAB_API_AUTHORIZATION_HEADER,
        ).json()
        for project in projects:
            if project["name"] == repo_name:
                self.gitlab_project_id = project["id"]
                break

    def check_existing_prs(self, repo):
        """
        Check if there are open PRs created by bot
        """
        # https://docs.gitlab.com/ee/api/merge_requests.html#list-merge-requests
        prs = requests.get(
            GITLAB_API_URL + "merge_requests?state=opened",
            headers=GITLAB_API_AUTHORIZATION_HEADER,
        ).json()
        for pr in prs:
            if repo in pr["title"].lower():
                pr_latest = pr["title"].split("...")[-1].strip()
                if pr_latest == self.commit_info[repo]["latest"]:
                    # same update, pr is not merged yet
                    return None
                return {
                    "iid": pr["iid"]
                }  # iid is unique only in scope of a single project
        return False

    def check_branch_exists(self):
        # https://docs.gitlab.com/ee/api/branches.html#list-repository-branches
        branches = requests.get(
            f"{GITLAB_API_URL}/projects/{self.gitlab_project_id}/repository/branches",
            headers=GITLAB_API_AUTHORIZATION_HEADER,
        ).json()
        return self.branch_name in [b["name"] for b in branches]

    def delete_old_branch_if_exists(self):
        if self.check_branch_exists():
            # https://docs.gitlab.com/ee/api/branches.html#delete-repository-branch
            res = requests.delete(
                f"{GITLAB_API_URL}/projects/{self.gitlab_project_id}/repository/branches/{self.branch_name}",
                headers=GITLAB_API_AUTHORIZATION_HEADER,
            )
            assert res.status_code == 204

    def edit_files(self, repo):
        """
        Controlling method to update file for the repo
        """
        pass

    def add_commit_push(self, files_changed, repo):
        """
        After making change, add, commit and push to fork
        """
        for f in files_changed:
            subprocess.check_call(["git", "add", f])

        commit_message = "Update from bot"

        subprocess.check_call(["git", "config", "user.name", GITLAB_BOT_NAME])
        subprocess.check_call(["git", "config", "user.email", GITLAB_BOT_EMAIL])
        subprocess.check_call(["git", "commit", "-m", commit_message])
        if self.check_branch_exists():
            # there is an open PR for this repo, so update it
            subprocess.check_call(
                ["git", "push", "-f", GITLAB_REPO_URL, self.branch_name]
            )
        else:
            subprocess.check_call(["git", "push", GITLAB_REPO_URL, self.branch_name])

    def get_associated_prs(self, compare_url):
        """
        Gets all PRs from dependency repo associated with the upgrade
        """
        repo_api = compare_url.replace("github.com", "api.github.com/repos")
        res = requests.get(repo_api).json()
        if "commits" not in res or not res["commits"]:
            logging.error(
                "Compare url returns no commits but there must be commits. "
                "Something must be wrong with compare url."
            )
        commit_shas = [x["sha"] for x in res["commits"]]

        pr_api = repo_api.split("/compare/")[0] + "/pulls/"
        associated_prs = ["Associated PRs:"]
        for sha in commit_shas[::-1]:
            res = requests.get(
                "https://api.github.com/search/issues?q=sha:{}".format(sha)
            ).json()
            if "items" in res:
                for i in res["items"]:
                    formatted = "- {} [#{}]({})".format(
                        i["title"], i["number"], i["html_url"]
                    )
                    repo_owner = i["repository_url"].split("/")[-2]
                    try:
                        merged_at = requests.get(pr_api + str(i["number"])).json()[
                            "merged_at"
                        ]
                    except KeyError:
                        continue
                    if (
                        formatted not in associated_prs
                        and repo_owner.startswith("jupyter")
                        and merged_at
                    ):
                        associated_prs.append(formatted)
            time.sleep(3)

        return associated_prs

    def make_pr_body(self, repo):
        """
        Formats a text body for the PR
        """
        if repo == "repo2docker":
            old, new = normalize_r2d_tags(
                self.commit_info["repo2docker"]["live"],
                self.commit_info["repo2docker"]["latest"],
            )
            compare_url = (
                "https://github.com/jupyterhub/repo2docker/compare/{}...{}".format(
                    old, new
                )
            )
        elif repo == "binderhub":
            compare_url = (
                "https://github.com/jupyterhub/binderhub/compare/{}...{}".format(
                    self.bhub_live, self.bhub_latest
                )
            )
        logging.info("compare url: {}".format(compare_url))
        associated_prs = self.get_associated_prs(compare_url)
        body = "\n".join(
            [
                f"This is a {repo} version bump. See the link below for a diff of new changes:\n",
                compare_url + " \n",
            ]
            + associated_prs
        )
        return body

    def create_update_pr(self, repo, existing_pr):
        """
        Makes the PR from all components
        """
        body = self.make_pr_body(repo)
        title = f"{repo}: {self.commit_info[repo]['live']}...{self.commit_info[repo]['latest']}"
        params = {
            "source_branch": self.branch_name,
            "target_branch": "master",
            "title": title,
            "description": f"{body}",
        }
        if existing_pr:
            # update title and description of existing PR
            # https://docs.gitlab.com/ee/api/merge_requests.html#update-mr
            res = requests.put(
                f"{GITLAB_API_URL}projects/{self.gitlab_project_id}/merge_requests/{existing_pr['iid']}",
                params=params,
                headers=GITLAB_API_AUTHORIZATION_HEADER,
            )
        else:
            # https://docs.gitlab.com/ee/api/merge_requests.html#create-mr
            res = requests.post(
                f"{GITLAB_API_URL}projects/{self.gitlab_project_id}/merge_requests",
                params=params,
                headers=GITLAB_API_AUTHORIZATION_HEADER,
            )
        logging.info(f"PR done: {title}")

    def get_repo2docker_live(self):
        """
        Get the live r2d SHA from GESIS Notebooks
        """
        # Load master repo2docker
        url_helm_chart = f"{GITHUB_REPO_RAW_URL}gesisbinder/gesisbinder/values.yaml"
        helm_chart = requests.get(url_helm_chart)
        helm_chart = load(helm_chart.text)
        r2d_live = helm_chart["binderhub"]["config"]["BinderHub"]["build_image"].split(
            ":"
        )[-1]
        self.commit_info["repo2docker"]["live"] = r2d_live

    def get_binderhub_live(self):
        """
        Get the latest BinderHub SHA from GESIS Notebooks
        """
        # Load master requirements
        url_requirements = (
            f"{GITHUB_REPO_RAW_URL}gesisbinder/gesisbinder/requirements.yaml"
        )
        requirements = load(requests.get(url_requirements).text)
        binderhub_dep = [
            ii for ii in requirements["dependencies"] if ii["name"] == "binderhub"
        ][0]
        bhub_live = binderhub_dep["version"].strip()
        self.commit_info["binderhub"]["live"] = bhub_live

    def get_jupyterhub_live(self):
        """
        Get the live JupyterHub SHA from BinderHub repo
        """
        url_binderhub_requirements = (
            f"{BHUB_RAW_URL}{self.bhub_live}/helm-chart/binderhub/Chart.yaml"
        )
        requirements = load(requests.get(url_binderhub_requirements).text)
        logging.info(url_binderhub_requirements, requirements)
        jupyterhub_dep = [
            ii for ii in requirements["dependencies"] if ii["name"] == "jupyterhub"
        ][0]
        jhub_live = jupyterhub_dep["version"].strip()
        self.commit_info["jupyterhub"]["live"] = jhub_live

    def get_repo2docker_latest(self):
        """
        Get the latest r2d SHA from mybinder.org
        """
        # Load master repo2docker
        url_helm_chart = f"{MYBINDER_REPO_RAW_URL}master/mybinder/values.yaml"
        helm_chart = requests.get(url_helm_chart)
        helm_chart = load(helm_chart.text)
        r2d_latest = helm_chart["binderhub"]["config"]["BinderHub"][
            "build_image"
        ].split(":")[-1]
        self.commit_info["repo2docker"]["latest"] = r2d_latest
        self.commit_info["repo2docker"][
            "repo_latest"
        ] = f"quay.io/jupyterhub/repo2docker:{r2d_latest}"

    def get_binderhub_latest(self):
        """
        Get the latest BinderHub SHA from mybinder.org
        """
        # Load master requirements
        url_requirements = f"{MYBINDER_REPO_RAW_URL}master/mybinder/Chart.yaml"
        requirements = load(requests.get(url_requirements).text)
        binderhub_dep = [
            ii for ii in requirements["dependencies"] if ii["name"] == "binderhub"
        ][0]
        bhub_latest = binderhub_dep["version"].strip()
        self.commit_info["binderhub"]["latest"] = bhub_latest

    def get_jupyterhub_latest(self):
        """
        Get the live JupyterHub SHA from BinderHub repo
        """
        url_binderhub_requirements = (
            f"{BHUB_RAW_URL}{self.bhub_latest}/helm-chart/binderhub/Chart.yaml"
        )
        requirements = load(requests.get(url_binderhub_requirements).text)
        logging.info(url_binderhub_requirements, requirements)
        jupyterhub_dep = [
            ii for ii in requirements["dependencies"] if ii["name"] == "jupyterhub"
        ][0]
        jhub_latest = jupyterhub_dep["version"].strip()
        self.commit_info["jupyterhub"]["latest"] = jhub_latest

    def get_new_commits(self):
        """
        Main controlling method to get commit SHAs
        """
        # logging.info('Fetching latest commit SHAs for repo2docker, BinderHub and JupyterHub that deployed on GESIS Binder')
        self.get_repo2docker_live()
        self.get_binderhub_live()
        self.get_jupyterhub_live()

        # logging.info('Fetching latest commit SHAs for repo2docker, BinderHub and JupyterHub that deployed on mybinder.org')
        self.get_repo2docker_latest()
        self.get_binderhub_latest()
        self.get_jupyterhub_latest()

        logging.info(self.commit_info)

    def parse_chart_version(self, chart_version):
        """
        All cases: https://github.com/jupyterhub/chartpress#examples-chart-versions-and-image-tags
        - 0.8.0
        - 0.8.0-n004.hasdf123
        - 0.9.0-beta.1
        - 0.2.0-072.544c0b1
        - 0.9.0-beta.1.n001.hdfgh345
        """
        parts = chart_version.split("-")
        if len(parts) == 1:
            # stable version: 0.8.0
            return chart_version
        else:
            parts = chart_version.split("-")[-1].split(".")
            if (
                len(parts) == 2
                and not parts[0].startswith("n")
                and not parts[0].isdigit()
            ):
                # beta version: 0.9.0-beta.1
                return chart_version
            else:
                # dev: 0.8.0-n004.hasdf123 or 0.9.0-beta.1.n001.hdfgh345 or 0.2.0-072.544c0b1
                chart_version = parts[-1]
                if chart_version.startswith("h"):
                    chart_version = chart_version[1:]
                return chart_version

    @property
    def bhub_live(self):
        return self.parse_chart_version(self.commit_info["binderhub"]["live"])

    @property
    def bhub_latest(self):
        return self.parse_chart_version(self.commit_info["binderhub"]["latest"])


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
