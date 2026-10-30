"""Publish the BeaconMind car's robot description and TF tree (M2.T4 step 6).

AI-assisted: Claude Opus 5.5 (xhigh effort) via Claude Code, 2026-10-10: wrote the URDF/xacro, launch file and tests.

Runs xacro on urdf/beaconmind_car.urdf.xacro from this package's share folder and starts
robot_state_publisher with the result. Fixed frames (chassis_link, caster_link, camera_link,
camera_optical_frame, imu_link) go out on /tf_static at once; the two wheel frames appear only once
something publishes /joint_states (the simulator or the car's wheel encoders).

    ros2 launch beaconmind_description description.launch.py
    ros2 launch beaconmind_description description.launch.py use_sim_time:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    use_sim_time = LaunchConfiguration("use_sim_time")
    xacro_file = PathJoinSubstitution(
        [FindPackageShare("beaconmind_description"), "urdf", "beaconmind_car.urdf.xacro"]
    )
    robot_description = ParameterValue(Command(["xacro ", xacro_file]), value_type=str)

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[
            {
                "robot_description": robot_description,
                "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
            }
        ],
        output="screen",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="false",
                description="Use the simulator's /clock (true in the Isaac twin or Gazebo, false on the real car)",
            ),
            robot_state_publisher,
        ]
    )
