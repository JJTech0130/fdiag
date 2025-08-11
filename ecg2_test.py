from obdlink import *
import time

def bcd_decode(data: bytes, decimals: int):
    '''
    Decode BCD number
    '''
    res = 0
    for n, b in enumerate(reversed(data)):
        res += (b & 0x0F) * 10 ** (n * 2 - decimals)
        res += (b >> 4) * 10 ** (n * 2 + 1 - decimals)
    return res

def test(port):
    NUL = "\x00" # Convenience for f-strings

    elm = OBDLink(port)
    diag = UDS(elm)
    elm.connect()
    elm.defaults()
    
    diag.wait_for_tester_present(0x716, timeout=10)
    
    print("Got response from 0x716\n")

    print(f"\n ==== ECU Hardware ====")
    print(f"WERS Part Number: {diag.read_data_by_identifier(0x716, 0xF110).decode('utf-8').rstrip(NUL)}")
    print(f"Core Assembly Part Number: {diag.read_data_by_identifier(0x716, 0xF111).decode('utf-8').rstrip(NUL)}")
    print(f"Delivery Assembly Part Number: {diag.read_data_by_identifier(0x716, 0xF113).decode('utf-8').rstrip(NUL)}") # F111 + SW + Calibrations
    print(f"Serial Number: {diag.read_data_by_identifier(0x716, 0xF18C).decode('utf-8').rstrip(NUL)}")
    print(f"FESN (Ford Electronic Serial Number): {diag.read_data_by_identifier(0x716, 0xF17F).decode('utf-8').rstrip(NUL)}")

    #print()
    # What is NOS? Not parsing this correctly
    #nos_generation_tool_version = bytes(reversed(diag.read_data_by_identifier(0x716, 0xF15F)))
    #print(f"NOS Generation Tool Version: {nos_generation_tool_version[0:9].hex()} {nos_generation_tool_version[9]} {'(Vector)' if nos_generation_tool_version[9] == 8 else '(?)'}")
    #nos_msg_db_version = bytes(reversed(diag.read_data_by_identifier(0x716, 0xF166)))
    #print(f"NOS Message Database Version: {bcd_decode(nos_msg_db_version[0:1], 0)} ({bcd_decode(nos_msg_db_version[1:2], 0)}/{bcd_decode(nos_msg_db_version[2:3], 0)}/{bcd_decode(nos_msg_db_version[3:4], 0)})")


    print(f"\n ==== ECU Software ====")
    vmcu_stgy_version = diag.read_data_by_identifier(0x716, 0xF188).decode('utf-8').rstrip(NUL)
    print(f"VMCU Strategy Part Number: {vmcu_stgy_version}")
    print(f"Embedded Consumer Operating System Part Number: {diag.read_data_by_identifier(0x716, 0x8033).decode('utf-8').rstrip(NUL)}") # Linux squashfs
    print(f"Embedded Consumer Boot Software Part Number: {diag.read_data_by_identifier(0x716, 0x8068).decode('utf-8').rstrip(NUL)}") # Boot.img

    # Split into 24 byte chunks
    apps = diag.read_data_by_identifier(0x716, 0x8060)
    apps = [apps[i:i+24].decode('utf-8').rstrip(NUL) for i in range(0, len(apps), 24)]
    apps_2 = diag.read_data_by_identifier(0x716, 0x8061)
    apps_2 = [apps_2[i:i+24].decode('utf-8').rstrip(NUL) for i in range(0, len(apps_2), 24)]
    apps_3 = diag.read_data_by_identifier(0x716, 0x806A)
    apps_3 = [apps_3[i:i+24].decode('utf-8').rstrip(NUL) for i in range(0, len(apps_3), 24)]
    apps_4 = diag.read_data_by_identifier(0x716, 0x806B)
    apps_4 = [apps_4[i:i+24].decode('utf-8').rstrip(NUL) for i in range(0, len(apps_4), 24)]

    apps = apps + apps_2 + apps_3 + apps_4
    apps = [app for app in apps if app]

    print(f"Embedded Consumer Application Part Numbers: {apps}")
    #for app in apps:
    #    print(f"  - {app}")

    print(f"\n ==== TRON ====")
    print(f"Service Mode Status: {'Enabled' if diag.read_data_by_identifier(0x716, 0xA021)[0] == 0x01 else 'Disabled'}")
    print(f"Gateway Network Protection (GNP) Mode Status: {diag.read_data_by_identifier(0x716, 0xC015)[0]}") # TODO: Lookup enum
    print(f"(Failed) Secure Message Payload: {diag.read_data_by_identifier(0x716, 0xC01D).rstrip(NUL.encode())}")
    print(f"Trip Counter: {diag.read_data_by_identifier(0x716, 0xC01F)[0]}")
    print(f"On Vehicle Telematics Protocol(OVTP) Key Management Negative Response Codes: {diag.read_data_by_identifier(0x716, 0xC020).hex().upper()}") # TODO: Lookup enum
    print(f"Control Module Message Authentication Self Test Response: {diag.read_data_by_identifier(0x716, 0xC022).hex().upper()}")
    print(f"Control Module Message Authentication Failure Monitor Time Window: {int.from_bytes(diag.read_data_by_identifier(0x716, 0xC023), 'big')} seconds")
    print(f"On Vehicle Telematics Protocol Key Management Function Identifiers: {diag.read_data_by_identifier(0x716, 0xC024).hex().upper()}") # TODO: Lookup enum
    print(f"Trusted Realtime Operational Network(TRON) Group Key Slot Counter: {diag.read_data_by_identifier(0x716, 0xC025).hex().upper()}")
    print(f"Message Authentication Self Test Challenge: {diag.read_data_by_identifier(0x716, 0xC026).hex().upper()}")
    print(f"Server Key Injection Status Table: {'Control Module Does Not Have Factory Default Message Authentication Key Configuration' if diag.read_data_by_identifier(0x716, 0xC027)[0] == 1 else 'Control Module Has Factory Default Message Authentication Key Configuration'}")
    print(f"Control Module Message Authentication Failure Threshold: {int.from_bytes(diag.read_data_by_identifier(0x716, 0xC028), 'big')}")
    print(f"Trusted Realtime Operational Network Command Control Counter: {int.from_bytes(diag.read_data_by_identifier(0x716, 0xC02A), 'big')}")
    print(f"Trusted Realtime Operational Network Public Key Hash: {diag.read_data_by_identifier(0x716, 0xC02B).hex().upper()}")
    print(f"Key Injection Status Table Summary State: {diag.read_data_by_identifier(0x716, 0xC02C).hex().upper()}") # TODO: Lookup enum
    print(f"Trusted Realtime Operational Network Configuration Version Counter: {int.from_bytes(diag.read_data_by_identifier(0x716, 0xC02D), 'big')}")
    print(f"Trusted Realtime Operational Network Invalid Authorization Payload: {diag.read_data_by_identifier(0x716, 0xC02E).hex().upper()}") # TODO: Lookup enum
    print(f"Trusted Realtime Operational Network Key Update Status: {diag.read_data_by_identifier(0x716, 0xC033).hex().upper()}") # TODO: Lookup enum

    print(f"\n ==== Provisioning and OTA ====")
    print(f"Provisioning Uniform Resource Locator (URL): {diag.read_data_by_identifier(0x716, 0xD01E).decode('utf-8').rstrip(NUL)}")
    print(f"Authorization State: {diag.read_data_by_identifier(0x716, 0xD021).hex().upper()}") # TODO: Lookup enum
    print(f"Customer Connectivity Settings OnBoard Synchronization Status: {diag.read_data_by_identifier(0x716, 0xD023).hex().upper()}") # TODO: Lookup enum
    print(f"Reason for Most Recent OTA Event Non-Activation: {diag.read_data_by_identifier(0x716, 0xD032)}")
    print(f"Consumer Apps Failure: {diag.read_data_by_identifier(0x716, 0xD033).rstrip(NUL.encode())}")
    print(f"Security Package ID: {diag.read_data_by_identifier(0x716, 0xD03D).decode('utf-8').rstrip(NUL)}")
    print(f"Enabled Debug Tokens: {diag.read_data_by_identifier(0x716, 0xD040).decode('utf-8').rstrip(NUL)}") 
    print(f"Most Recent OTA Event Status: {diag.read_data_by_identifier(0x716, 0xD042)}")
    print(f"2nd Most Recent OTA Event Status: {diag.read_data_by_identifier(0x716, 0xD043)}")
    print(f"3rd Most Recent OTA Event Status: {diag.read_data_by_identifier(0x716, 0xD044)}")
    print(f"4th Most Recent OTA Event Status: {diag.read_data_by_identifier(0x716, 0xD045)}")
    print(f"5th Most Recent OTA Event Status: {diag.read_data_by_identifier(0x716, 0xD046)}")
    print(f"Vehicle Interrogator Log Status: {diag.read_data_by_identifier(0x716, 0xD047)}")
    print(f"OTA ProgrammingSession Entry And A/B Swap Precondition Status: {diag.read_data_by_identifier(0x716, 0xD04F).hex().upper()}") # TODO: Lookup enum

    print(f"\n ==== Miscellaneous Status ====")
    print(f"OBD Voltage: {elm.read_voltage():.2f} V")
    print(f"ECU Voltage: {diag.read_data_by_identifier(0x716, 0xD111)[0] / 10:.2f} V")

    
    print(f"\n ==== DTCs ====")
    dtcs = diag.read_dtcs(0x716)
    if dtcs:
        print(f"Stored DTCs: {dtcs}")
    else:
        print("No stored DTCs")


    # Keep awake indefinitely
    print("\nKeeping the connection alive. Press Ctrl+C to exit.")
    try:
        while True:
            diag.tester_present(0x716)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")

    elm.disconnect()

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
        #interactive(selected_port)
        test(selected_port)
    except (ValueError, IndexError) as e:
        print(f"Error: {e}")