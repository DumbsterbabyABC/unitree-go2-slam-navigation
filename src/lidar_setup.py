#!/usr/bin/env python3
"""
LiDAR Position Konfiguration für Unitree Go2
Stellt die Position des Front-LiDAR relativ zum base_link ein
und startet KISS-ICP + RViz2 zur Überprüfung der Karte
"""
import math
import subprocess
import sys
import time


#  DOCKER KONFIGURATION

CONTAINER_NAME = "unitree_ros2_container"
DOCKER_DISPLAY = ":0"

# Quellen die EINMAL am Anfang in jeder Shell gesourct werden
SOURCE_CMD = (
    "source /opt/ros/humble/setup.bash && "
    "source /basis/unitree_ros2/setup.sh && "
    "source /root/kiss_ws/install/setup.bash"
)

#  LIDAR POSITION KONFIGURATION
#  Wertänderung Position anpassen


# Position relativ zu base_link (in Metern)
LIDAR_X = 0.24   # Nach vorne (+) / hinten (-)
LIDAR_Y = 0.0    # Nach links (+) / rechts (-)
LIDAR_Z = 0.13   # Nach oben (+) / unten (-)

# Rotation (in Radians) - normalerweise 0
LIDAR_ROLL = 0.0  # Rotation um X-Achse
LIDAR_PITCH = -0.261799 # Rotation um Y-Achse (~90°)
LIDAR_YAW = 0.0   # Rotation um Z-Achse

# Quaternion W-Komponente (zum einfachen Anpassen)
LIDAR_QUAT_W = 0.0




def docker_exec(cmd, background=False, source=True):
    """
    Führt einen Befehl im Docker-Container aus.
    
    Args:
        cmd:        Der Befehl der im Container laufen soll
        background: True = im Hintergrund starten (-d Flag)
        source:     True = ROS2/KISS Quellen vorher sourcen
    """
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
    """
    Prüft ob der Docker-Container läuft und erreichbar ist.
    Wird EINMAL am Anfang aufgerufen – saftig rein dippen 
    """
    print(f" Prüfe Docker-Container '{CONTAINER_NAME}'...")
    
    # Ist der Container überhaupt am laufen?
    result = subprocess.run(
        f"sudo docker inspect -f '{{{{.State.Running}}}}' {CONTAINER_NAME}",
        shell=True, capture_output=True, text=True
    )
    if result.stdout.strip() != "true":
        print(f"   ✗ Container '{CONTAINER_NAME}' läuft nicht!")
        print(f"   → Starte ihn mit: sudo docker start {CONTAINER_NAME}")
        sys.exit(1)
    
    # Können wir reinkommen und ROS sourcen?
    result = docker_exec("echo ok", source=True)
    if result.returncode != 0:
        print("   ✗ Kann nicht in den Container!")
        print(f"   stderr: {result.stderr}")
        sys.exit(1)
    
    # X11 forwarding vorbereiten
    subprocess.run("xhost +local:root 2>/dev/null", shell=True)
    
    print(f"   ✓ Container läuft, ROS2 Humble bereit, X11 forwarding aktiv")


def stop_all():
    """Stoppt alle laufenden Prozesse im Container"""
    print(" Stoppe alle Prozesse...")
    docker_exec("pkill -f static_transform 2>/dev/null", source=False)
    docker_exec("pkill -f kiss_icp 2>/dev/null", source=False)
    docker_exec("pkill -f rviz2 2>/dev/null", source=False)
    time.sleep(1)


