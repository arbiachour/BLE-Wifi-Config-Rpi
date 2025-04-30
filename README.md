# Advertise WPA Configuration Over BLE (Button-Triggered)

This project provides a way to **advertise** and **configure Wi-Fi (WPA) settings** for a device using **Bluetooth Low Energy (BLE)**, triggered manually by a **physical button**.

## Project Structure

- `gatt_module.py`:  
  Core BLE GATT server framework built on top of BlueZ using D-Bus.

- `advertise_wpa.py`:  
  BLE GATT service to expose Wi-Fi scanning, configuration, and status reporting.

- `ble_wifi_trigger.py`:  
  Listens for a GPIO button press to start the BLE advertisement and server (optional).

- `ble_wifi_trigger.service`:  
  Systemd service file to run the ble_wifi_trigger script at system boot (optional).

- `install.sh`:  
  Installer script to set up system and Python dependencies automatically (optional).

## Features

- BLE Advertising starts only **on physical button press** (GPIO2).
- BLE Service exposes:
  - **Read** available Wi-Fi networks.
  - **Write** Wi-Fi SSID and password.
  - **Notify** connection result and IP address.
- **Secure BLE pairing** supported with Agent (`KeyboardDisplay` capability).
- **Idle timeout** and **auto-disconnection** if the user stays inactive.
- **Service auto-restart** mechanism if Wi-Fi connection fails.

## Requirements

- Raspberry Pi running Linux.
- Bluetooth Low Energy (BLE) support.
- Python 3.7+
- Installed system libraries:
  - `bluez`
  - `python3-dbus`
  - `python3-gi`
  - `network-manager`
  - `python3-gpiozero`

Install the necessary system dependencies manually:

```bash
sudo apt update
sudo apt install -y bluetooth bluez python3-dbus python3-gi network-manager python3-gpiozero
```

Or use the provided installer:

```bash
chmod +x install.sh
./install.sh
```

The installer also provides useful **debugging tips** and **commands** to troubleshoot Bluetooth and NetworkManager.

## Getting Started

### 1. Connect Button

Wire a button between **GPIO2 (Pin 3)** and **GND**.

### 2. Clone the repository

```bash
git clone https://github.com/DeWarmteNL/GATT_WIFI_SETUP.git
cd GATT_WIFI_SETUP
```

### 3. Run the BLE Trigger

```bash
python3 ble_wifi_trigger.py
```


### 4. Connect and Configure

- Press the button to start BLE advertising.
- Use a BLE app (e.g., **nRF Connect**) to discover your device (hostname as BLE name).
- Interact with the BLE service:
  - **Read** SSIDs.
  - **Write** credentials as JSON:

    ```json
    {
      "ssid": "YourWiFiSSID",
      "psk": "YourWiFiPassword"
    }
    ```

- Receive connection status notifications.

## BLE Service Overview

- **Service UUID**: `00001801-0000-1000-9000-00805f9b34fb`
- **Characteristic UUID**: `00001801-0000-1000-6000-00805f9b34fb`
  - **Read**: Available Wi-Fi networks.
  - **Write**: Wi-Fi credentials.
  - **Notify**: Status and IP address.

## File Descriptions

| File | Description |
|:-----|:------------|
| `gatt_server.py` | Core GATT server components (services, characteristics, agent, advertisements). |
| `wpa_characteristics.py` | BLE GATT server for Wi-Fi configuration. |
| `ble_characteristic_trigger.py` | Button event detection to trigger BLE interface. |
| `ble_characteristic_trigger.service` | Systemd unit to auto-launch `ble_wifi_trigger.py` at boot (optional). |
| `install.sh` | Setup script to install all required system and Python dependencies automatically. |

## Flow Example

1. Raspberry Pi boots.
2. User presses the button.
3. BLE advertising starts.
4. User connects via BLE and submits Wi-Fi credentials.
5. Raspberry Pi connects to Wi-Fi and updates client via notification.
6. After inactivity, BLE connection is closed.

## Important Notes

- **GPIO Button Configuration:** Button must be connected properly (Pull-down recommended).
- **Bluetooth Must be Powered:** Script ensures Bluetooth is powered on before starting BLE services.
- **Idle Disconnects:** BLE disconnects after 5 minutes of inactivity automatically.
- **Secure BLE Pairing:** Device pairing uses the `KeyboardDisplay` IO capability.
- **Installer Help:** After running `install.sh`, useful debug commands are shown to help troubleshoot networking or Bluetooth issues.

## Author

