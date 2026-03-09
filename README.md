# Größter Text (H1)
## Großer Text (H2)
### Mittegroßer Text (H3)

# Unitree Go2 Education: Autonomous Security Patrol SLAM

Dieses Repository enthält die technische Implementierung eines autonomen Security-Roboters auf Basis des **Unitree Go2 Education**. Das Projekt wurde im Rahmen des Moduls "Service- und Industrierobotik" an der **TH Köln** (WS 25/26) entwickelt.

## 1. Projektübersicht
[cite_start]Das Ziel des Projekts war die Realisierung einer SLAM-basierten Kartierung und Navigation in Innenräumen der TH Köln[cite: 61]. [cite_start]Dabei wurde bewusst auf zusätzliche, kostspielige 3D-LiDAR-Hardware verzichtet, um die Praxistauglichkeit des serienmäßig verbauten Front-LiDARs zu evaluieren[cite: 62].

### Kernkomponenten:
* [cite_start]**Hardware:** Unitree Go2 Education (Front-LiDAR)[cite: 161, 163].
* [cite_start]**Middleware:** ROS 2 Humble unter Ubuntu 22.04[cite: 157].
* [cite_start]**Infrastruktur:** Vollständige Containerisierung via Docker[cite: 157].

## 2. Systemarchitektur
Die Applikationslogik ist in einem Docker-Container gekapselt, der im `host`-Netzwerkmodus operiert, um eine latenzfreie Kommunikation mit dem Onboard-Rechner des Roboters zu ermöglichen.

* [cite_start]**Datenakquise:** Abruf der Roh-Punktwolken über das Unitree SDK[cite: 162].
* [cite_start]**Algorithmus:** Einsatz von **KISS-ICP** (LiDAR-only SLAM) nach einem Strategiewechsel von Fast-LIO[cite: 160].

## 3. Aktueller Status und Resultate
Die technische Evaluation zeigt eine erfolgreiche Dateninfrastruktur, jedoch erhebliche Herausforderungen bei der Kartierung:

* [cite_start]**Stabile Pipeline:** Die Roh-Punktwolken können präzise ausgelesen und in Rviz2 visualisiert werden[cite: 170].
* [cite_start]**Mapping-Instabilität:** Es tritt eine signifikante Drift des Koordinatenursprungs (Map-Frame) auf, auch im stationären Zustand[cite: 177, 181].
* [cite_start]**Pathfinding:** Aufgrund der inkonsistenten Kartenqualität konnte eine autonome Pfadplanung bisher nicht zielführend umgesetzt werden[cite: 173].

## 4. Installation
```bash
# Repository klonen
git clone [https://github.com/DumbsterbabyABC/unitree-go2-slam-navigation.git](https://github.com/DumbsterbabyABC/unitree-go2-slam-navigation.git)

# Docker Image bauen
docker build -t go2-slam .

# Start der Pipeline
docker run --network host go2-slam
```


## 5. Autoren
* [cite_start]**Namen:** Franz, Lennackers, Nothelle, Schiffmann 
* [cite_start]**Institution:** Fakultät für Fahrzeugsysteme und Produktion, TH Köln [cite: 2, 10, 15]
