"""Install beaconmind_bringup launch and config files.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the ament_python setup.
"""

import os
from glob import glob

from setuptools import find_packages, setup

package_name = "beaconmind_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.launch.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Xiaohui Chen",
    maintainer_email="xhchen0328@utexas.edu",
    description="BeaconMind Humble bringup for the apriltag smoke graph.",
    license="Proprietary",
    entry_points={
        "console_scripts": [],
    },
)
