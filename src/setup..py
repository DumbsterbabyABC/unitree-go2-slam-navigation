import subprocess
import time
import os
import getpass

def run_robot_setup_fixed():
    """
    Startet FAST-LIO für LiDAR-basiertes Mapping mit RViz2 Visualisierung.
    """
    # Passwort-Abfrage in der VS Code Konsole
    sudo_password = getpass.getpass(prompt='Sudo-Passwort eingeben: ')

    # Host-Display und XAuthority (Wichtig für Grafik-Rechte)
    host_display = os.environ.get("DISPLAY", ":0")
    xauth = os.environ.get("XAUTHORITY", os.path.expanduser("~/.X11-unix"))

    def run_bg_cmd(command):
        # Nutzt sudo -S für den Hintergrundlauf
        full_cmd = f"echo '{sudo_password}' | sudo -S {command}"
        return subprocess.Popen(full_cmd, shell=True)

    def docker_exec(cmd, background=True):
        """Führt einen Befehl im Docker-Container aus."""
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
                shell=True, capture_output=True, text=True
            )

    # 1. Display für Docker freigeben (Host-Seite)
    print("=" * 50)
    print("FAST-LIO Mapping Setup")
    print("=" * 50)
    print("\n[1/5] Berechtige X11 Zugriff...")
    subprocess.run(["xhost", "+local:root"], capture_output=True)

    # 2. Docker Container starten (Falls er noch nicht läuft)
    print("[2/5] Starte Container...")
    run_bg_cmd("docker start unitree_ros2_container")
    time.sleep(3)

    # 3. Prüfe verfügbare LiDAR-Topics
    print("[3/5] Prüfe LiDAR-Topics...")
    topic_check = docker_exec(
        "source /opt/ros/humble/setup.bash && "
        "source /basis/unitree_ros2/setup.sh && "
        "ros2 topic list 2>/dev/null | grep -E 'point|cloud|lidar|scan' || echo 'Keine LiDAR-Topics gefunden'",
        background=False
    )
    if topic_check.stdout:
        print(f"    Gefundene Topics:\n{topic_check.stdout}")

    # 4. FAST-LIO starten
    print("[4/5] Starte FAST-LIO Mapping...")
    
    # Prüfe zuerst ob FAST-LIO installiert ist
    check_result = docker_exec(
        "source /opt/ros/humble/setup.bash && ros2 pkg list | grep -q fast_lio && echo 'installed' || echo 'not_installed'",
        background=False
    )
    
    if "not_installed" in check_result.stdout:
        print("    ⚠️  FAST-LIO nicht installiert!")
        print("    → Starte RViz2 zur manuellen Pointcloud-Visualisierung")
        print("    → Siehe Installationsanleitung am Ende")
        fastlio_running = False
    else:
        # FAST-LIO Launch-Befehl
        fastlio_cmd = (
            "source /opt/ros/humble/setup.bash && "
            "source /basis/unitree_ros2/setup.sh && "
            "ros2 launch fast_lio mapping.launch.py"
        )
        docker_exec(fastlio_cmd, background=True)
        fastlio_running = True
        time.sleep(3)

    # 5. RViz2 mit Mapping-Konfiguration starten
    print("[5/5] Starte RViz2 für Kartenvisualisierung...")
    
    # RViz2 mit vorkonfigurierter Ansicht für Mapping
    rviz_cmd = (
        "source /opt/ros/humble/setup.bash && "
        "source /basis/unitree_ros2/setup.sh && "
        "rviz2 -d /opt/ros/humble/share/rviz2/default.rviz"
    )
    # Falls eine FAST-LIO RViz-Config existiert:
    # rviz_cmd = (
    #     "source /opt/ros/humble/setup.bash && "
    #     "source /basis/unitree_ros2/setup.sh && "
    #     "rviz2 -d $(ros2 pkg prefix fast_lio)/share/fast_lio/rviz/mapping.rviz"
    # )
    
    docker_exec(rviz_cmd, background=True)
    
    print("\n" + "=" * 50)
    print("Setup abgeschlossen!")
    print("=" * 50)
    print("""
In RViz2:
  1. Fixed Frame auf 'map' oder 'odom' setzen
  2. 'Add' -> 'PointCloud2' -> Topic: /cloud_registered
  3. 'Add' -> 'Path' -> Topic: /path (Trajektorie)
  4. 'Add' -> 'TF' für Koordinatensysteme

Wichtige FAST-LIO Topics:
  - /cloud_registered  : Registrierte Pointcloud (Karte)
  - /Odometry          : Roboter-Odometrie
  - /path              : Gefahrene Trajektorie

Karte speichern (im Container):
  ros2 run pcl_ros pointcloud_to_pcd input:=/cloud_registered
""")

