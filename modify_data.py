import random
from elements import ELEMENTS, TYPE_MAP


def change_composition(data_path="data", deltas=None):
    if deltas is None:
        return

    with open(data_path) as f:
        lines = f.readlines()

    atom_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Atoms"):
            atom_start = i + 2
            break
    if atom_start is None:
        raise ValueError("Atoms section not found in data file")

    atom_lines = lines[atom_start:]

    atom_indices = {el: [] for el in ELEMENTS}

    # -----------------------------------
    # identify atoms by element
    # -----------------------------------
    for i, line in enumerate(atom_lines):
        parts = line.split()
        if len(parts) >= 2:
            for el, code in TYPE_MAP.items():
                if parts[1] == code:
                    atom_indices[el].append(i)

    if sum(deltas.values()) != 0:
        raise ValueError("Deltas must sum to zero")

    # -----------------------------------
    # SAFETY CHECK — clamp impossible removals
    # -----------------------------------
    for el, d in deltas.items():
        if d < 0:
            available = len(atom_indices[el])
            if -d > available:
                print(f"[WARN] Requested removal of {-d} {el} but only {available} exist. Clamping.")
                deltas[el] = -available

    # -----------------------------------
    # atoms to convert (removals)
    # -----------------------------------
    to_convert = []
    for el, d in deltas.items():
        if d < 0:
            remove_n = min(-d, len(atom_indices[el]))
            chosen = random.sample(atom_indices[el], remove_n)
            to_convert.extend((idx, el) for idx in chosen)

    # -----------------------------------
    # targets to assign (additions)
    # -----------------------------------
    to_assign = []
    for el, d in deltas.items():
        if d > 0:
            to_assign.extend([el] * d)

    random.shuffle(to_assign)

    # -----------------------------------
    # perform conversion
    # -----------------------------------
    for (idx, _), new_el in zip(to_convert, to_assign):
        parts = atom_lines[idx].split()
        parts[1] = TYPE_MAP[new_el]
        atom_lines[idx] = " ".join(parts) + "\n"

    lines[atom_start:] = atom_lines

    with open(data_path, "w") as f:
        f.writelines(lines)


def count_atom_types(data_path="data"):
    from elements import ELEMENTS, TYPE_MAP

    counts = {el: 0 for el in ELEMENTS}

    with open(data_path) as f:
        lines = f.readlines()

    atom_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Atoms"):
            atom_start = i + 2
            break

    for line in lines[atom_start:]:
        parts = line.split()
        if len(parts) >= 2:
            for el, code in TYPE_MAP.items():
                if parts[1] == code:
                    counts[el] += 1

    return counts
