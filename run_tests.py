#!/usr/bin/env python3

from configparser import ConfigParser
from tempfile import TemporaryDirectory

import argparse
import os
import platform
import subprocess
import sys
import time

script_dir = os.path.dirname(os.path.realpath(__file__))

tox_config = ConfigParser()

if not tox_config.read(os.path.join(script_dir, "tox.ini")):
    print("Error: tox.ini was not found", file=sys.stderr)
    sys.exit(1)
python_version_choices = tox_config["tox"]["envlist"].split(",")

wwiseroot_env = os.environ["WWISEROOT"] if "WWISEROOT" in os.environ else None

parser = argparse.ArgumentParser()
optional_arguments = parser.add_argument_group("Optional named arguments.")
optional_arguments.add_argument("-p", "--python-versions", help="Python version to run", nargs="+", choices=python_version_choices)
optional_arguments.add_argument("-w", "--wwiseroot-path", required=False, help="Override the path to the Wwise Root")
optional_arguments.add_argument("-c", "--console-path", required=False, help="Override the path to the WwiseConsole executable")
args = parser.parse_args()

print(f"Running tests on {args.python_versions}.")

tox_results = []

wwiseconsole_path = None
if args.console_path:
    wwiseconsole_path = args.console_path
else:
    wwiseroot = args.wwiseroot if args.wwiseroot is not None else wwiseroot_env

    if not wwiseroot:
        print("Error: Cannot find WwiseConsole executable", file=sys.stderr)
        print("Pass --console-path or --wwiseroot, or define the WWISEROOT environment variable")
        sys.exit(1)

    platform_roots = {
        "Windows": [os.path.join("Authoring", "x64", "Release", "bin", "WwiseConsole.exe")],
        "Darwin": [os.path.join("Authoring", "macosx_gmake", "Release", "bin", "WwiseConsole"), os.path.join("Authoring", "macosx_xcode4", "Release", "bin", "WwiseConsole")],
        "Linux": [os.path.join("Authoring", "linux_gmake", "Release", "bin", "WwiseConsole")]
    }.get(platform.system())

    wwiseconsole_path = None
    for platform_root in platform_roots:
        path = os.path.join(wwiseroot, platform_root)
        if os.path.exists(path):
            wwiseconsole_path = path
            break

if not wwiseconsole_path:
    print("Error: Wwise Authoring was not found", file=sys.stderr)
    sys.exit(1)

with TemporaryDirectory() as temp_dir:
    path_new_project = os.path.join(temp_dir, "WaapiClientPython", "WaapiClientPython.wproj")
    # Create new wwise project
    command = [wwiseconsole_path, "create-new-project", path_new_project, "--platform", "Windows"]
    subprocess.run(command, check=False)

    # Open Project
    command = [wwiseconsole_path, "waapi-server", path_new_project]
    wwiseconsole_project_open = subprocess.Popen(command)
    time.sleep(5)

    command = ["tox"]

    # Add the specified python versions
    if args.python_versions:
        command += [f"-e {python_version}" for python_version in args.python_versions]

    tox_result = subprocess.run(command, check=False)
    wwiseconsole_project_open.terminate()

sys.exit(tox_result.returncode)
