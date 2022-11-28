#!/usr/bin/env python3
"""
Check version at http://release-monitoring.org against ours
in OBS.
"""
import logging
import requests
import yaml
import subprocess

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
    with open(CONFIG) as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    projects = {}
    for k, v in config["projects"].items():
        logger.info(f'Processing project: {k}')
        projects[k] = Project(k, v['id'])
        print(projects[k].get_versions())


    c = Container("release_monitoring")
    c.create()
    for project in projects.keys():
        c.get_version(project)
    c.delete()

class Container:
    def __init__(self, name) -> None:
        self.name = name

    def create(self):
        subprocess.run(
            ["docker", "run", "--rm", "--name", self.name, "-d",
            "opensuse/leap", "sleep", "60"])
        self.run("refresh")

    def delete(self):
        subprocess.run(["docker", "rm", "-f", self.name])
        self.run("refresh")

    def run(self, cmd):
        subprocess.run(
            ["docker", "exec", self.name, cmd],
            capture_output=True)

    def get_version(self, pkg):
        v = subprocess.run(
            ["docker", "exec", self.name, "zypper", "-q", "info", pkg],
            capture_output=True)
        res = v.stdout.decode().split('\n')
        version = [x for x in res if x.startswith("Version")][0].split(':')[-1].strip()
        print(version)
        return version

class Project:
    def __init__(self, name, id=None) -> None:
        self.name = name
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

    def get_versions(self):
        params = {
            "project_id": self.id
        }
        q = self.query_get("api/v2/versions", params)
        return q

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
            print("ERROR: Wrong arguments for request '{}'".format(resp.url))
        return result


if __name__ == "__main__":
    main()