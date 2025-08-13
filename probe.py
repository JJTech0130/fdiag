import sys
import time
from obdlink import *
from mdx import parse_mdx, interpret_dtc  # Your earlier parsing code

def probe_using_mdx(diag: UDS, mdx_path, ecu_addr=0x716):
    # Parse MDX to get DID definitions
    parsed = parse_mdx(mdx_path)



    print(f"Waiting for ECU {hex(ecu_addr)}...")
    diag.wait_for_tester_present(ecu_addr, timeout=10)
    print(f"Connected to ECU {hex(ecu_addr)}\n")

    print("===== Reading All DIDs from MDX =====")
    for did_num, did_info in parsed["dids"].items():
        try:
            # Try to interpret DID as hex
            if did_num.startswith("0x") or did_num.startswith("0X"):
                did_val = int(did_num, 16)
            else:
                did_val = int(did_num, 16) if did_num else None
            if did_val is None:
                continue

            # Read from ECU
            raw = diag.read_data_by_identifier(ecu_addr, did_val)
            try:
                # Attempt to decode as UTF-8 string, strip NULs
                decoded = raw.decode("ascii", errors="strict").rstrip("\x00")
                # Check for empty string
                if not decoded:
                    raise ValueError("Empty string after decoding")
                # Check for nonprintable characters
                if not all(c.isprintable() or c.isspace() for c in decoded):
                    raise ValueError("Non-printable characters found")
                print(f"{did_num} ({did_info['name']}): {decoded}")
            except Exception:
                # Fall back to b''
                print(f"{did_num} ({did_info['name']}): {raw}")
        except Exception as e:
            print(f"{did_num} ({did_info['name']}): ERROR - {e}")

    print("\n===== Reading and Interpreting DTCs =====")
    try:
        dtcs = diag.read_dtcs(ecu_addr)
        if not dtcs:
            print("No stored DTCs")
        else:
            for code in dtcs:
                dtc_info = interpret_dtc(parsed, code)
                if dtc_info:
                    print(f"{code} - {dtc_info['base_description']}: {dtc_info['failure_description']}")
                else:
                    print(f"{code} - (Unknown DTC)")
    except Exception as e:
        print("Error reading DTCs:", e)

if __name__ == "__main__":
    from serial.tools import list_ports
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_mdx>")
        sys.exit(1)
    mdx_path = sys.argv[1]
    idle_flag = "--idle" in sys.argv

    ports = list_ports.comports()
    if not ports:
        print("No serial ports found.")
        sys.exit(1)

    if len(ports) == 1:
        selected_port = ports[0].device
    else:
        print("Available serial ports:")
        for i, p in enumerate(ports, start=1):
            print(f"{i}: {p.description} ({p.device})")
        idx = int(input("Select port: ")) - 1
        if idx < 0 or idx >= len(ports):
            print("Invalid selection")
            sys.exit(1)
        selected_port = ports[idx].device

    elm = OBDLink(selected_port)
    elm.connect()
    elm.defaults()
    diag = UDS(elm)

    probe_using_mdx(diag, mdx_path)
    if idle_flag:
        print("Keeping the connection alive. Press Ctrl+C to exit.")
        try:
            while True:
                diag.tester_present(0x716)
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")