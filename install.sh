#!/bin/bash

# Exit on any error
set -e

# Update and Upgrade System
sudo apt update
sudo apt upgrade -y

# Install Python3.9 and necessary tools
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.9 python3-pip python3.9-venv git wget unzip build-essential libboost-dev -y

# Create and activate virtual environment
python3.9 -m venv myenv
source myenv/bin/activate

# Install Python Libraries
pip install asyncio prettytable numpy pythonmonkey

# Check for the presence of main.py, simulator.py, optimizer.py, and engine.py to determine if we are in the bustabit-hyperopt directory
if !([ -f "main.py" ] && [ -f "simulator.py" ] && [ -f "optimizer.py" ] && [ -f "engine.py" ];) then
  echo "Cloning the bustabit-hyperopt repository..."
  git clone https://github.com/dsetzer/bustabit-hyperopt.git
  cd bustabit-hyperopt
fi

# At this point, the environment is set up and ready to run the project
echo "Setup completed. To run the project, activate the virtual environment with 'source myenv/bin/activate', then navigate to the bustabit-hyperopt directory and run 'python3 main.py'."
