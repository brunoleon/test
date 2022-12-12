#!/usr/bin/env python3
"""
Check version at http://release-monitoring.org against ours
in OBS.
"""
import logging
import requests
import yaml
import subprocess
import csv
import shutil
import sys

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
CONFIG = "projects.yaml"

def main():
    c = Container("release_monitoring")
    if c.engine is None:
        logger.error('You need either podman/docker installed')
        sys.exit(1)

    with open(CONFIG) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    projects = {}
    for k, v in config["projects"].items():
        logger.info(f'Processing project: {k}')
        projects[k] = Project(k, v['id'])
        if projects[k].get_versions_rm() is None:
            projects[k].get_versions_lv()

    c = Container("release_monitoring")
    c.create()
    for project in projects.keys():
        projects[project].suse_version = c.get_version(project)
    c.delete()

    mylist = []
    for project in projects.keys():
        data = {
            'package': project,
            'upstream': projects[project].version,
            'suse': projects[project].suse_version
            }
        mylist.append(data)

    with open('report.csv', 'w') as f:
        writer = csv.DictWriter(f, fieldnames=["package", "upstream", "suse"])
        writer.writeheader()
        writer.writerows(mylist)


class Container:
    def __init__(self, name) -> None:
        self.name = name
        self.engine = self.get_container_engine()

    def get_container_engine(self):
        for engine in ['podman', 'docker']:
            if shutil.which(engine) is not None:
                logger.info(f'Using {engine} as container engine')
                return engine
        else:
            return None

    def create(self):
        subprocess.run(
            [self.engine, "run", "--rm", "--name", self.name, "-d",
            "opensuse/leap", "sleep", "1800"])
        self.exec("refresh")

    def delete(self):
        subprocess.run([self.engine, "rm", "-f", self.name])

    def exec(self, cmd):
        subprocess.run(
            [self.engine, "exec", self.name, cmd],
            capture_output=True)

    def get_version(self, pkg):
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
    def __init__(self, name, id=None) -> None:
        self.name = name
        self.version = None
        self.suse_version = None
        if id is None:
            self.id = self.get_project_id(self.name)
        else:
            self.id = id

    def get_project_id(self, name):
        """
        Get project id from name.
        """
        result = None
        params = {
            "name": name
        }
        q = self.query_get("api/v2/projects", params)
        if q["items"]:
            result = q["items"][0]["id"]
        return result

    def get_versions_rm(self):
        if self.version is not None:
            return self.version
        params = {
            "project_id": self.id
        }
        q = self.query_get("api/v2/versions", params)
        if q is not None:
            self.version = q['latest_version']
        return self.version

    def get_versions_lv(self):
        if self.version is not None:
            return self.version
        v = subprocess.run(["lastversion", self.name], capture_output=True)
        self.version = v.stdout.decode().strip()
        return self.version

    def get_version_obs(self):
        """
        Get a project version in Suse OBS
        """
        #https://api.opensuse.org/build/openSUSE:Factory/standard/x86_64/helm
        pass


    def add_to_anitya(self):
        """
        Add a project to release-monitoring if not present
        """
        pass



    def query_get(self, path, params):
        result = None
        resp = requests.get(SERVER_URL + path, params=params)
        if resp.status_code == 200:
            result = resp.json()
        else:
            logger.error("ERROR: Wrong arguments for request '{}'".format(resp.url))
        return result


if __name__ == "__main__":
    main()