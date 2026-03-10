#!/usr/bin/env python3
"""
LiDAR Position Konfiguration für Unitree Go2
- Setzt base_link -> utlidar_lidar (Extrinsik des LiDAR)
- "klebt" TF-Bäume zusammen via odom_lidar -> base_link (Glue-TF)
- Startet KISS-ICP + RViz2 zur Überprüfung
"""
import math
import subprocess
import sys
import time

# ============================================================
#  DOCKER KONFIGURATION
# ============================================================
CONTAINER_NAME = "unitree_ros2_container"
DOCKER_DISPLAY = ":0"

SOURCE_CMD = (
    "source /opt/ros/humble/setup.bash && "
    "source /basis/unitree_ros2/setup.sh && "
    "source /root/kiss_ws/install/setup.bash"
)

# ============================================================
#  LIDAR EXTRINSIK (base_link -> utlidar_lidar)
# ============================================================
LIDAR_X = 0.24
LIDAR_Y = 0.0
LIDAR_Z = 0.13

LIDAR_ROLL = 0.0
LIDAR_PITCH = 0.0   # z.B. -0.261799 für -15°
LIDAR_YAW = 0.0

# ============================================================
#  TF-GLUE (odom_lidar -> base_link)
#  Damit RViz/KISS und der Robot-TF im gleichen Baum hängen.
#  Erstmal Identity als Debug-Fix.
# ============================================================
GLUE_X = 0.0
GLUE_Y = 0.0
GLUE_Z = 0.0

GLUE_ROLL = 0.0
GLUE_PITCH = 0.0
GLUE_YAW = 0.0


def docker_exec(cmd, background=False, source=True):
    """Führt einen Befehl im Docker-Container aus."""
    source_prefix = f"{SOURCE_CMD} && " if source else ""
    d_flag = "-d" if background else ""

    full_cmd = (
        f"sudo docker exec {d_flag} "
        f"-e DISPLAY={DOCKER_DISPLAY} "
        f"-e QT_X11_NO_MITSHM=1 "
        f"{CONTAINER_NAME} bash -c '"
        f"export DISPLAY={DOCKER_DISPLAY} && "
        f"{source_prefix}"
        f"{cmd}'"
    )
    return subprocess.run(full_cmd, shell=True, capture_output=not background, text=True)


def check_docker():
    """Prüft ob der Docker-Container läuft und erreichbar ist."""
    print(f"🐳 Prüfe Docker-Container '{CONTAINER_NAME}'...")

    result = subprocess.run(
        f"sudo docker inspect -f '{{{{.State.Running}}}}' {CONTAINER_NAME}",
        shell=True, capture_output=True, text=True
    )
    if result.stdout.strip() != "true":
        print(f"   ✗ Container '{CONTAINER_NAME}' läuft nicht!")
        print(f"   → Starte ihn mit: sudo docker start {CONTAINER_NAME}")
        sys.exit(1)

    result = docker_exec("echo ok", source=True)
    if result.returncode != 0:
        print("   ✗ Kann nicht in den Container!")
        print(f"   stderr: {result.stderr}")
        sys.exit(1)

    subprocess.run("xhost +local:root 2>/dev/null", shell=True)
    print(f"   ✓ Container läuft, ROS2 Humble bereit, X11 forwarding aktiv")


def stop_all():
    """Stoppt alle laufenden Prozesse im Container."""
    print("🛑 Stoppe alle Prozesse...")
    docker_exec("pkill -f static_transform_publisher 2>/dev/null", source=False)
    docker_exec("pkill -f kiss_icp 2>/dev/null", source=False)
    docker_exec("pkill -f rviz2 2>/dev/null", source=False)
    time.sleep(1)