- Developed by **Mohamed Arbi Achour** (DeWarmte)
# Advertise WPA Configuration Over BLE (Button-Triggered)

This project provides a way to **advertise** and **configure Wi-Fi (WPA) settings** for a device using **Bluetooth Low Energy (BLE)**, triggered manually by a **physical button**.

## Project Structure

- `gatt_server.py`:  
  Core BLE GATT server framework built on top of BlueZ using D-Bus.

- `wpa_charateristics.py`:  
  BLE GATT service to expose Wi-Fi scanning, configuration, and status reporting.

- `ble_characteristic_trigger.py`:  
  Listens for a GPIO button press to start the BLE advertisement and server (optional).

- `ble_characteristic_trigger.service`:  
  Systemd service file to run the ble_wifi_trigger script at system boot (optional).

- `install.sh`:  
  Installer script to set up system and Python dependencies automatically (optional).

## Features

- BLE Advertising starts only **on physical button press** (GPIO2).
- BLE Service exposes:
  - **Read** available Wi-Fi networks.
  - **Write** Wi-Fi SSID and password.
  - **Notify** connection result and IP address.
- **Secure BLE pairing** supported with Agent (`KeyboardDisplay` capability).
- **Idle timeout** and **auto-disconnection** if the user stays inactive.
- **Service auto-restart** mechanism if Wi-Fi connection fails.

## Requirements

- Raspberry Pi running Linux.
- Bluetooth Low Energy (BLE) support.
- Python 3.7+
- Installed system libraries:
  - `bluez`
  - `python3-dbus`
  - `python3-gi`
  - `network-manager`
  - `python3-gpiozero`

Install the necessary system dependencies manually:

```bash
sudo apt update
sudo apt install -y bluetooth bluez python3-dbus python3-gi network-manager python3-gpiozero
```

Or use the provided installer:

```bash
chmod +x install.sh
./install.sh
```

The installer also provides useful **debugging tips** and **commands** to troubleshoot Bluetooth and NetworkManager.

## Getting Started

### 1. Connect Button

Wire a button between **GPIO2 (Pin 3)** and **GND**.

### 2. Clone the repository

```bash
git clone https://github.com/DeWarmteNL/GATT_WIFI_SETUP.git
cd GATT_WIFI_SETUP
```

### 3. Run the BLE Trigger

```bash
python3 ble_wifi_trigger.py
```


### 4. Connect and Configure

- Press the button to start BLE advertising.
- Use a BLE app (e.g., **nRF Connect**) to discover your device (hostname as BLE name).
- Interact with the BLE service:
  - **Read** SSIDs.
  - **Write** credentials as JSON:

    ```json
    {
      "ssid": "YourWiFiSSID",
      "psk": "YourWiFiPassword"
    }
    ```

- Receive connection status notifications.

## BLE Service Overview

- **Service UUID**: `00001801-0000-1000-9000-00805f9b34fb`
- **Characteristic UUID**: `00001801-0000-1000-6000-00805f9b34fb`
  - **Read**: Available Wi-Fi networks.
  - **Write**: Wi-Fi credentials.
  - **Notify**: Status and IP address.

## File Descriptions

| File | Description |
|:-----|:------------|
| `gatt_module.py` | Core GATT server components (services, characteristics, agent, advertisements). |
| `advertise_wpa.py` | BLE GATT server for Wi-Fi configuration. |
| `ble_wifi_trigger.py` | Button event detection to trigger BLE interface. |
| `ble_wifi_trigger.service` | Systemd unit to auto-launch `ble_wifi_trigger.py` at boot (optional). |
| `install.sh` | Setup script to install all required system and Python dependencies automatically. |

## Flow Example

1. Raspberry Pi boots.
2. User presses the button.
3. BLE advertising starts.
4. User connects via BLE and submits Wi-Fi credentials.
5. Raspberry Pi connects to Wi-Fi and updates client via notification.
6. After inactivity, BLE connection is closed.

## Important Notes

- **GPIO Button Configuration:** Button must be connected properly (Pull-down recommended).
- **Bluetooth Must be Powered:** Script ensures Bluetooth is powered on before starting BLE services.
- **Idle Disconnects:** BLE disconnects after 5 minutes of inactivity automatically.
- **Secure BLE Pairing:** Device pairing uses the `KeyboardDisplay` IO capability.
- **Installer Help:** After running `install.sh`, useful debug commands are shown to help troubleshoot networking or Bluetooth issues.

## Author

- Developed by **Mohamed Arbi Achour** (DeWarmte)
