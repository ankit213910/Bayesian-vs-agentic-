import re

def get_max_stress(file_path="load.1"):
    with open(file_path) as f:
        lines = f.readlines()

    stresses = []
    for line in lines:
        if re.match(r"^\s*[\d\.\-eE]+\s+[\d\.\-eE]+\s+[\d\.\-eE]+\s+", line):
            try:
                parts = list(map(float, line.split()))
                stress = parts[5]  # already in GPa
                stresses.append(abs(stress))
            except:
                continue

    return max(stresses) if stresses else None

