#!/usr/bin/env python3
"""
This script will retrieve packages names for partial names defined in PARTIAL_NAMES constant.
It will actually retrieves all the packages from Anitya and then tries to match the partial name.
"""
import time

import requests

# Generate delete url for Anitya to delete the package
GENERATE_DELTE_URL = True
# List of partial names to look for
PARTIAL_NAMES = ["helm", "kubernetes"]
# Anitya URL to use
SERVER_URL = "https://release-monitoring.org/"
# Number of items to request per page
# Let's use maximum page size, so we don't do too much requests
ITEMS_PER_PAGE = 250
# Wait time before retry of the request
WAIT_TIME = 0.5


def get_all_packages():
    """
    Get all packages in Anitya..

    Returns:
      (list): List of packages in Anitya represented as dict containing name,
              distribution, project, ecosystem.
    """
    packages_list = []
    run = True
    page = 0
    while(run):
        page = page + 1
        request_failure = True
        print("toto")
        while(request_failure):
            try:
                packages_list_page = _request_anitya_packages_page(page)
            except requests.ConnectionError:
                print("Connection error occurred, waiting for '{}' second before retry".format(
                    WAIT_TIME
                ))
                time.sleep(WAIT_TIME)
            else:
                request_failure = False
        if len(packages_list_page) < ITEMS_PER_PAGE:
            run = False
        packages_list = packages_list + packages_list_page

    return packages_list


def _request_anitya_packages_page(page):
    """
    Sent paged request to Anitya.

    Returns:
      (list): List of packages in Anitya represented as dict containing name,
              distribution, project, ecosystem for the provided page.
    """
    packages_list = []
    params = {
        "items_per_page": ITEMS_PER_PAGE,
        "page": page
    }
    resp = requests.get(SERVER_URL + "api/v2/packages", params=params)
    #print(resp.url)
    if resp.status_code == 200:
        response_dict = resp.json()
        for item in response_dict["items"]:
            packages_list.append(item)
    else:
        print("ERROR: Wrong arguments for request '{}'".format(resp.url))

    return packages_list


def filter_packages(packages):
    """
    Filter list of packages dict by the PARTIAL_NAMES list.

    Params:
      (list): List of packages represented as dict containing name,
              distribution, project, ecosystem.

    Returns:
      (list): List of packages represented as dict containing name,
              distribution, project, ecosystem for the provided page
              filtered by PARTIAL_NAMES list.
    """
    filtered_list = []
    for package in packages:
        for partial_name in PARTIAL_NAMES:
            if partial_name.lower() in package["name"].lower():
                filtered_list.append(package)


    return filtered_list


def get_project_id(project):
    """
    Get project id from name.

    Params:
        project (str): Project name

    Returns:
        (str): Project id
    """
    result = None
    if not project:
        return result

    params = {
        "name": project
    }
    resp = requests.get(SERVER_URL + "api/v2/projects", params=params)
    #print(resp.url)
    if resp.status_code == 200:
        response_dict = resp.json()
        if response_dict["items"]:
            result = response_dict["items"][0]["id"]
            print("Project '{}' has id '{}'".format(project, result))
        else:
            print("Package '{}' not found".format(project))
    else:
        print("ERROR: Wrong arguments for request '{}'".format(resp.url))

    return result


if __name__ ==  "__main__":
    packages = get_all_packages()
    filtered_packages = filter_packages(packages)
    for package in filtered_packages:
        checked = False
        while not checked:
            try:
                project_id = get_project_id(package["project"])
            except requests.ConnectionError:
                print("Connection error occurred, waiting for '{}' second before retry".format(
                    WAIT_TIME
                ))
                time.sleep(WAIT_TIME)
            else:
                checked = True
        if project_id:
            package["project_id"] = project_id

    for package in filtered_packages:
        print('###')
        print(package)
        print("{};{};{}".format(package["project_id"], package["distribution"], package["name"]))
