import subprocess
import time
import os

def run_robot_setup():
    # --- TERMINAL 1: Docker Start & Topic Check ---
    # Befehlskette für Terminal 1
    t1_commands = (
        "sudo docker start -ai unitree_ros2_container; "
        "source /basis/unitree_ros2/setup.sh; "
        "ros2 topic list; "
        "ros2 topic echo /utlidar/cloud"
    )
    print("Starte Terminal 1...")
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', t1_commands])
    
    # Kurze Pause, damit der Docker-Container Zeit zum Hochfahren hat
    time.sleep(3)

    # --- TERMINAL 3: Host Display & xhost ---
    # Wir lesen zuerst den Wert am Host aus, um ihn später für Terminal 2 zu nutzen
    host_display = os.environ.get("DISPLAY", ":0")
    t3_commands = f"xhost +local:root; echo 'Host DISPLAY is: {host_display}'; exec bash"
    
    print(f"Starte Terminal 3 (Host Display: {host_display})...")
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', t3_commands])

    # --- TERMINAL 2: Docker Exec, Display Vergleich & RViz ---
    # Hier nutzen wir das 'host_display', um es im Docker zu exportieren
    t2_commands = (
        f"sudo docker exec -it unitree_ros2_container bash -c '"
        f"source /basis/unitree_ros2/setup.sh; "
        f"echo \"Docker initial DISPLAY: \\$DISPLAY\"; "
        f"echo \"Setting DISPLAY to Host value: {host_display}\"; "
        f"export DISPLAY={host_display}; "
        f"rviz2'"
    )
    
    print("Starte Terminal 2 (Docker Exec & RViz)...")
    subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', t2_commands])

if __name__ == "__main__":
    run_robot_setup()