def quat_to_rpy(qx, qy, qz, qw):
    """Konvertiert Quaternion (x,y,z,w) zu Roll/Pitch/Yaw (rad)."""
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if norm == 0:
        return 0.0, 0.0, 0.0
    qx /= norm
    qy /= norm
    qz /= norm
    qw /= norm

    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2 * (qw * qy - qz * qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


def start_tf_publishers():
    """
    Startet:
    1) base_link -> utlidar_lidar  (Extrinsik)
    2) odom_lidar -> base_link     (Glue, damit TF-Bäume verbunden sind)
    """
    print(f"📍 Starte TF Publisher (Extrinsik + Glue)...")

    print(f"   [Extrinsik] base_link -> utlidar_lidar")
    print(f"     xyz:  {LIDAR_X:.3f}, {LIDAR_Y:.3f}, {LIDAR_Z:.3f}  [m]")
    print(f"     rpy:  {LIDAR_ROLL:.3f}, {LIDAR_PITCH:.3f}, {LIDAR_YAW:.3f}  [rad]")

    docker_exec(
        f"ros2 run tf2_ros static_transform_publisher "
        f"--x {LIDAR_X} --y {LIDAR_Y} --z {LIDAR_Z} "
        f"--roll {LIDAR_ROLL} --pitch {LIDAR_PITCH} --yaw {LIDAR_YAW} "
        f"--frame-id base_link --child-frame-id utlidar_lidar",
        background=True
    )

    print(f"   [Glue] odom_lidar -> base_link")
    print(f"     xyz:  {GLUE_X:.3f}, {GLUE_Y:.3f}, {GLUE_Z:.3f}  [m]")
    print(f"     rpy:  {GLUE_ROLL:.3f}, {GLUE_PITCH:.3f}, {GLUE_YAW:.3f}  [rad]")

    '''docker_exec(
        f"ros2 run tf2_ros static_transform_publisher "
        f"--x {GLUE_X} --y {GLUE_Y} --z {GLUE_Z} "
        f"--roll {GLUE_ROLL} --pitch {GLUE_PITCH} --yaw {GLUE_YAW} "
        f"--frame-id odom_lidar --child-frame-id base_link",
        background=True
    )'''

    time.sleep(1)
    print("   ✓ TF Publisher gestartet")


def start_kiss_icp():
    """Startet KISS-ICP Odometry auf der Rohwolke im Sensorframe."""
    print("🗺️  Starte KISS-ICP Odometry...")

    result = docker_exec(
        "ros2 launch kiss_icp odometry.launch.py "
        "topic:=/utlidar/cloud "
        "base_frame:=base_link "
        "lidar_odom_frame:=odom "
        "publish_odom_tf:=true "
        "invert_odom_tf:=true",
        background=True
    )

    if result.returncode == 0:
        print("   ✓ KISS-ICP gestartet")
    else:
        print("   ✗ Fehler beim Starten")
        if result.stderr:
            print(result.stderr)

    time.sleep(2)


def start_rviz():
    """Startet RViz2."""
    print("👁️  Starte RViz2...")
    result = docker_exec("rviz2", background=True)
    if result.returncode == 0:
        print("   ✓ RViz2 gestartet")
    else:
        print("   ✗ Fehler beim Starten")
        if result.stderr:
            print(result.stderr)


def check_topics():
    """Prüft ob alle Topics aktiv sind."""
    print("\n📡 Prüfe Topics...")
    time.sleep(2)

    result = docker_exec('ros2 topic list | grep -E "kiss|utlidar|tf"')
    if result.stdout:
        print("   Aktive Topics:")
        for line in result.stdout.strip().split('\n'):
            print(f"     {line}")


def print_rviz_help():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║  RViz2 Setup (Debug)                                          ║
╠═══════════════════════════════════════════════════════════════╣
║  A) Rohdaten prüfen (Sensorframe)                             ║
║     Fixed Frame: utlidar_lidar                                ║
║     Add -> PointCloud2 -> /utlidar/cloud                      ║
║                                                               ║
║  B) KISS + Rohdaten zusammen (Odom-Frame)                     ║
║     Fixed Frame: odom_lidar                                   ║
║     Add -> PointCloud2 -> /utlidar/cloud                      ║
║     Add -> PointCloud2 -> /kiss/local_map                     ║
║     Add -> TF                                                 ║
║                                                               ║
║  Hinweis: /utlidar/cloud_deskewed hat bei euch frame_id=odom,  ║
║           daher NICHT als KISS-Input verwenden.               ║
╚═══════════════════════════════════════════════════════════════╝
""")


def print_position_help():
    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║  LiDAR Extrinsik (base_link -> utlidar_lidar)                 ║
╠═══════════════════════════════════════════════════════════════╣
║  X: {LIDAR_X:>7.3f} m    Y: {LIDAR_Y:>7.3f} m    Z: {LIDAR_Z:>7.3f} m   ║
║  Roll:  {LIDAR_ROLL:>7.3f} rad                                ║
║  Pitch: {LIDAR_PITCH:>7.3f} rad                                ║
║  Yaw:   {LIDAR_YAW:>7.3f} rad                                ║
╠═══════════════════════════════════════════════════════════════╣
║  TF-Glue (odom_lidar -> base_link)                            ║
║  X: {GLUE_X:>7.3f} m    Y: {GLUE_Y:>7.3f} m    Z: {GLUE_Z:>7.3f} m   ║
║  Roll:  {GLUE_ROLL:>7.3f} rad                                ║
║  Pitch: {GLUE_PITCH:>7.3f} rad                                ║
║  Yaw:   {GLUE_YAW:>7.3f} rad                                ║
╚═══════════════════════════════════════════════════════════════╝
""")


