# Wibutler Integration for Home Assistant

![Wibutler Logo](https://raw.githubusercontent.com/patrickweh/ha-wibutler/main/custom_components/wibutler/logo.png)

This is a custom component for integrating **Wibutler** devices into **Home Assistant**. It enables communication with your Wibutler hub and provides support for various devices such as sensors, switches, climate devices, and more.

## ⚡ Features
- ✅ WebSocket-based real-time updates
- ✅ Supports **binary sensors, switches, climate controls, covers, and more**
- ✅ Full integration with Home Assistant's entity model

## 🚀 Installation

### **1️⃣ Install via HACS (Recommended)**
1. Go to **HACS → Integrations**.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Add this repository URL:
   ```
   https://github.com/patrickweh/ha-wibutler
   ```
   and select **Integration** as the category.
4. Click **Add** and wait for HACS to find the repository.
5. After installation, restart Home Assistant.

### **2️⃣ Manual Installation**
1. Download the latest release from the repository.
2. Extract the files and place them in:
   ```
   /config/custom_components/wibutler/
   ```
3. Restart Home Assistant.

## 🛠️ Configuration
1. In Home Assistant, go to **Settings → Devices & Services**.
2. Click **Add Integration** and search for **Wibutler**.
3. Enter your **Wibutler hub’s IP address** and authentication details.
4. Click **Submit**.

## 🏠 Available Entities
| Entity Type      | Description                            |
|-----------------|--------------------------------|
| `binary_sensor` | Button states (e.g., pressed/released) |
| `switch`        | Relay switches for lights, power, etc. |
| `climate`       | Heating and cooling controls |
| `sensor`        | Temperature, humidity, energy sensors |
| `cover`         | Shutters, blinds, and similar |

## 📌 Notes
- This integration uses **WebSocket connections** to ensure near real-time updates.
- Some devices may require additional configuration on your Wibutler hub before they appear in Home Assistant.

## 📖 Troubleshooting
If you encounter issues:
- Check **Home Assistant logs** for errors.
- Restart Home Assistant after installation.
- Ensure your **Wibutler hub is reachable** over the network.

## 📝 License
This project is licensed under the **MIT License**.

---

_This is a community project and not officially affiliated with Wibutler GmbH._

