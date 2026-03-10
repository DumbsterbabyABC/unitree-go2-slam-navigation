#!/usr/bin/env python3
"""
Checker_tobi
Kurzer Diagnose-Checker für RViz/KISS-ICP/LiDAR-Setup.
"""
import subprocess
import textwrap

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def check_topic_pub(topic):
    result = run(
        f"sudo docker exec unitree_ros2_container bash -c "
        f"'source /opt/ros/humble/setup.bash && ros2 topic info {topic} -v'"
    )
    return result.stdout


def check_topic_hz(topic):
    result = run(
        f"timeout 2 sudo docker exec unitree_ros2_container bash -c "
        f"'source /opt/ros/humble/setup.bash && ros2 topic hz {topic} --window 1 2>&1'"
    )
    return result.stdout


def main():
    print("Checker_tobi")
    print("=" * 60)

    print("[1] /tf und /tf_static Publisher")
    tf_info = run("sudo docker exec unitree_ros2_container bash -c 'source /opt/ros/humble/setup.bash && ros2 topic info /tf'")
    tf_static_info = run("sudo docker exec unitree_ros2_container bash -c 'source /opt/ros/humble/setup.bash && ros2 topic info /tf_static'")
    print(tf_info.stdout.strip() or tf_info.stderr.strip())
    print(tf_static_info.stdout.strip() or tf_static_info.stderr.strip())

    print("\n[2] Wichtige Topics: Publisher & Hz")
    topics = [
        "/utlidar/cloud_deskewed",
        "/utlidar/cloud",
        "/kiss/local_map",
        "/kiss/odometry",
        "/utlidar/robot_odom",
    ]
    for t in topics:
        print(f"\n- {t}")
        print(check_topic_pub(t).strip() or "(keine Info)")
        hz = check_topic_hz(t).strip()
        print(hz if hz else "(keine Hz Daten)")

    print("\n[3] Hinweise")
    print(textwrap.dedent("""
        Wenn /tf keine Publisher hat, gibt es keine gültigen Frames (z.B. odom).
        Dann erscheint in RViz "No tf data" oder "Frame does not exist".

        Wenn /utlidar/cloud_deskewed keine Daten liefert, kann die Karte verzerrt wirken.
        Falls nur /utlidar/cloud Daten hat, teste KISS-ICP mit diesem Topic.

        Bei chaotischer Karte:
        - LiDAR-Extrinsics (Position/Quaternion) prüfen
        - Roboter still halten (Test)
        - QoS der PointCloud2 Displays anpassen
        - Zeit-Sync prüfen (Sensorzeit vs. Systemzeit)
    """).strip())


if __name__ == "__main__":
    main()
