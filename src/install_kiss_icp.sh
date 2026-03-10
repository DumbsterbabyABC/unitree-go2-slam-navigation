#!/bin/bash
# KISS-ICP Installation im Docker Container
# Einfacher LiDAR-SLAM der nur Pointcloud braucht

echo "=========================================="
echo "  KISS-ICP Installation für Unitree Go2"
echo "=========================================="

# Im Container ausführen
sudo docker exec -it unitree_ros2_container bash -c '
    set -e
    
    echo "[1/4] ROS2 Environment laden..."
    source /opt/ros/humble/setup.bash
    
    echo "[2/4] KISS-ICP installieren..."
    pip3 install kiss-icp
    
    echo "[3/4] ROS2 Wrapper installieren..."
    apt-get update
    apt-get install -y ros-humble-kiss-icp 2>/dev/null || {
        echo "Installiere von Source..."
        mkdir -p /root/kiss_ws/src
        cd /root/kiss_ws/src
        git clone https://github.com/PRBonn/kiss-icp.git
        cd /root/kiss_ws
        colcon build --packages-select kiss_icp
        echo "source /root/kiss_ws/install/setup.bash" >> ~/.bashrc
    }
    
    echo "[4/4] Fertig!"
    echo ""
    echo "KISS-ICP starten mit:"
    echo "  ros2 launch kiss_icp odometry.launch.py topic:=/utlidar/cloud"
'

echo ""
echo "Installation abgeschlossen!"
echo ""
echo "Starte KISS-ICP mit:"
echo "  python3 Setup_slam.py"
