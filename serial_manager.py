from arduino_helper import (
    connect_arduino,
    read_arduino_line,
    send_to_arduino,
    START_MESSAGE,
)

import serial
import time


class SerialManager:

    def __init__(self):

        self.ser = None
        self.connected = False
        self.handshake = False

    def connect(self):
        try:

            self.ser = connect_arduino()
            if self.ser:

                self.connected = True
                self.handshake = False
                self.notify_status()

                return True

        except Exception as e:
            print("Arduino Connect Fehler:", e)

        self.connected = False
        self.ser = None

        return False
    def disconnect(self):

        if self.ser:

            try:
                self.ser.close()

            except:
                pass

        self.ser = None
        self.connected = False
        self.handshake = False

        self.notify_status()

    def reconnect(self):
        self.disconnect()
        time.sleep(1)
        return self.connect()

    def update(self):
        if not self.ser:
            self.connected = False
            return

        try:

            if not self.ser.is_open:
                self.disconnect()
                return

            line = read_arduino_line(self.ser)

        except (serial.SerialException, OSError):

            self.disconnect()
            return None

        if line is None:
            return None

        line = line.strip()

        if not self.handshake:

            if line == START_MESSAGE:

                try:

                    send_to_arduino(
                        self.ser,
                        "1"
                    )

                    self.handshake = True
                    self.notify_status()

                except:

                    self.disconnect()

            return None


        return line

    def send(self, text):

        if not self.connected:
            return False

        try:

            send_to_arduino(self.ser, text)

            return True

        except (serial.SerialException, OSError):

            self.disconnect()

            return False

    def notify_status(self):

        from app import socketio

        socketio.emit(
            "status_update",
            {
                "connected": self.connected,
                "handshake": self.handshake
            }
        )

    def connect_dmx(self):

        return self.send("CONNECT")


    def send_event(self, event):

        return self.send(f"E{event}")


    def send_dmx(self, command):

        return self.send(command)


    def send_scene(self, data):

        return self.send(
            "S;" + data
        )


    def clear_dmx(self):

        return self.send("C")