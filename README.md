# Digital Twin for Gelcoating Process 

## Overview
This project aims to enhance the gelcoating process at TRYGONS SA by integrating a sophisticated digital twin developed in collaboration with iThermAI. The digital twin provides real-time tracking, predictive maintenance, and enhanced monitoring capabilities, significantly improving product quality, reducing downtime, and increasing operational efficiency.

![Diagram](Dashboard/assets/screenshots/diagram.jpg?raw=true)


## Key Features
- Real-time monitoring of gelcoating parameters
- Predictive maintenance alerts for pumps and filters
- Remote access and control through a user-friendly React dashboard
- Data logging and historical analysis for continuous process improvement
- Integration with existing robotic and pump control systems

## Project Objectives
- Reduce unplanned downtime and maintenance costs
- Improve product quality and consistency
- Enable real-time problem detection and immediate corrective actions
- Enhance overall operational efficiency and scalability

## Installation

### 1. React Dashboard
1. Navigate to the `dashboard` directory:
   ```sh
   cd dashboard
   ```
2. Install the required packages (Required only for the first time):
   ```sh
   npm install
   ```
3. Update the ip attribute in `./src/ip_backend.json` to match the backend device's IP address.
4. Start the dashboard:
   ```sh
   npm start
   ```
#### screenshots:
   ![Diagram](Dashboard/assets/screenshots/dashboard.jpg?raw=true)
   ![Diagram](Dashboard/assets/screenshots/charts.jpg?raw=true)
   ![Diagram](Dashboard/assets/screenshots/history.jpg?raw=true)
### 2. Agent, API, and Database
1. Navigate to the backend directory (on the backend device)
   ```sh
   cd backend
   ```
2. Build the Docker environment (Required only for the first time):
   ```sh
   docker-compose build
   ```
3. run the Docker environment:
   ```sh
   docker-compose up
   ```
### 3. Rotary Encoder
1. Make sure the docker environment is running, then navigate to the rotary directory:
   ```sh
   cd backend/rotary
   ```
2. Install the required Python packages (Required only for the first time):
   ```sh
   pip install -r requirements.txt
   ```
3. Start the data recording process:
   ```sh
   python app.py
   ```

## Contributors
- **TRYGONS SA**: Provided manufacturing infrastructure, integrated digital twin system, dataset collection, and validation.

- **iThermAi**: Developed models, algorithms, and the dashboard for the digital twin.
