#!/usr/bin/env python3
"""
Check version at http://release-monitoring.org against ours
in OBS.
"""
import time
import requests
import yaml

# Anitya URL to use
SERVER_URL = "https://release-monitoring.org/"
# Number of items to request per page
# Let's use maximum page size, so we don't do too much requests
ITEMS_PER_PAGE = 250
CONFIG = "projects.yaml"

def main():
    with open(CONFIG) as file:
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        config = yaml.load(file, Loader=yaml.FullLoader)

    projects = {}
    for k, v in config["projects"].items():
        projects[k] = Project(k, v['id'])
        print(projects[k].get_versions())


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