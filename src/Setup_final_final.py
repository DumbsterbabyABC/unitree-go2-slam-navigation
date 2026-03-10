#!/usr/bin/env python3
"""
Unitree Go2 – LiDAR Setup

Funktionen:
- Publiziert die statische Extrinsik base_link -> utlidar_lidar
- Startet KISS-ICP Odometry (ohne TF-Glue; Launch-Parameter wie im aktuellen Stand)
- Startet RViz2 zur visuellen Kontrolle
- Stoppt auf Wunsch alle zugehörigen Prozesse im Container

Hinweis:
- Das Verhalten entspricht dem aktuellen Skriptstand; es wurden nur Struktur, Lesbarkeit
  und Robustheit verbessert (keine Funktionsänderung).
"""

from __future__ import annotations

import math
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional


# =========================
# Konfiguration
# =========================

@dataclass(frozen=True)
class DockerConfig:
    container_name: str = "unitree_ros2_container"
    display: str = ":0"
    source_cmd: str = (
        "source /opt/ros/humble/setup.bash && "
        "source /basis/unitree_ros2/setup.sh && "
        "source /root/kiss_ws/install/setup.bash"
    )


@dataclass
class TransformRPY:
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float


@dataclass
class LidarConfig:
    # Statischer TF: base_link -> utlidar_lidar
    extrinsics: TransformRPY = TransformRPY(
        x=0.24,
        y=0.0,
        z=0.13,
        roll=0.0,
        pitch=0.0,
        yaw=0.0,
    )
    parent_frame: str = "base_link"
    child_frame: str = "utlidar_lidar"


@dataclass(frozen=True)
class KissConfig:
    # Start wie im aktuellen Stand (Launchfile), Parameter unverändert
    topic: str = "/utlidar/cloud"
    base_frame: str = "base_link"
    lidar_odom_frame: str = "odom"
    publish_odom_tf: bool = True
    invert_odom_tf: bool = True


DOCKER = DockerConfig()
LIDAR = LidarConfig()
KISS = KissConfig()


# =========================
# Hilfsfunktionen
# =========================

