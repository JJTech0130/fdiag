import serial
from serial.tools import list_ports
import time

class CANError(Exception):
    """Custom exception for CAN-related errors."""
    pass

class ELM327:
    def __init__(self, port, baud):
        self.port = port
        self.baud = baud
        self.ser = None

    def connect(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=None) # No timeout is set

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def defaults(self):
        # Some sane default settings to make things work nicely
        self.reset()
        self.disable_spaces()
        self.allow_long_messages()

    def write_command(self, command: str, expect_echo: bool = True) -> str:
        if not self.ser or not self.ser.is_open:
            raise serial.SerialException("Serial port is not open.")
        self.ser.write((command + '\r\n').encode('utf-8'))
        if expect_echo:
            self.ser.read_until(b"\r")
        resp =  self.ser.read_until(b">").decode('utf-8').replace('\r', '\n').replace('\n\n>', '').strip()
        #print(f"Command: {command}, Response: {resp}")
        return resp
    
    def write_obd(self, header: bytes | int, data: bytes) -> bytes:
        # This won't work properly if response is segmented (with ISO-TP)!
        if isinstance(header, int):
            header = header.to_bytes(3, byteorder='big')
        self._set_header(header)
        resp = self.write_command(data.hex().upper())
        if resp == "CAN ERROR":
            raise CANError()
        if resp == "NO DATA":
            return b""
        return bytes.fromhex(resp)

    def reset(self):
        assert self.write_command("ATZ")

    def _set_header(self, header: bytes):
        assert self.write_command(f"ATSH{header.hex().upper()}") == "OK", "Failed to set header"

    def read_voltage(self) -> float:
        response = self.write_command("ATRV")
        voltage_str = response[:-1].strip()
        return float(voltage_str)

    def disable_spaces(self):
        assert self.write_command("ATS0") == "OK", "Failed to disable spaces"

    def allow_long_messages(self):
        assert self.write_command("ATL1") == "OK", "Failed to allow long messages"
    
class OBDLink(ELM327):
    def __init__(self, port):
        super().__init__(port, 115200)

    def defaults(self):
        super().defaults()
        self.enable_segmentation()

    def write_obd(self, header: bytes | int, data: bytes) -> bytes:
        if isinstance(header, int):
            # STPX won't accept 3-byte headers?
            header = header.to_bytes(2, byteorder='big')
        resp = self.write_command(f"STPXh:{header.hex().upper()},d:{data.hex().upper()},r:1")
        if resp == "CAN ERROR":
            raise CANError()
        if resp == "NO DATA":
            return b""
        return bytes.fromhex(resp)

    def device_id(self):
        response = self.write_command("STDI")
        return response.strip()

    def _set_protocol(self, protocol: int):
        if protocol < 11:
            # Use AT command
            assert self.write_command(f"ATSP {protocol}") == "OK", "Failed to set protocol"
        else:
            # Use STP command
            assert self.write_command(f"STP {protocol}") == "OK", "Failed to set protocol"
        print(f"Protocol set to {protocol}")
        
    def _set_baud(self, baud: int):
        assert self.write_command(f"STPBR {baud}") == "OK", "Failed to set baud rate"

    def enable_segmentation(self):
        # Segmentation on received messages will automatically re-assemble ISO-TP messages
        # You should use STPX for this to work
        assert self.write_command("STCSEGR1") == "OK", "Failed to enable segmentation"

    def clear_flow_control(self):
        assert self.write_command("STCCFCP") == "OK", "Failed to clear flow control"

    def add_flow_control_address_pair(self, pair: tuple):
        if len(pair) != 2:
            raise ValueError("Flow control address pair must be a tuple of two addresses.")
        command = f"STCAFCP{pair[0].upper()},{pair[1].upper()}"
        assert self.write_command(command) == "OK", f"Failed to add flow control address pair {pair}"
        
class UDS:
    def __init__(self, adapter: OBDLink):
        self.adapter = adapter

    def read_data_by_identifier(self, target: bytes | int, identifier: int) -> bytes:
        response = self.adapter.write_obd(target, b"\x22" + identifier.to_bytes(2, byteorder='big'))
        if response.startswith(b"\x62"):
            data = response[3:]
            return data
        else:
            raise ValueError("Failed to read data by identifier", response.hex())

    def tester_present(self, target: bytes | int) -> bool:
        try:
            response = self.adapter.write_obd(target, b"\x3E\x00")
        except CANError:
            return False
        if response.startswith(b"\x7E"):
            return True
        return False
    
    def wait_for_tester_present(self, target: bytes | int, timeout: float | None = None) -> bool:
        start_time = time.time()
        while True:
            if self.tester_present(target):
                return True
            if timeout is not None and (time.time() - start_time) > timeout:
                return False
            time.sleep(0.1)

    def read_dtcs(self, target: bytes | int, status_mask: int = 0xFF) -> list:
        # TODO: Use status mask in request
        response = self.adapter.write_obd(target, b"\x19\x02\xFF")
        if response[0] == 0x59:
            print(f"Raw DTC response: {response.hex().upper()}")
            # Byte 1 is subfunction echoed back, byte 2 is the DTC status availability mask count
            dtcs = []
            payload = response[3:]

            dtcs = []
            for i in range(0, len(payload), 4):
                if i + 3 >= len(payload):
                    break
                b1, b2, ftb, status = payload[i:i+4]
                if status & status_mask == 0:
                    continue  # Skip DTCs that do not match the status mask

                dtc_num = f"{b1:02X}{b2:02X}{ftb:02X}"  # e.g., "F00004"
                dtcs.append(dtc_num)

            return dtcs
        else:
            raise ValueError("Failed to read DTCs", response.hex())

def interactive(port):
    elm = OBDLink(port)
    try:
        elm.connect()
        
        print(f"Connected to {port} ({elm.device_id()})")
        while True:
            command = input("Enter ELM327 command (or 'exit' to quit): ")
            if command.lower() == 'exit':
                break
            try:
                response = elm.write_command(command)
                print(f"Response: {response}")
            except serial.SerialException as e:
                print(f"Error: {e}")
    finally:
        elm.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    ports = list_ports.comports()
    if ports:
        print("Connected serial ports:")
        i = 1
        for port in ports:
            print(f"{i}: {port.description}: {port.device}")
            i += 1
    else:
        print("No serial ports found.")

    if len(ports) == 1:
        port_number = "1"
    else:
        port_number = input("Select a port number: ")
    try:
        port_number = int(port_number) - 1
        if port_number < 0 or port_number >= len(ports):
            raise ValueError("Invalid port number.")
        selected_port = ports[port_number].device
        interactive(selected_port)
    except (ValueError, IndexError) as e:
        print(f"Error: {e}")