#!/bin/bash

# Create BLE folder under /home/pi
BLE_DIR="/home/pi/ble"
if [ ! -d "$BLE_DIR" ]; then
    mkdir -p "$BLE_DIR"
    echo "Created directory: $BLE_DIR"
else
    echo "Directory already exists: $BLE_DIR"
fi

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip3 install -r requirements.txt
else
    echo "requirements.txt not found. Skipping installation."
fi

# Create log files
LOG_FILE1="/home/pi/dewarmtewpable.log"
LOG_FILE2="/home/pi/dewarmteble.log"

touch "$LOG_FILE1" "$LOG_FILE2"
echo "Created log files: $LOG_FILE1, $LOG_FILE2"

# Give pi user permission for the log files
chown pi:pi "$LOG_FILE1" "$LOG_FILE2"
chmod 644 "$LOG_FILE1" "$LOG_FILE2"
echo "Set ownership and permissions for log files."

# Give pi owner permission on /etc/wpa_supplicant/wpa_supplicant.conf
WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"
if [ -f "$WPA_CONF" ]; then
    chown pi:pi "$WPA_CONF"
    echo "Set ownership for $WPA_CONF"
else
    echo "$WPA_CONF not found. Skipping ownership change."
fi

echo "Script execution completed."