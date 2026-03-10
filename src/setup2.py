import subprocess
import os
import time


def run_unitree_setup():

    print("ugabooga")
    env=os.environ.copy()

    #Terminal 1

    print("Terminal 1: Setup start")
    subprocess.run(["sudo", "docker", "start", "-ai", "unitree_ros2_container"])
    docker_cmd = "source /basis/unitree_ros2/setup.sh && ros2 topic list && ros2 topic echo /utlidar/cloud"


    #Terminal 3

    subprocess.run(["xhost", "+local:root"])


    #Terminal 2

    print("Terminal 2: setup start")
    subprocess.run(["sudo", "docker", "exec", "-it", "unitree_ros2_container", "bash"])
    docker_cmd = "source /basis/unitree_ros2/setup.sh && echo $DISPLAY"


if __name__ == "__maim__":
    print("ugabooga1")
    run_unitree_setup()