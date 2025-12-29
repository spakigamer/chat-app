import requests
import serial
import serial.tools.list_ports
import time

API_BASE_URL = "http://localhost:5001/api"
EMAIL = "dhruvgoel165@gmail.com"
PASSWORD = "Dhruv#9210"

RECEIVER_ID = "6906eb624668c7295a147754"  # user who receives motion alerts

session = requests.Session()
JWT_TOKEN = None


# ---------------------------------------------------
# AUTO-DETECT ESP32 PORT
# ---------------------------------------------------
def find_esp32_port():
    print("🔍 Scanning COM ports for ESP32...")
    ports = serial.tools.list_ports.comports()

    for port in ports:
        desc = port.description.lower()
        if (
            "usb" in desc or "uart" in desc or "ch340" in desc or
            "cp210" in desc or "esp" in desc
        ):
            print(f"✅ ESP32 detected on: {port.device}")
            return port.device

    print("❌ No ESP32 found. Please reconnect it.")
    return None


# ------------------------------
# LOGIN
# ------------------------------
def python_login():
    global JWT_TOKEN
    print("🔐 Logging in...")

    try:
        res = session.post(
            f"{API_BASE_URL}/auth/python-login",
            json={"email": EMAIL, "password": PASSWORD}
        )

        data = res.json()

        if "token" not in data:
            print("❌ Login failed:", data)
            return False

        JWT_TOKEN = data["token"]

        # 🔥 FORCE token into headers (fixed)
        session.headers.clear()
        session.headers.update({
            "Authorization": f"Bearer {JWT_TOKEN}",
            "Content-Type": "application/json"
        })

        print("🔑 Token attached successfully.")
        print("✅ Login successful!")
        return True

    except Exception as e:
        print("❌ Login error:", e)
        return False


# ------------------------------
# SEND MESSAGE TO BACKEND
# ------------------------------
def send_motion_alert():
    payload = {
        "token": JWT_TOKEN,
        "text": "🚨 Motion detected by ESP32!",
        "image": None
    }

    print("🔎 Current Headers:", session.headers)

    try:
        # FIXED ROUTE → must use /messages/send/<receiverId>
        res = session.post(
            f"{API_BASE_URL}/messages/python-send/{RECEIVER_ID}",
            json=payload
        )

        if res.status_code == 201:
            print("📩 Message sent:", res.json()["_id"])
        else:
            print("❌ Error sending message:", res.text)

    except Exception as e:
        print("❌ Request failed:", e)


# ------------------------------
# READ ESP32 MOTION SENSOR
# ------------------------------
def start_motion_listener():
    while True:
        print("📡 Connecting to ESP32...")
        port = find_esp32_port()

        if port is None:
            time.sleep(2)
            continue

        try:
            ser = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)
            print("📡 Started reading from ESP32...\n")
        except Exception as e:
            print("❌ Failed to open serial port:", e)
            time.sleep(2)
            continue

        while True:
            try:
                raw = ser.readline()

                if not raw:
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
                print("📥 RAW:", line)

                # Accept both: "Sensor: 1" or "1"
                clean = line.replace("Sensor:", "").strip()

                if clean not in ["0", "1"]:
                    continue

                value = int(clean)
                print("Sensor:", value)

                if value == 1:
                    print("🚨 Motion detected! Sending alert...")
                    send_motion_alert()

                time.sleep(0.2)

            except serial.SerialException:
                print("❌ Serial disconnected! Restarting...")
                break

            except KeyboardInterrupt:
                print("🛑 Stopped manually.")
                return

            except Exception as e:
                print("⚠️ Sensor Read Error:", e)


# ------------------------------
# MAIN
# ------------------------------
if python_login():
    start_motion_listener()
else:
    print("❌ Exiting because login failed")