def quat_to_rpy(qx, qy, qz, qw):
    """Konvertiert Quaternion (x,y,z,w) zu Roll/Pitch/Yaw (rad)."""
    # Normalize to avoid drift
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if norm == 0:
        return 0.0, 0.0, 0.0
    qx /= norm
    qy /= norm
    qz /= norm
    qw /= norm

    # Roll (x-axis rotation)
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2 * (qw * qy - qz * qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw


def start_tf_publisher():
    """Startet den TF Publisher mit der konfigurierten LiDAR-Position"""
    print(f" Starte TF Publisher...")
    print(f"   Position: X={LIDAR_X}m, Y={LIDAR_Y}m, Z={LIDAR_Z}m")
    print(f"   Rotation: Roll={LIDAR_ROLL}, Pitch={LIDAR_PITCH}, Yaw={LIDAR_YAW}")
    
    result = docker_exec(
        f"ros2 run tf2_ros static_transform_publisher "
        f"--x {LIDAR_X} --y {LIDAR_Y} --z {LIDAR_Z} "
        f"--roll {LIDAR_ROLL} --pitch {LIDAR_PITCH} --yaw {LIDAR_YAW} "
        f"--frame-id base_link --child-frame-id utlidar_lidar",
        background=True
    )
    if result.returncode == 0:
        print("   ✓ TF Publisher gestartet")
    else:
        print("   ✗ Fehler beim Starten")
    time.sleep(1)


def start_kiss_icp():
    """Startet KISS-ICP SLAM"""
    print("  Starte KISS-ICP SLAM...")
    
    result = docker_exec(
        "ros2 launch kiss_icp odometry.launch.py "
        "topic:=/utlidar/cloud "
        "odom_frame:=odom_lidar "
        "child_frame:=base_link",
        background=True
    )
    if result.returncode == 0:
        print("   ✓ KISS-ICP gestartet")
    else:
        print("   ✗ Fehler beim Starten")
    time.sleep(2)


def start_rviz():
    """Startet RViz2"""
    print("  Starte RViz2...")
    
    result = docker_exec("rviz2", background=True)
    if result.returncode == 0:
        print("   ✓ RViz2 gestartet")
    else:
        print("   ✗ Fehler beim Starten")


def check_topics():
    """Prüft ob alle Topics aktiv sind"""
    print("\n Prüfe Topics...")
    time.sleep(2)
    
    result = docker_exec('ros2 topic list | grep -E "kiss|utlidar"')
    if result.stdout:
        print("   Aktive Topics:")
        for line in result.stdout.strip().split('\n'):
            print(f"     {line}")
    

def print_rviz_help():
    """Zeigt RViz2 Einstellungen"""
    print("""

     RViz2 Einstellungen für Karten-Überprüfung                   

  1. Fixed Frame:     odom_lidar                               
  2. Add → PointCloud2 → Topic: /kiss/local_map                
  3. Add → PointCloud2 → Topic: /utlidar/cloud_deskewed        
  4. Add → TF (um Frames zu sehen)                             
                                                               
  Decay Time für local_map: 0                                  
  Color Transformer: AxisColor (Axis: Z) für Höhenfarben      
""")


def print_position_help():
    """Zeigt wie man die Position ändert"""
    print(f"""
          
  Aktuelle LiDAR-Position (relativ zu base_link):              

  X (vorne/hinten):  {LIDAR_X:>6.3f} m                                 
  Y (links/rechts):  {LIDAR_Y:>6.3f} m                                 
  Z (oben/unten):    {LIDAR_Z:>6.3f} m                                 

  
  Um die Position zu ändern:                                   
  1. Öffne diese Datei: lidar_setup.py                         
  2. Ändere LIDAR_X, LIDAR_Y, LIDAR_Z oben im Skript           
  3. Starte neu: python3 lidar_setup.py                        
                                                               
  Oder direkt mit Argumenten:                                  
  python3 lidar_setup.py --pos 0.30 0.0 0.10                   
  python3 lidar_setup.py --quat 0 0 0 1                        

""")


def main():
    global LIDAR_X, LIDAR_Y, LIDAR_Z, LIDAR_ROLL, LIDAR_PITCH, LIDAR_YAW
    
    # Parse Argumente (unterstützt mehrere Flags)
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
            print(f" Neue Position: X={LIDAR_X}, Y={LIDAR_Y}, Z={LIDAR_Z}")
            i += 4
            continue
        elif arg == "--quat" and i + 4 < len(sys.argv):
            qx = float(sys.argv[i + 1])
            qy = float(sys.argv[i + 2])
            qz = float(sys.argv[i + 3])
            qw = float(sys.argv[i + 4])
            LIDAR_ROLL, LIDAR_PITCH, LIDAR_YAW = quat_to_rpy(qx, qy, qz, qw)
            print(
                f" Neue Quaternion: x={qx}, y={qy}, z={qz}, w={qw} -> "
                f"Roll={LIDAR_ROLL:.6f}, Pitch={LIDAR_PITCH:.6f}, Yaw={LIDAR_YAW:.6f}"
            )
            i += 5
            continue
        else:
            i += 1
    
    print("=" * 60)
    print("   Unitree Go2 - LiDAR Position Setup")
    print("=" * 60)
    
    # Einmal saftig in den Docker dipp═══════════════════════════════════════════════════════════════╣
    check_docker()
    
    # Alles stoppen und neu starten
    stop_all()
    start_tf_publisher()
    start_kiss_icp()
    start_rviz()
    check_topics()
    
    print_position_help()
    print_rviz_help()
    
    print("\n Setup abgeschlossen!")
    print("   Zum Beenden: python3 lidar_setup.py --stop")


if __name__ == "__main__":
    main()