def check_fastlio_installation():
    """Prüft, ob FAST-LIO im Container installiert ist."""
    print("Prüfe FAST-LIO Installation...")
    result = subprocess.run(
        "sudo docker exec unitree_ros2_container bash -c "
        "'source /opt/ros/humble/setup.bash && ros2 pkg list | grep -i fast_lio'",
        shell=True, capture_output=True, text=True
    )
    if "fast_lio" in result.stdout:
        print(f"✓ FAST-LIO gefunden: {result.stdout}")
        return True
    else:
        print("✗ FAST-LIO nicht gefunden!")
        print("""
╔══════════════════════════════════════════════════════════════╗
║  FAST-LIO Installation im Container (ROS2 Humble)            ║
╠══════════════════════════════════════════════════════════════╣
║  1. Container öffnen:                                        ║
║     sudo docker exec -it unitree_ros2_container bash         ║
║                                                              ║
║  2. Abhängigkeiten installieren:                             ║
║     apt update && apt install -y libeigen3-dev libpcl-dev    ║
║                                                              ║
║  3. Workspace erstellen:                                     ║
║     mkdir -p ~/fast_lio_ws/src && cd ~/fast_lio_ws/src       ║
║                                                              ║
║  4. FAST-LIO klonen (ROS2 Branch):                           ║
║     git clone -b ros2 https://github.com/hku-mars/FAST_LIO   ║
║                                                              ║
║  5. Livox SDK (falls Livox LiDAR):                           ║
║     git clone https://github.com/Livox-SDK/livox_ros_driver2 ║
║                                                              ║
║  6. Bauen:                                                   ║
║     cd ~/fast_lio_ws                                         ║
║     source /opt/ros/humble/setup.bash                        ║
║     colcon build --symlink-install                           ║
║                                                              ║
║  7. Setup hinzufügen (in ~/.bashrc):                         ║
║     echo "source ~/fast_lio_ws/install/setup.bash" >> ~/.bashrc║
╚══════════════════════════════════════════════════════════════╝
""")
        return False

def install_fastlio_in_container():
    """Interaktive Installation von FAST-LIO."""
    print("Starte FAST-LIO Installation...")
    
    install_script = '''
    set -e
    apt update
    apt install -y git libeigen3-dev libpcl-dev ros-humble-pcl-ros
    
    mkdir -p /root/fast_lio_ws/src
    cd /root/fast_lio_ws/src
    
    if [ ! -d "FAST_LIO" ]; then
        git clone -b ros2 https://github.com/hku-mars/FAST_LIO.git
    fi
    
    cd /root/fast_lio_ws
    source /opt/ros/humble/setup.bash
    colcon build --symlink-install
    
    echo "source /root/fast_lio_ws/install/setup.bash" >> /root/.bashrc
    echo "FAST-LIO Installation abgeschlossen!"
    '''
    
    result = subprocess.run(
        f"sudo docker exec unitree_ros2_container bash -c '{install_script}'",
        shell=True
    )
    return result.returncode == 0

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            check_fastlio_installation()
        elif sys.argv[1] == "--install":
            install_fastlio_in_container()
        elif sys.argv[1] == "--help":
            print("""
FAST-LIO Mapping Setup
======================
Verwendung:
  python Setup_final.py           # Startet Mapping + RViz2
  python Setup_final.py --check   # Prüft FAST-LIO Installation
  python Setup_final.py --install # Installiert FAST-LIO automatisch
  python Setup_final.py --help    # Zeigt diese Hilfe
""")
    else:
        run_robot_setup_fixed()