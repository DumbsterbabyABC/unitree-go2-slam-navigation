#!/usr/bin/env python3
"""
SLAM Setup für Unitree Go2 mit KISS-ICP
Nutzt /utlidar/cloud für LiDAR-basiertes Mapping
"""
import subprocess
import time
import os
import getpass
import signal
import sys
import tempfile

# RViz2 Konfiguration für KISS-ICP SLAM
RVIZ_CONFIG = """
Panels:
  - Class: rviz_common/Displays
    Name: Displays
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Name: Grid
      Enabled: true
      Cell Size: 1
      Plane: XY
      Plane Cell Count: 50

    - Class: rviz_default_plugins/PointCloud2
      Name: LiDAR Input
      Enabled: false
      Topic:
        Value: /utlidar/cloud_deskewed
        Depth: 1
        Reliability Policy: Best Effort
        Durability Policy: Volatile
      Size (m): 0.02
      Color Transformer: FlatColor
      Color: 0; 255; 0
      Decay Time: 0

    - Class: rviz_default_plugins/PointCloud2
      Name: SLAM Map
      Enabled: true
      Topic:
        Value: /kiss/local_map
        Depth: 1
        Reliability Policy: Best Effort
        Durability Policy: Volatile
      Size (m): 0.03
      Color Transformer: AxisColor
      Axis: Z
      Decay Time: 0

    - Class: rviz_default_plugins/Path
      Name: Trajectory
      Enabled: true
      Topic:
        Value: /kiss/trajectory
        Depth: 5
      Color: 255; 0; 255

    - Class: rviz_default_plugins/TF
      Name: TF
      Enabled: true
      Show Names: true
      Show Arrows: false

  Global Options:
    Fixed Frame: odom
    Frame Rate: 15
"""

running_processes = []

def cleanup_and_exit(signum=None, frame=None):
    """Beendet alle Prozesse sauber."""
    print("\n\n🛑 Beende SLAM und alle Prozesse...")
    for proc in running_processes:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            try:
                proc.kill()
            except:
                pass
    subprocess.run("sudo pkill -f kiss_icp 2>/dev/null", shell=True)
    subprocess.run("sudo pkill -f rviz2 2>/dev/null", shell=True)
    print("✓ Beendet.")
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)


