# BLE WiFi Configurator for Raspberry Pi

This project enables configuration of WiFi credentials on a Raspberry Pi using a Bluetooth Low Energy (BLE) interface. A BLE GATT service exposes a characteristic allowing the user to write new WiFi settings, which are then applied automatically.

## ✨ Features

- BLE GATT service to read/write WiFi settings (`/etc/wpa_supplicant/wpa_supplicant.conf`)
- Configurable via mobile app or BLE client (e.g., nRF Connect)
- Triggered via physical GPIO button
- Systemd service for persistent startup
- Installer script for easy setup

## ⚙️ Hardware Requirements

- Raspberry Pi (tested on Pi 3 / 4)
- Push button connected to GPIO2
- Bluetooth enabled

## 📁 Project Structure

```
/ble
  ├── ble_characteristic_trigger.py      # Launches BLE service on button press
  ├── wpa_characteristics.py             # GATT service and characteristic
  ├── install.sh                         # Setup script
  └── requirements.txt                   # Python dependencies
ble_trigger.service                      # systemd service file
```

## 🚀 Setup Instructions

1. **Clone the repo**:

```bash
git clone https://github.com/arbiachour/ble-wifi-configurator.git
cd ble-wifi-configurator
```

2. **Install dependencies and setup**:

```bash
chmod +x install.sh
./install.sh
```

3. **Enable and start the service**:

```bash
sudo cp ble_trigger.service /etc/systemd/system/
sudo systemctl daemon-reexec
sudo systemctl enable ble_trigger.service
sudo systemctl start ble_trigger.service
```

## 📡 How it works

- On pressing the GPIO2-connected button, the BLE service starts.
- The GATT characteristic exposes:
  - **Read**: Current SSID
  - **Write**: JSON config (`{"ssid": "yourSSID", "psk": "yourPassword"}`)
- On successful write, the Pi restarts `wpa_supplicant` and connects to the new WiFi.

## 🧪 Test with nRF Connect

- Connect to device "Arbi" (Feel free to change the name if needed)
- Discover services
- Locate the characteristic with UUID: `4321f8d2-9f96-4f58-a53d-fc7550e7c15e` (Feel free to change the uuid of the characteristic)
- Write new config as JSON string

Example:

```json
{
  "ssid": "MyNetwork",
  "psk": "MyPassword"
}
```

## 📃 Logs

- BLE logs: `/home/pi/ble.log`
- WiFi config logs: `/home/pi/able.log`

## 🔐 Permissions

Ensure `/etc/wpa_supplicant/wpa_supplicant.conf` is owned by user `pi` to allow write access.

## 📋 License

[MIT](LICENSE)

## 🤝 Contributions

PRs welcome! Feel free to fork and propose improvements.

