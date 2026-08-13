"""
arduino_helper.py
-----------------
Hilfsfunktionen für den automatischen Verbindungsaufbau und die Kommunikation
mit einem Arduino über die serielle Schnittstelle (pySerial) inkl. Wiederverbindung.
"""

import serial
import serial.tools.list_ports
import time

# -------------------- Standardwerte --------------------
BAUD = 115200
START_MESSAGE = "I'm waiting for response: Quizconsole for Buzz"
RECONNECT_DELAY = 2  # Sekunden warten, bevor neu gesucht wird


# -------------------- Arduino finden --------------------
def find_arduino(baudrate: int = BAUD, target_message: str = START_MESSAGE, max_wait: int = 0.5) -> serial.Serial | None:
    ports = [p.device for p in serial.tools.list_ports.comports()]
    print("🔎 Verfügbare COM-Ports:", ports)

    for port in ports:
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            time.sleep(2)  # Arduino Reset abwarten
            ser.reset_input_buffer()

            start = time.time()
            while time.time() - start < max_wait:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if target_message in line:
                        print(f"✅ Arduino gefunden auf {port}")
                        return ser
                time.sleep(0.1)
            ser.close()
        except (serial.SerialException, OSError):
            pass

    print("⚠️ Kein Arduino gefunden.")
    return None


# -------------------- Verbindung aufbauen --------------------
def connect_arduino() -> serial.Serial | None:
    ser = find_arduino()
    if ser:
        print(f"🔗 Verbindung hergestellt mit {ser.port}")
    return ser


# -------------------- Zeile vom Arduino lesen (sicher) --------------------
def read_arduino_line(ser: serial.Serial) -> str | None:
    try:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"⬅️  Arduino sendet: {line}")
                return line
    except serial.SerialException as e:
        # Verbindung weg
        print(f"⚠️ Arduino-Verbindung verloren: {e}")
        try:
            ser.close()
        except:
            pass
        return None
    return None


# -------------------- Nachricht an Arduino senden --------------------
def send_to_arduino(ser: serial.Serial, message: int | str):
    try:
        if isinstance(message, int):
            msg = f"{message}\n"
        else:
            msg = str(message) + "\n"
        ser.write(msg.encode('utf-8'))
        #print(f"➡️  Python sendet: {msg.strip()}")
    except serial.SerialException as e:
        print(f"⚠️ Fehler beim Senden: {e}")


# -------------------- Wiederverbindungs-Loop --------------------
def ensure_connection(ser: serial.Serial | None) -> serial.Serial | None:
    """
    Prüft, ob die Verbindung noch steht. Wenn nicht, versucht sie neu zu verbinden.
    """
    if ser is None:
        print("🔄 Versuche, Arduino wieder zu verbinden...")
        ser = connect_arduino()
        if ser:
            print("✅ Arduino wieder verbunden")
        else:
            print(f"⏱ Warte {RECONNECT_DELAY}s, bevor erneut gesucht wird")
            time.sleep(RECONNECT_DELAY)
    return ser


# -------------------- Beispiel Hauptloop --------------------
def main():
    ser = connect_arduino()
    start_message_handled = False

    while True:
        ser = ensure_connection(ser)
        if ser is None:
            continue

        line = read_arduino_line(ser)
        if line is None:
            continue

        # Startmeldung einmal beantworten
        if not start_message_handled and START_MESSAGE in line:
            send_to_arduino(ser, 2)
            start_message_handled = True
            continue

        # Beispiel: auf Zahl 1 reagieren
        if line.isdigit() and int(line) == 1:
            send_to_arduino(ser, 2)

        time.sleep(0.05)


# -------------------- Startpunkt --------------------
if __name__ == "__main__":
    main()
