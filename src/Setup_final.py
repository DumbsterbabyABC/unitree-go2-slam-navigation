import subprocess
import time
import os
import getpass
import tempfile
import signal
import sys

# Globale Liste für gestartete Prozesse
running_processes = []

def cleanup_and_exit(signum=None, frame=None):
    """Beendet alle gestarteten Prozesse sauber."""
    print("\n\n🛑 Beende alle Prozesse...")
    for proc in running_processes:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            try:
                proc.kill()
            except:
                pass
    
    # RViz2 im Container stoppen
    subprocess.run(
        "sudo pkill -f rviz2 2>/dev/null",
        shell=True, capture_output=True
    )
    print("✓ Alle Prozesse beendet.")
    sys.exit(0)

# Signal-Handler registrieren
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

# RViz2 Konfiguration für Unitree Go2 LiDAR Mapping
RVIZ_CONFIG = """
Panels:
  - Class: rviz_common/Displays
    Name: Displays
  - Class: rviz_common/Views
    Name: Views
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Name: Grid
      Enabled: true
      Cell Size: 1
      Color: 160; 160; 164
      Line Style: Lines
      Plane: XY
      Plane Cell Count: 20

    - Class: rviz_default_plugins/PointCloud2
      Name: LiDAR Live
      Enabled: true
      Topic:
        Value: /utlidar/cloud
        Depth: 5
      Size (m): 0.03
      Color Transformer: Intensity
      Decay Time: 0

    - Class: rviz_default_plugins/PointCloud2
      Name: Cloud Deskewed
      Enabled: true
      Topic:
        Value: /cloud_deskewed
        Depth: 5
      Size (m): 0.03
      Color Transformer: FlatColor
      Color: 0; 255; 0

    - Class: rviz_default_plugins/PointCloud2
      Name: Map (uSLAM)
      Enabled: true
      Topic:
        Value: /uslam/cloud_map
        Depth: 5
      Size (m): 0.02
      Color Transformer: AxisColor
      Axis: Z
      Decay Time: 0

    - Class: rviz_default_plugins/PointCloud2
      Name: Voxel Map
      Enabled: false
      Topic:
        Value: /voxel_map
        Depth: 5
      Size (m): 0.05
      Color Transformer: FlatColor
      Color: 255; 100; 0

    - Class: rviz_default_plugins/Odometry
      Name: Robot Odometry
      Enabled: true
      Topic:
        Value: /robot_odom
        Depth: 5
      Keep: 100
      Shape: Arrow

    - Class: rviz_default_plugins/TF
      Name: TF
      Enabled: true
      Show Names: true
      Show Arrows: true
      Show Axes: true

  Global Options:
    Fixed Frame: odom
    Frame Rate: 30

  Views:
    Current:
      Class: rviz_default_plugins/Orbit
      Distance: 15
      Focal Point:
        X: 0
        Y: 0
        Z: 0
      Pitch: 0.5
      Yaw: 0.5
"""

