# Größter Text (H1)
## Großer Text (H2)
### Mittegroßer Text (H3)

# Unitree Go2 Education: Autonomous Security Patrol SLAM

Dieses Repository enthält die technische Implementierung eines autonomen Security-Roboters auf Basis des **Unitree Go2 Education**. Das Projekt wurde im Rahmen des Moduls "Service- und Industrierobotik" an der **TH Köln** entwickelt.

## 1. Projektübersicht
Das Ziel des Projekts war die Realisierung einer SLAM-basierten Kartierung und Navigation in Innenräumen der TH Köln. Dabei wurde auf zusätzliche 3D-LiDAR-Hardware verzichtet, um die Praxistauglichkeit des serienmäßig verbauten Front-LiDARs zu evaluieren.

### Kernkomponenten:
* **Hardware:** Unitree Go2 Education (Front-LiDAR)
* **Middleware:** ROS 2 Humble (Ubuntu 22.04)
* **Infrastruktur:** Vollständige Containerisierung via Docker

## 2. Systemarchitektur
Die Applikationslogik ist in einem Docker-Container gekapselt, der im `host`-Netzwerkmodus operiert, um eine latenzfreie Kommunikation mit dem Onboard-Rechner des Roboters zu ermöglichen.

* **Datenakquise:** Abruf der Roh-Punktwolken über das offizielle Unitree SDK.
* **Algorithmus:** Einsatz von **KISS-ICP** (LiDAR-only SLAM) nach einem Strategiewechsel von Fast-LIO.

## 3. Aktueller Status und Resultate
Die technische Evaluation zeigt eine erfolgreiche Dateninfrastruktur, jedoch Herausforderungen bei der Kartierung:
* **Stabile Pipeline:** Die Roh-Punktwolken können präzise ausgelesen und in Rviz2 visualisiert werden.
* **Mapping-Instabilität:** Es tritt eine Drift des Koordinatenursprungs (Map-Frame) auf, auch im stationären Zustand.
* **Pathfinding:** Aufgrund der inkonsistenten Kartenqualität konnte eine autonome Pfadplanung bisher nicht stabil umgesetzt werden.

## 4. Installation & Setup

### Voraussetzungen
1. **Unitree SDK:** Stelle sicher, dass das `unitree_ros2_sdk` im `src`-Ordner deines Arbeitsbereichs liegt oder über das Dockerfile eingebunden ist.
2. **Netzwerk:** Eine Ethernet-Verbindung zum Go2 Onboard-Computer wird empfohlen.

### Start der Pipeline
```bash
# Repository klonen
git clone [https://github.com/DumbsterbabyABC/unitree-go2-slam-navigation.git](https://github.com/DumbsterbabyABC/unitree-go2-slam-navigation.git)
cd unitree-go2-slam-navigation

# Docker Image bauen (installiert alle Abhängigkeiten inkl. SDK-Treiber)
docker build -t go2-slam .

# Container starten
docker run --network host go2-slam


## 5. Autoren
* **Namen:** Franz, Lennackers, Nothelle, Schiffmann 
* **Institution:** Fakultät für Fahrzeugsysteme und Produktion, TH Köln 
```


##5. Autoren
Namen: Franz, Lennackers, Nothelle, Schiffmann
Institution: Fakultät für Fahrzeugsysteme und Produktion, TH Köln
