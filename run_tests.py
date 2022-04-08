#!/usr/bin/env python3

import argparse
import subprocess
import os
import sys
import time
from tempfile import TemporaryDirectory
import platform

wwiseroot_env = os.environ["WWISEROOT"] if "WWISEROOT" in os.environ else None

parser = argparse.ArgumentParser()
optional_arguments = parser.add_argument_group("Optional named arguments.")
optional_arguments.add_argument("-w", "--wwiseroot", required=wwiseroot_env==None, help="Path to WwiseConsole.exe.")
optional_arguments.add_argument("-p", "--python-versions", help="Python version to run", nargs="+", choices=["37", "38", "39"])
args = parser.parse_args()

print(f"Running tests on {args.python_versions}.")

tox_results = []
wwiseroot = args.wwiseroot if args.wwiseroot != None else wwiseroot_env

platform_roots = {
    "Windows": [os.path.join("Authoring", "x64", "Release", "bin", "WwiseConsole.exe")],
    "darwin": [os.path.join("Authoring", "macosx_gmake", "Release", "bin", "WwiseConsole"), os.path.join("Authoring", "macosx_xcode4", "Release", "bin", "WwiseConsole")],
    "linux": [os.path.join("Authoring", "linux_gmake", "Release", "bin", "WwiseConsole")]
}.get(platform.system())

wwiseconsole_path = None
for platform_root in platform_roots:
    path = os.path.join(wwiseroot, platform_root)
    if os.path.exists(path):
        wwiseconsole_path = path
        break

if not wwiseconsole_path:
    print("Error: Wwise Authoring was not found.")
    sys.exit(1)

with TemporaryDirectory() as temp_dir:
    path_new_project = os.path.join(temp_dir, "WaapiClientPython", "WaapiClientPython.wproj")
    # Create new wwise project
    command = [wwiseconsole_path, "create-new-project", path_new_project, "--platform", "Windows"]
    subprocess.run(command)

    # Open Project
    command = [wwiseconsole_path, "waapi-server", path_new_project]
    wwiseconsole_project_open = subprocess.Popen(command)
    time.sleep(5)

    command = ["tox"]

    # Add the specifiecd python versions
    if args.python_versions:
        command.append("-e")
        command += [f"py{python_version}" for python_version in args.python_versions]

    tox_result = subprocess.run(command)
    wwiseconsole_project_open.terminate()

sys.exit(tox_result.returncode)
