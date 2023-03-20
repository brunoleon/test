#!/usr/bin/env python3
"""
Check version at http://release-monitoring.org against ours
in OBS.
"""
import logging
from typing import Any, Literal, NoReturn, TypedDict, overload
from typing_extensions import NotRequired
import requests
import yaml
import subprocess
import csv
import shutil
import sys
import time
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)

# Anitya URL to use
SERVER_URL = "https://release-monitoring.org/"
OBS_URL = "https://api.opensuse.org"
# Number of items to request per page
# Let's use maximum page size, so we don't do too much requests
ITEMS_PER_PAGE = 250
CONFIG = "config.yaml"
IMAGES = ['opensuse/leap:15.4', 'registry.suse.com/bci/bci-base:15.4',
          'registry.suse.com/bci/bci-base:15.3']


class ConfigProject(TypedDict):
    id: None | str
    distribution: list[str]
    real_name: NotRequired[str]
    suse_name: NotRequired[str]

class Config(TypedDict):
    projects: dict[str, ConfigProject]

class ProjectsParams(TypedDict, total=False):
    page: int
    items_per_page: int
    ecosystem: str
    name: str

class ProjectResponse(TypedDict):
    backend: str
    created_on: float
    ecosystem: str
    homepage: str
    id: int
    name: str
    regex: str
    updated_on: float
    version: str
    version_url: str
    versions: list[str]
    stable_versions: list[str]

class ProjectsResponse(TypedDict):
    items: list[ProjectResponse]
    items_per_page: int
    page: int
    total_items: int

class VersionsParams(TypedDict, total=False):
    project_id: int

class VersionsResponse(TypedDict):
    latest_version: str
    versions: list[str]
    stable_versions: list[str]

def main() -> None:
    if get_container_engine() is None:
        logger.error('You need either podman/docker installed')
        sys.exit(1)

    with open(CONFIG) as file:
        config: Config = yaml.safe_load(file)

    projects = gen_projects(config)
    get_suse_versions(projects)
    build_report(projects)


def build_report(projects: dict[str, "Project"]) -> None:
    mylist = []
    for project in projects.keys():
        data = {
            'package': project,
            'upstream': projects[project].version
        }
        for os in projects[project].suse_versions:
            data[os] = projects[project].suse_versions[os]
        mylist.append(data)

    with open('report.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        writer.writeheader()
        writer.writerows(mylist)


def get_suse_versions(projects: dict[str, "Project"]) -> None:
    for image in IMAGES:
        logger.info(f'Launching {image} based container')
        c = Container("release_monitoring", image)
        c.create()
        for project in projects.keys():
            os = image.split('/')[-1]
            projects[project].suse_versions[os] = c.get_version(
                projects[project].suse_name)
        c.delete()

def gen_projects(config: Config) -> dict[str, "Project"]:
    projects: dict[str, Project] = {}
    for k, v in config["projects"].items():
        logger.info(f'Processing project: {k}')
        projects[k] = Project(k, v)
        if projects[k].get_versions_rm() is None:
            projects[k].get_versions_lv()
        time.sleep(1)
    return projects

def get_container_engine() -> Literal['podman', 'docker'] | None:
    """Check if we are running podman or docker"""
    for engine in ['podman', 'docker']:
        if shutil.which(engine) is not None:
            logger.info(f'Using {engine} as container engine')
            return engine
    else:
        return None

class Container:
    def __init__(self, name: str, image: str) -> None:
        self.name: str = name
        self.image: str = image

        engine = get_container_engine()
        if not engine:
            raise RuntimeError("No container engine present")
        self.engine = engine

    def create(self) -> None:
        subprocess.run(
            [self.engine, "run", "--rm", "--name", self.name, "-d",
            self.image, "sleep", "1800"])
        self.exec("refresh")

    def delete(self) -> None:
        subprocess.run([self.engine, "rm", "-f", self.name])

    def exec(self, cmd: str) -> None:
        subprocess.run(
            [self.engine, "exec", self.name, cmd],
            capture_output=True)

    def get_version(self, pkg: str) -> str | None:
        """Get the package version available on this container"""
        v = subprocess.run(
            [self.engine, "exec", self.name, "zypper", "-q", "info", pkg],
            capture_output=True)
        res = v.stdout.decode().split('\n')
        try:
            version = [x for x in res if x.startswith("Version")][0].split(':')[-1].strip()
        except:
            logger.error(f"Unable to parse zypper output: {res}")
            version = None
        return version


class Project:
    def __init__(self, name: str, metadata: ConfigProject) -> None:
        self.name: str = name
        self.branch: str | None = None
        if 'real_name' in metadata:
            self.real_name = metadata['real_name']
            self.branch = name.split(self.real_name)[-1]
        else:
            self.real_name = name
        if 'suse_name' in metadata:
            self.suse_name = metadata['suse_name']
        else:
            self.suse_name = name
        self.id = self.get_project_id()
        self.version: str | None = None
        self.suse_versions: dict[str, str | None] = {}


    def get_project_id(self) -> int | None:
        """Get project id from name"""
        result = None
        params: ProjectsParams = {
            "name": self.real_name
        }
        q = self.query_get("api/v2/projects", params)
        if q["items"]:
            result = q["items"][0]["id"]
        return result

    def get_versions_rm(self) -> str | None:
        """Get package version from anitya"""
        if self.version is not None:
            return self.version

        params: VersionsParams = {
            "project_id": self.id
        }
        q = self.query_get("api/v2/versions", params)
        if q is not None:
            if self.branch:
                n = [i for i in q['stable_versions'] if re.match(self.branch, i)]
                self.version = n[0]
            else:
                self.version = q['stable_versions'][0]
        return self.version

    def get_versions_lv(self) -> str | None:
        """Get package version using 'lastversion' tool"""
        if self.version is not None:
            return self.version
        v = subprocess.run(["lastversion", self.name], capture_output=True)
        self.version = v.stdout.decode().strip()
        return self.version

    def get_version_obs(self) -> NoReturn:
        """
        Get a project version in SUSE OBS
        """
        #https://api.opensuse.org/build/openSUSE:Factory/standard/x86_64/helm
        raise NotImplementedError()


    def add_to_anitya(self) -> NoReturn:
        """
        Add a project to release-monitoring if not present
        """
        raise NotImplementedError()

    @overload
    def query_get(self, path: str = "/api/v2/projects", params: ProjectsParams|None = None) -> ProjectsResponse: ...

    @overload
    def query_get(self, path: str = "/api/v2/versions", params: VersionsParams|None = None) -> VersionsResponse: ...

    def query_get(self, path: str, params: VersionsParams | ProjectsParams | None) -> Any | None:
        result = None
        resp = requests.get(SERVER_URL + path, params=params)
        if resp.status_code == 200:
            result = resp.json()
        else:
            logger.error("ERROR: Wrong arguments for request '{}'".format(resp.url))
        return result

if __name__ == "__main__":
    main()