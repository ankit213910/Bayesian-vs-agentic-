import subprocess
import re


def get_nvac(dump_first="dump.first.txt", all_out="all.out",
             rcell=2.8, axis_exec="axis"):

    cmd = [axis_exec, "-defect", dump_first,
           "--fin", all_out, "--rcell", str(rcell)]

    try:
        proc = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        output = proc.stdout + proc.stderr

    except subprocess.CalledProcessError as e:
        output = (e.stdout or "") + (e.stderr or "")
    except FileNotFoundError:
        print("AXIS not found on PATH")
        return None

    m = re.search(r"\bNvac\s*=\s*(\d+)", output)
    if m:
        return int(m.group(1))

    print("WARNING: Could not parse Nvac from AXIS output")
    return None