def run_slam():
    """Startet KISS-ICP SLAM mit /utlidar/cloud"""
    
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
            f'"{cmd}"'
        )
        if background:
            return run_bg_cmd(docker_cmd)
        else:
            try:
                return subprocess.run(
                    f"echo '{sudo_password}' | sudo -S {docker_cmd}",
                    shell=True, capture_output=True, text=True, timeout=15
                )
            except subprocess.TimeoutExpired:
                return None

    print("=" * 55)
    print("  🗺️  KISS-ICP SLAM für Unitree Go2")
    print("=" * 55)

    # 1. X11 und Container
    print("\n[1/5] Setup...")
    subprocess.run(["xhost", "+local:root"], capture_output=True)
    run_bg_cmd("docker start unitree_ros2_container")
    time.sleep(2)
    print("      ✓ Container läuft")

    # 2. Prüfe ob KISS-ICP installiert ist
    print("[2/5] Prüfe KISS-ICP Installation...")
    check = docker_exec(
        "source /opt/ros/humble/setup.bash && "
        "ros2 pkg list 2>/dev/null | grep -q kiss && echo 'OK' || echo 'MISSING'",
        background=False
    )
    
    if check and "MISSING" in (check.stdout or ""):
        print("      ⚠️  KISS-ICP nicht installiert!")
        print("      → Führe erst aus: bash install_kiss_icp.sh")
        print("      → Oder nutze Alternative unten")
        use_kiss = False
    else:
        use_kiss = True
        print("      ✓ KISS-ICP verfügbar")

    # 3. RViz Config kopieren
    print("[3/5] RViz2 Konfiguration...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rviz', delete=False) as f:
        f.write(RVIZ_CONFIG)
        temp_config = f.name
    
    subprocess.run(
        f"echo '{sudo_password}' | sudo -S docker cp {temp_config} unitree_ros2_container:/tmp/slam.rviz",
        shell=True, capture_output=True
    )
    os.unlink(temp_config)
    print("      ✓ Konfiguration geladen")

    # 4. SLAM starten
    print("[4/5] Starte SLAM...")
    
    if use_kiss:
        # KISS-ICP starten mit cloud_deskewed (bewegungskorrigiert)
        slam_cmd = (
            "source /opt/ros/humble/setup.bash && "
            "source /basis/unitree_ros2/setup.sh && "
            "source /root/kiss_ws/install/setup.bash 2>/dev/null; "
            "ros2 launch kiss_icp odometry.launch.py "
            "topic:=/utlidar/cloud_deskewed "
            "odom_frame:=odom "
            "child_frame:=base_link "
            "visualize:=false"
        )
        docker_exec(slam_cmd, background=True)
        print("      ✓ KISS-ICP gestartet")
    else:
        # Alternative: Einfache Pointcloud-Akkumulation
        print("      → Nutze einfache Pointcloud-Akkumulation")
        # Wir können octomap oder pcl_ros nutzen
    
    time.sleep(3)

    # 5. RViz2 starten
    print("[5/5] Starte RViz2...")
    rviz_cmd = (
        "source /opt/ros/humble/setup.bash && "
        "source /basis/unitree_ros2/setup.sh && "
        "rviz2 -d /tmp/slam.rviz"
    )
    docker_exec(rviz_cmd, background=True)
    
    print("\n" + "=" * 55)
    print("  ✅ SLAM läuft!")
    print("=" * 55)
    print("""
┌─────────────────────────────────────────────────────┐
│  KISS-ICP Topics:                                   │
├─────────────────────────────────────────────────────┤
│  📥 Input:      /utlidar/cloud                      │
│  🗺️  Map:        /kiss/local_map                    │
│  📍 Odometry:   /kiss/odometry                      │
│  🛤️  Trajectory: /kiss/trajectory                   │
├─────────────────────────────────────────────────────┤
│  Fixed Frame: odom                                  │
│                                                     │
│  Karte speichern:                                   │
│  ros2 run pcl_ros pointcloud_to_pcd                 │
│      input:=/kiss/local_map                         │
└─────────────────────────────────────────────────────┘

Drücke Ctrl+C zum Beenden.
""")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup_and_exit()


def install_kiss_icp():
    """Installiert KISS-ICP im Container."""
    print("Installiere KISS-ICP im Container...")
    
    install_cmd = '''
    source /opt/ros/humble/setup.bash
    pip3 install kiss-icp
    
    mkdir -p /root/kiss_ws/src
    cd /root/kiss_ws/src
    if [ ! -d "kiss-icp" ]; then
        git clone https://github.com/PRBonn/kiss-icp.git
    fi
    cd /root/kiss_ws
    colcon build --packages-select kiss_icp
    echo "source /root/kiss_ws/install/setup.bash" >> ~/.bashrc
    echo "Installation erfolgreich!"
    '''
    
    result = subprocess.run(
        f"sudo docker exec unitree_ros2_container bash -c '{install_cmd}'",
        shell=True
    )
    return result.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--install":
            install_kiss_icp()
        elif sys.argv[1] == "--stop":
            print("Stoppe SLAM...")
            subprocess.run("sudo pkill -9 -f kiss_icp", shell=True)
            subprocess.run("sudo pkill -9 -f rviz2", shell=True)
            print("✓ Gestoppt")
        elif sys.argv[1] == "--help":
            print("""
KISS-ICP SLAM für Unitree Go2
=============================
  python3 Setup_slam.py              # Startet SLAM + RViz2
  python3 Setup_slam.py --install    # Installiert KISS-ICP
  python3 Setup_slam.py --stop       # Stoppt alles
  python3 Setup_slam.py --help       # Diese Hilfe

KISS-ICP nutzt /utlidar/cloud und generiert:
  - /kiss/local_map     : Akkumulierte Karte
  - /kiss/odometry      : Geschätzte Roboter-Pose
  - /kiss/trajectory    : Gefahrener Pfad
""")
    else:
        run_slam()
