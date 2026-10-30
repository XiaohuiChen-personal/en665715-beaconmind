# AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the apriltag smoke launch.
# Executable name is apriltag_ros's apriltag_node (confirmed against the Humble docs;
# M1.T3 step 8 re-checks `ros2 pkg executables apriltag_ros` before this is launched).

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("beaconmind_bringup")
    params = os.path.join(share, "config", "apriltag.yaml")
    return LaunchDescription(
        [
            Node(
                package="apriltag_ros",
                executable="apriltag_node",
                name="apriltag",
                output="screen",
                parameters=[params],
                remappings=[
                    ("image_rect", "/camera/image_rect"),
                    ("camera_info", "/camera/camera_info"),
                    ("detections", "/apriltag/detections"),
                ],
            )
        ]
    )
