#!/usr/bin/env python3
"""Publish one PNG as a rectified camera image for the apriltag smoke test.

The node name is bm_test_image. It publishes sensor_msgs/Image (bgr8, frame
camera_optical_frame) on /camera/image_rect and sensor_msgs/CameraInfo on
/camera/camera_info at 5 Hz, then exits.

AI-assisted: Grok 4.7 via Cursor, 2026-10-06: wrote the synthetic image publisher.
Derived from: none (rclpy and OpenCV library calls only).
"""

import argparse
import sys
import time

import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image


FRAME_ID = "camera_optical_frame"


def qos_profile(name):
    if name == "reliable":
        return QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
    if name == "sensor_data":
        return QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
    raise ValueError("unknown qos {0}".format(name))


class TestImage(Node):
    def __init__(self, image_bgr, fx, fy, cx, cy, seconds, image_qos, info_qos):
        super().__init__("bm_test_image")
        self.image_bgr = image_bgr
        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = float(cx)
        self.cy = float(cy)
        self.deadline = time.monotonic() + float(seconds)
        self.finished = False
        height, width = image_bgr.shape[:2]
        self.width = int(width)
        self.height = int(height)
        self.image_pub = self.create_publisher(Image, "/camera/image_rect", qos_profile(image_qos))
        self.info_pub = self.create_publisher(CameraInfo, "/camera/camera_info", qos_profile(info_qos))
        self.timer = self.create_timer(0.2, self.publish_once)

    def publish_once(self):
        if time.monotonic() >= self.deadline:
            self.timer.cancel()
            self.finished = True
            return
        stamp = self.get_clock().now().to_msg()
        self.image_pub.publish(self.build_image(stamp))
        self.info_pub.publish(self.build_info(stamp))

    def build_image(self, stamp):
        msg = Image()
        msg.header.stamp = stamp
        msg.header.frame_id = FRAME_ID
        msg.height = self.height
        msg.width = self.width
        msg.encoding = "bgr8"
        msg.is_bigendian = 0
        msg.step = self.width * 3
        msg.data = self.image_bgr.tobytes()
        return msg

    def build_info(self, stamp):
        msg = CameraInfo()
        msg.header.stamp = stamp
        msg.header.frame_id = FRAME_ID
        msg.width = self.width
        msg.height = self.height
        msg.distortion_model = "plumb_bob"
        msg.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        msg.k = [self.fx, 0.0, self.cx, 0.0, self.fy, self.cy, 0.0, 0.0, 1.0]
        msg.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        msg.p = [self.fx, 0.0, self.cx, 0.0, 0.0, self.fy, self.cy, 0.0, 0.0, 0.0, 1.0, 0.0]
        return msg


def load_bgr(path, width, height):
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit("could not read {0}".format(path))
    got_h, got_w = image.shape[:2]
    if got_w != int(width) or got_h != int(height):
        raise SystemExit(
            "{0} is {1}x{2}, expected {3}x{4}".format(path, got_w, got_h, width, height)
        )
    if not image.flags["C_CONTIGUOUS"]:
        image = image.copy()
    return image


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Publish one PNG on /camera/image_rect.")
    parser.add_argument("image", help="PNG path")
    parser.add_argument("--fx", type=float, required=True)
    parser.add_argument("--fy", type=float, required=True)
    parser.add_argument("--cx", type=float, required=True)
    parser.add_argument("--cy", type=float, required=True)
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--seconds", type=float, required=True)
    parser.add_argument(
        "--image-qos",
        choices=("reliable", "sensor_data"),
        default="reliable",
        help="QoS for /camera/image_rect (installed apriltag_ros qos_profile default is 'default')",
    )
    parser.add_argument(
        "--info-qos",
        choices=("reliable", "sensor_data"),
        default="reliable",
        help="QoS for /camera/camera_info",
    )
    return parser.parse_args(argv)


def main(argv):
    args = parse_args(argv)
    image = load_bgr(args.image, args.width, args.height)
    rclpy.init()
    node = TestImage(
        image, args.fx, args.fy, args.cx, args.cy, args.seconds, args.image_qos, args.info_qos
    )
    try:
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