def run_robot_setup_fixed():
    """
    Startet Unitree Go2 LiDAR Mapping mit RViz2 Visualisierung.
    Nutzt den eingebauten uSLAM des Roboters.
    """
    sudo_password = getpass.getpass(prompt='Sudo-Passwort eingeben: ')

    host_display = os.environ.get("DISPLAY", ":0")
    xauth = os.environ.get("XAUTHORITY", os.path.expanduser("~/.Xauthority"))

    def run_bg_cmd(command):
        full_cmd = f"echo '{sudo_password}' | sudo -S {command}"
        proc = subprocess.Popen(full_cmd, shell=True)
        running_processes.append(proc)
        return proc

    def docker_exec(cmd, background=True):
        docker_cmd = (
            f"docker exec -e DISPLAY={host_display} "
            f"-e XAUTHORITY={xauth} "
            f"unitree_ros2_container bash -c "
            f"'{cmd}'"
        )
        if background:
            return run_bg_cmd(docker_cmd)
        else:
            return subprocess.run(
                f"echo '{sudo_password}' | sudo -S {docker_cmd}",
                shell=True, capture_output=True, text=True, timeout=10
            )

    print("=" * 55)
    print("  🐕 Unitree Go2 LiDAR Mapping Setup")
    print("=" * 55)

    print("\n[1/5] X11 Zugriff freigeben...")
    subprocess.run(["xhost", "+local:root"], capture_output=True)
    print("      ✓ Erledigt")

    print("[2/5] Docker Container starten...")
    run_bg_cmd("docker start unitree_ros2_container")
    time.sleep(3)
    print("      ✓ Container läuft")

    print("[3/5] RViz2 Konfiguration erstellen...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rviz', delete=False) as f:
        f.write(RVIZ_CONFIG)
        temp_config = f.name
    
    subprocess.run(
        f"echo '{sudo_password}' | sudo -S docker cp {temp_config} unitree_ros2_container:/tmp/go2_mapping.rviz",
        shell=True, capture_output=True
    )
    os.unlink(temp_config)
    print("      ✓ Konfiguration geladen")

    print("[4/5] Mapping-Modus aktivieren...")
    try:
        docker_exec(
            "source /opt/ros/humble/setup.bash && "
            "source /basis/unitree_ros2/setup.sh && "
            "ros2 service call /mapping_cmd std_srvs/srv/SetBool \"{data: true}\" 2>/dev/null || "
            "ros2 topic pub /api/mapping/start std_msgs/msg/String \"{data: ''}\" --once 2>/dev/null || "
            "echo 'Manuell aktivieren'",
            background=False
        )
    except:
        pass
    
    print("      ℹ️  Falls keine Karte erscheint:")
    print("         → Mapping in Unitree App aktivieren")

    print("[5/5] RViz2 starten...")
    rviz_cmd = (
        "source /opt/ros/humble/setup.bash && "
        "source /basis/unitree_ros2/setup.sh && "
        "rviz2 -d /tmp/go2_mapping.rviz"
    )
    docker_exec(rviz_cmd, background=True)
    print("      ✓ RViz2 Fenster öffnet sich...")
    
    print("\n" + "=" * 55)
    print("  ✅ Setup abgeschlossen!")
    print("=" * 55)
    print("""
┌─────────────────────────────────────────────────────┐
│  Vorkonfigurierte Displays in RViz2:                │
├─────────────────────────────────────────────────────┤
│  🟢 LiDAR Live      → /utlidar/cloud (Raw-Daten)    │
│  🟢 Cloud Deskewed  → /cloud_deskewed (korrigiert)  │
│  🟢 Map (uSLAM)     → /uslam/cloud_map (Karte)      │
│  🔴 Voxel Map       → /voxel_map (deaktiviert)      │
│  🟢 Robot Odometry  → /robot_odom                   │
├─────────────────────────────────────────────────────┤
│  Fixed Frame: odom                                  │
│                                                     │
│  Kein Mapping sichtbar?                             │
│  1. In Unitree App → Advanced → Mapping starten     │
│  2. Roboter muss sich bewegen für SLAM              │
│  3. Fixed Frame auf 'utlidar' oder 'base' ändern    │
└─────────────────────────────────────────────────────┘

Drücke Ctrl+C um zu beenden.
""")
    
    # Warte auf Benutzer-Interrupt
    print("⏳ Läuft... Drücke Ctrl+C zum Beenden.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup_and_exit()


def check_topics():
    """Prüft welche Topics aktiv Daten senden."""
    print("Prüfe aktive Topics vom Roboter...\n")
    
    topics = ["/utlidar/cloud", "/cloud_deskewed", "/uslam/cloud_map", "/voxel_map", "/robot_odom"]
    
    for topic in topics:
        result = subprocess.run(
            f"timeout 2 sudo docker exec unitree_ros2_container bash -c "
            f"'source /opt/ros/humble/setup.bash && source /basis/unitree_ros2/setup.sh && "
            f"ros2 topic hz {topic} --window 1 2>&1' | head -2",
            shell=True, capture_output=True, text=True
        )
        
        if "average rate" in result.stdout:
            print(f"  ✓ {topic}: Aktiv")
        else:
            print(f"  ✗ {topic}: Keine Daten")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            check_topics()
        elif sys.argv[1] == "--stop":
            print("Stoppe alle RViz2 Prozesse...")
            subprocess.run("sudo pkill -9 -f rviz2", shell=True)
            subprocess.run("pkill -9 -f Setup_final", shell=True)
            print("✓ Gestoppt")
        elif sys.argv[1] == "--help":
            print("""
Unitree Go2 Mapping Setup
=========================
  python Setup_final.py           # Startet Mapping + RViz2
  python Setup_final.py --check   # Prüft aktive Topics
  python Setup_final.py --stop    # Stoppt alle Prozesse
  python Setup_final.py --help    # Zeigt diese Hilfe

Während das Skript läuft: Ctrl+C drücken zum Beenden
""")
    else:
        run_robot_setup_fixed()
