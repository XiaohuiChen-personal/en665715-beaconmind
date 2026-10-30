"""Install beaconmind_description: the car's URDF/xacro files and its launch file.

AI-assisted: Claude Opus 5.5 (xhigh effort) via Claude Code, 2026-10-10: wrote the URDF/xacro, launch file and tests.
"""

import os
from glob import glob

from setuptools import find_packages, setup

package_name = "beaconmind_description"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "urdf"), glob("urdf/*.xacro")),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Xiaohui Chen",
    maintainer_email="xhchen0328@utexas.edu",
    description="URDF/xacro of the BeaconMind car and a launch file that publishes its TF tree.",
    license="Proprietary",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [],
    },
)
