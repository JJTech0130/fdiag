import xml.etree.ElementTree as ET

def parse_mdx(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    data = {"dids": {}, "dtcs": {}}
    for did in root.findall(".//DATA_IDENTIFIERS/DID"):
        number = (did.findtext("NUMBER") or "").strip()
        name = (did.findtext("NAME") or "").strip()
        desc = (did.findtext("DESCRIPTION") or "").strip()
        byte_size = (did.findtext("BYTE_SIZE") or "").strip()
        did_type = (did.findtext("DID_TYPE") or "").strip()
        access = {}
        ap = did.find("ACCESS_PARAMETERS")
        if ap is not None:
            for child in ap:
                access[child.tag] = child.attrib.copy()
        subfields = []
        for sf in did.findall("SUB_FIELD"):
            subfields.append({
                "name": (sf.findtext("NAME") or "").strip(),
                "lsb": (sf.findtext("LEAST_SIG_BIT") or "").strip(),
                "msb": (sf.findtext("MOST_SIG_BIT") or "").strip()
            })
        data["dids"][number] = {
            "number": number, "name": name, "description": desc,
            "byte_size": byte_size, "did_type": did_type, "access": access,
            "subfields": subfields
        }

    for dtc in root.findall(".//DTC"):
        base_num = dtc.findtext("NUMBER", "").replace("0x", "").upper().zfill(4)
        base_desc = dtc.findtext("DESCRIPTION", "").strip()

        for fi in dtc.findall("DTC_FAILURE_INFO"):
            fi_desc = fi.findtext("DESCRIPTION", "").strip()
            if fi_desc == "":
                # fall back to DTC_CONTINUOUS_PARAMETERS / FDC_PASS_FAIL_CRITERIA
                fi_desc = fi.findtext("DTC_CONTINUOUS_PARAMETERS/FDC_PASS_FAIL_CRITERIA", "").strip().replace("\n\n", "  ")
            ftb_elem = fi.find("DTC_FTB")
            if ftb_elem is not None and "FAILURE_REF" in ftb_elem.attrib:
                ftb = ftb_elem.attrib["FAILURE_REF"].replace("ftb_", "").upper().zfill(2)
                full_code = f"{base_num}{ftb}"
            else:
                full_code = base_num

            data["dtcs"][full_code] = {
                "base_code": base_num,
                "ftb": full_code[len(base_num):] if len(full_code) > len(base_num) else None,
                "base_description": base_desc,
                "failure_description": fi_desc
            }
    return data

def list_accessible_dids(parsed_data, session_ref='session_01'):
    out = []
    for num, info in parsed_data["dids"].items():
        access = info.get("access", {})
        for a in access.values():
            if session_ref in a.get("SESSION_REFS","").split():
                out.append(info)
                break
    return out

# def interpret_dtc(parsed_data, code):
#     if isinstance(code, int):
#         code_norm = hex(code).upper().replace('X','x')
#     else:
#         code_norm = str(code).strip().upper()
#         if not code_norm.startswith("0X"):
#             try:
#                 code_norm = hex(int(code)).upper().replace('X','x')
#             except:
#                 pass
#     code_norm = code_norm.replace('0X','0x')
#     dtc = parsed_data["dtcs"].get(code_norm)
#     if not dtc:
#         try:
#             iv = int(code_norm, 16)
#             for k,v in parsed_data["dtcs"].items():
#                 try:
#                     if int(k,16) == iv:
#                         dtc = v; break
#                 except: continue
#         except: pass
#     return dtc
def interpret_dtc(data, code):
    # Strip leading '0x', uppercase, pad
    code = code.replace("0x", "").upper()
    if len(code) == 4:  # base only
        code = code.zfill(4)
    elif len(code) <= 6:  # base + ftb
        code = code[:4].zfill(4) + code[4:].zfill(2)

    return data["dtcs"].get(code)

if __name__ == '__main__':
    import sys, pathlib
    if len(sys.argv) < 2:
        print("Usage: mdx_tools.py <path_to_mdx> [--list-session session_id] [--dtc CODE]")
        sys.exit(1)
    mdx = sys.argv[1]
    parsed = parse_mdx(mdx)
    if '--list-session' in sys.argv:
        idx = sys.argv.index('--list-session')+1
        session = sys.argv[idx] if idx < len(sys.argv) else 'session_01'
        dids = list_accessible_dids(parsed, session)
        for d in dids:
            print(d['number'], d['name'], d['byte_size'])
    if '--dtc' in sys.argv:
        idx = sys.argv.index('--dtc')+1
        code = sys.argv[idx] if idx < len(sys.argv) else None
        dtc = interpret_dtc(parsed, code)
        if dtc:
            print(dtc['number'], dtc['description'])
            for f in dtc['failures']:
                print("- ", f['description'][:200])
        else:
            print("DTC not found:", code)