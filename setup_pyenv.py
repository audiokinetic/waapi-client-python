#!/usr/bin/env python3

import pkg_resources
import subprocess
import os
import sys

script_dir = os.path.dirname(os.path.realpath(__file__))

# Set up pyenv local environment, if pyenv is installed
exit_code, versions_string = subprocess.getstatusoutput("pyenv versions --bare")
if exit_code == 0:
    installed_versions = [pkg_resources.parse_version(version) for version in versions_string.split("\n")]
    if not installed_versions:
        print("Error: No version of Python installed in pyenv", file=sys.stderr)
        sys.exit(1)

    installed_versions.sort(reverse=True) # Most recent first

    # Enable all python versions
    subprocess.run(
        ["pyenv", "local", *(str(version) for version in installed_versions)],
        cwd=script_dir,
        check=False
    )
