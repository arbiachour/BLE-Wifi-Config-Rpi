#!/bin/bash

set -e

# Colors for output
green='\e[32m'
red='\e[31m'
reset='\e[0m'

info() {
    echo -e "${green}[INFO]${reset} $1"
}

error() {
    echo -e "${red}[ERROR]${reset} $1"
    exit 1
}

info "Updating system packages..."
sudo apt update || error "Failed to update package list."

info "Installing required system dependencies..."
sudo apt install -y \
    bluetooth \
    bluez \
    python3-dbus \
    python3-gi \
    network-manager || error "Failed to install required packages."

info "Ensuring Python3 and pip are available..."
sudo apt install -y python3 python3-pip || error "Failed to install Python3 or pip."

info "Installing required Python packages..."
pip3 install --upgrade pip
pip3 install PyGObject dbus-python || error "Failed to install Python libraries."

info "Enabling and starting Bluetooth and NetworkManager services..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager

info "Setup Hardware Button Trigger Service..."
#cd BLE-Wifi-Config-Rpi || error "Failed to change directory."
sudo mv ble_characteristic_trigger.service /etc/systemd/system || error "Failed to copy service file."

info "Reloading systemd daemon..."
sudo systemctl daemon-reload || error "Failed to reload systemd daemon."

info "Enabling and starting the hardware button trigger service..."
sudo systemctl enable ble_characteristic_trigger.service || error "Failed to enable service."
sudo systemctl start ble_characteristic_trigger.service || error "Failed to start service."
sudo systemctl status ble_characteristic_trigger.service || error "Failed to check service status."

info "Setup completed successfully!"
echo -e "${green}To run the script, use:${reset} python3 wpa_charateristics.py"
echo -e "${green}To stop the script, use:${reset} Ctrl+C"

info "DEBUG AND MONITORING TIPS:"
echo -e "${green}To check the status of  Bluetooth on Seperate Terminal, use:${reset} sudo bluetoothctl show"
echo -e "${green}To check NetworkManager general status, use:${reset} nmcli general status"
echo -e "${green}To list all network devices, use:${reset} nmcli device status"
echo -e "${green}To scan available Wi-Fi networks, use:${reset} nmcli device wifi list"
echo -e "${green}To check dbus tree, use:${reset} dbus-tree"
echo -e "${green} Restart bluetooth using D-Bus control: ${reset} sudo systemctl restart bluetooth"
echo -e "${green} To check the status of bluetoothd, use:${reset} sudo systemctl status bluetooth"
echo -e "${green} To kill the bluetoothd process, use:${reset} sudo -pkill -f bluetoothd"
echo -e "${green} To start bluetoothd without daemonize, with a clean instance and to monitor live advertisement: ${reset} sudo bluetoothd --noplugin=sap --debug -n &"
echo -e "${green}Reset device history and pairing data: ${reset} sudo rm -rf /var/lib/bluetooth/*"


info "If Bluetooth doesn't work immediately, a system reboot may help: sudo reboot"
info "If you encounter any issues, please check the logs for more information."
info "For further assistance, please refer to the README file or contact mohamedarbi.achour@dewarmte.nl."
