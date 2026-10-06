def count_ti_atoms(data_path="data"):
    with open(data_path) as f:
        lines = f.readlines()

    atom_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Atoms"):
            atom_start = i + 2  # Skip "Atoms" header and blank/comment line
            break

    if atom_start is None:
        raise ValueError("Atoms section not found.")

    ti_count = 0
    for i in range(atom_start, len(lines)):
        line = lines[i].strip()
        if line == "" or line.startswith("#"):
            continue
        if line.startswith("Velocities"):
            break
        parts = line.split()
        if len(parts) >= 2 and parts[1] == '1':  # Ti has type 1
            ti_count += 1

    return ti_count