def main():
    global LIDAR_X, LIDAR_Y, LIDAR_Z, LIDAR_ROLL, LIDAR_PITCH, LIDAR_YAW
    global GLUE_X, GLUE_Y, GLUE_Z, GLUE_ROLL, GLUE_PITCH, GLUE_YAW

    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--stop":
            stop_all()
            print("✓ Alle Prozesse gestoppt")
            return
        elif arg == "--help":
            print_position_help()
            print_rviz_help()
            return
        elif arg == "--pos" and i + 3 < len(sys.argv):
            LIDAR_X = float(sys.argv[i + 1])
            LIDAR_Y = float(sys.argv[i + 2])
            LIDAR_Z = float(sys.argv[i + 3])
            print(f"📍 Neue LiDAR-Position: X={LIDAR_X}, Y={LIDAR_Y}, Z={LIDAR_Z}")
            i += 4
            continue
        elif arg == "--rpy" and i + 3 < len(sys.argv):
            LIDAR_ROLL = float(sys.argv[i + 1])
            LIDAR_PITCH = float(sys.argv[i + 2])
            LIDAR_YAW = float(sys.argv[i + 3])
            print(f"🧭 Neue LiDAR-RPY: Roll={LIDAR_ROLL}, Pitch={LIDAR_PITCH}, Yaw={LIDAR_YAW}")
            i += 4
            continue
        elif arg == "--quat" and i + 4 < len(sys.argv):
            qx = float(sys.argv[i + 1])
            qy = float(sys.argv[i + 2])
            qz = float(sys.argv[i + 3])
            qw = float(sys.argv[i + 4])
            LIDAR_ROLL, LIDAR_PITCH, LIDAR_YAW = quat_to_rpy(qx, qy, qz, qw)
            print(
                f"🧭 Quaternion -> RPY: "
                f"Roll={LIDAR_ROLL:.6f}, Pitch={LIDAR_PITCH:.6f}, Yaw={LIDAR_YAW:.6f}"
            )
            i += 5
            continue
        elif arg == "--glue" and i + 6 < len(sys.argv):
            GLUE_X = float(sys.argv[i + 1])
            GLUE_Y = float(sys.argv[i + 2])
            GLUE_Z = float(sys.argv[i + 3])
            GLUE_ROLL = float(sys.argv[i + 4])
            GLUE_PITCH = float(sys.argv[i + 5])
            GLUE_YAW = float(sys.argv[i + 6])
            print(
                f"🧷 Neue Glue-TF odom_lidar->base_link: "
                f"xyz=({GLUE_X},{GLUE_Y},{GLUE_Z}) rpy=({GLUE_ROLL},{GLUE_PITCH},{GLUE_YAW})"
            )
            i += 7
            continue
        else:
            i += 1

    print("=" * 60)
    print("  🐕 Unitree Go2 - LiDAR Setup (TF + KISS + RViz)")
    print("=" * 60)

    check_docker()

    stop_all()
    start_tf_publishers()
    start_kiss_icp()
    start_rviz()
    check_topics()

    print_position_help()
    print_rviz_help()

    print("\n✅ Setup abgeschlossen!")
    print("   Zum Beenden: python3 lidar_setup.py --stop")


if __name__ == "__main__":
    main()