def run_host(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def docker_exec(cmd: str, *, background: bool = False, source: bool = True) -> subprocess.CompletedProcess:
    """
    Führt einen Befehl im Container aus.

    - background=True nutzt `docker exec -d` (kein stdout/stderr verfügbar)
    - source=True sourct ROS/Overlay im Container vor der Ausführung
    """
    source_prefix = f"{DOCKER.source_cmd} && " if source else ""
    d_flag = "-d" if background else ""

    full_cmd = (
        f"sudo docker exec {d_flag} "
        f"-e DISPLAY={DOCKER.display} "
        f"-e QT_X11_NO_MITSHM=1 "
        f"{DOCKER.container_name} bash -c '"
        f"export DISPLAY={DOCKER.display} && "
        f"{source_prefix}"
        f"{cmd}'"
    )
    return subprocess.run(full_cmd, shell=True, capture_output=not background, text=True)


def check_docker_or_exit() -> None:
    """Prüft, ob der Container läuft und ein ROS-Command ausführbar ist."""
    print(f"Prüfe Docker-Container '{DOCKER.container_name}' ...")

    res = run_host(f"sudo docker inspect -f '{{{{.State.Running}}}}' {DOCKER.container_name}")
    if res.stdout.strip() != "true":
        print(f"Fehler: Container '{DOCKER.container_name}' läuft nicht.")
        print(f"Starten mit: sudo docker start {DOCKER.container_name}")
        sys.exit(1)

    res = docker_exec("echo ok", source=True)
    if res.returncode != 0:
        print("Fehler: Zugriff auf Container oder ROS-Setup fehlgeschlagen.")
        if res.stderr:
            print(res.stderr)
        sys.exit(1)

    # X11 für RViz2 erlauben (Host)
    run_host("xhost +local:root 2>/dev/null")
    print("Container läuft, ROS-Umgebung verfügbar, X11 ist freigeschaltet.")


def stop_all() -> None:
    """Beendet relevante Prozesse im Container."""
    print("Stoppe laufende Prozesse (TF/KISS/RViz) ...")
    docker_exec("pkill -f static_transform_publisher 2>/dev/null", source=False)
    docker_exec("pkill -f kiss_icp 2>/dev/null", source=False)
    docker_exec("pkill -f kiss_icp_node 2>/dev/null", source=False)
    docker_exec("pkill -f rviz2 2>/dev/null", source=False)
    time.sleep(1)


def quat_to_rpy(qx: float, qy: float, qz: float, qw: float) -> tuple[float, float, float]:
    """Konvertiert Quaternion (x,y,z,w) in Roll/Pitch/Yaw (rad)."""
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if norm == 0.0:
        return 0.0, 0.0, 0.0

    qx /= norm
    qy /= norm
    qz /= norm
    qw /= norm

    # Roll
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch
    sinp = 2 * (qw * qy - qz * qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


# =========================
# Start-Logik
# =========================

def start_static_lidar_tf(extr: TransformRPY) -> None:
    """Publiziert die statische Extrinsik base_link -> utlidar_lidar."""
    print("Starte statischen TF für LiDAR-Extrinsik ...")
    print(f"  {LIDAR.parent_frame} -> {LIDAR.child_frame}")
    print(f"  xyz [m] : ({extr.x:.3f}, {extr.y:.3f}, {extr.z:.3f})")
    print(f"  rpy [rad]: ({extr.roll:.3f}, {extr.pitch:.3f}, {extr.yaw:.3f})")

    docker_exec(
        "ros2 run tf2_ros static_transform_publisher "
        f"--x {extr.x} --y {extr.y} --z {extr.z} "
        f"--roll {extr.roll} --pitch {extr.pitch} --yaw {extr.yaw} "
        f"--frame-id {LIDAR.parent_frame} --child-frame-id {LIDAR.child_frame}",
        background=True,
    )

    time.sleep(1)
    print("Statischer TF gestartet.")


def start_kiss_odometry() -> None:
    """
    Startet KISS-ICP über das Launchfile (aktueller Stand).
    Parameter entsprechen dem aktuellen Skript; keine Verhaltensänderung.
    """
    print("Starte KISS-ICP Odometry ...")
    launch_cmd = (
        "ros2 launch kiss_icp odometry.launch.py "
        f"topic:={KISS.topic} "
        f"base_frame:={KISS.base_frame} "
        f"lidar_odom_frame:={KISS.lidar_odom_frame} "
        f"publish_odom_tf:={'true' if KISS.publish_odom_tf else 'false'} "
        f"invert_odom_tf:={'true' if KISS.invert_odom_tf else 'false'}"
    )

    res = docker_exec(launch_cmd, background=True)
    if res.returncode == 0:
        print("KISS-ICP gestartet.")
    else:
        print("Fehler beim Start von KISS-ICP.")
        if res.stderr:
            print(res.stderr)

    time.sleep(2)


def start_rviz() -> None:
    """Startet RViz2 im Container."""
    print("Starte RViz2 ...")
    res = docker_exec("rviz2", background=True)
    if res.returncode == 0:
        print("RViz2 gestartet.")
    else:
        print("Fehler beim Start von RViz2.")
        if res.stderr:
            print(res.stderr)


def check_topics() -> None:
    """Gibt eine reduzierte Liste relevanter Topics aus."""
    print("Prüfe Topics ...")
    time.sleep(2)
    res = docker_exec('ros2 topic list | grep -E "kiss|utlidar|tf"')
    if res.stdout.strip():
        for line in res.stdout.strip().splitlines():
            print(f"  {line}")


def print_rviz_help() -> None:
    print(
        """
RViz2 – empfohlene Debug-Ansicht

A) Rohdaten prüfen (Sensorframe)
  - Fixed Frame: utlidar_lidar
  - Add -> PointCloud2 -> /utlidar/cloud

B) KISS + Rohdaten (Odom-Frame)
  - Fixed Frame: odom
  - Add -> PointCloud2 -> /utlidar/cloud
  - Add -> PointCloud2 -> /kiss/local_map
  - Add -> TF
"""
    )


def print_config_summary(extr: TransformRPY) -> None:
    print(
        f"""
Aktuelle Konfiguration

LiDAR-Extrinsik (statisch)
  {LIDAR.parent_frame} -> {LIDAR.child_frame}
  xyz [m] : ({extr.x:.3f}, {extr.y:.3f}, {extr.z:.3f})
  rpy [rad]: ({extr.roll:.3f}, {extr.pitch:.3f}, {extr.yaw:.3f})

KISS-ICP (Launch)
  topic          : {KISS.topic}
  base_frame     : {KISS.base_frame}
  lidar_odom_frame: {KISS.lidar_odom_frame}
  publish_odom_tf: {KISS.publish_odom_tf}
  invert_odom_tf : {KISS.invert_odom_tf}
"""
    )


# =========================
# Argument-Parsing
# =========================

def parse_args(argv: list[str]) -> TransformRPY:
    """
    Unterstützte Argumente:
      --stop
      --help
      --pos  X Y Z
      --rpy  R P Y
      --quat QX QY QZ QW

    Rückgabe: aktualisierte Extrinsik (TransformRPY)
    """
    extr = LIDAR.extrinsics
    i = 1

    while i < len(argv):
        arg = argv[i]

        if arg == "--stop":
            stop_all()
            print("Alle Prozesse gestoppt.")
            sys.exit(0)

        if arg == "--help":
            print(
                """
Usage:
  python3 lidar_setup.py
  python3 lidar_setup.py --stop
  python3 lidar_setup.py --pos  X Y Z
  python3 lidar_setup.py --rpy  R P Y
  python3 lidar_setup.py --quat QX QY QZ QW
"""
            )
            sys.exit(0)

        if arg == "--pos" and i + 3 < len(argv):
            extr = TransformRPY(
                x=float(argv[i + 1]),
                y=float(argv[i + 2]),
                z=float(argv[i + 3]),
                roll=extr.roll,
                pitch=extr.pitch,
                yaw=extr.yaw,
            )
            i += 4
            continue

        if arg == "--rpy" and i + 3 < len(argv):
            extr = TransformRPY(
                x=extr.x,
                y=extr.y,
                z=extr.z,
                roll=float(argv[i + 1]),
                pitch=float(argv[i + 2]),
                yaw=float(argv[i + 3]),
            )
            i += 4
            continue

        if arg == "--quat" and i + 4 < len(argv):
            qx = float(argv[i + 1])
            qy = float(argv[i + 2])
            qz = float(argv[i + 3])
            qw = float(argv[i + 4])
            roll, pitch, yaw = quat_to_rpy(qx, qy, qz, qw)
            extr = TransformRPY(x=extr.x, y=extr.y, z=extr.z, roll=roll, pitch=pitch, yaw=yaw)
            i += 5
            continue

        i += 1

    return extr


# =========================
# Main
# =========================

def main() -> None:
    extr = parse_args(sys.argv)

    print("=" * 60)
    print("Unitree Go2 - LiDAR Setup (TF + KISS + RViz)")
    print("=" * 60)

    check_docker_or_exit()

    stop_all()
    start_static_lidar_tf(extr)
    start_kiss_odometry()
    start_rviz()
    check_topics()

    print_config_summary(extr)
    print_rviz_help()

    print("Setup abgeschlossen. Beenden mit: python3 lidar_setup.py --stop")


if __name__ == "__main__":
    main()
