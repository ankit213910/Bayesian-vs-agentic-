import csv
import os
import subprocess
import shutil

from elements import ELEMENTS
from modify_data import change_composition, count_atom_types
from parse_axis import get_nvac
from parse_log import get_max_stress
from llm_decision import ask_llm

NUM_ITER = 150
trajectory_file = "trajectory.csv"

PKA_INPUTS = [
    "in.TiAlV",
    "in.TiAlV2",
    "in.TiAlV3",
]

TENSION_INPUT = "in.tension"

# ======================================================
# Create CSV
# ======================================================

if not os.path.exists(trajectory_file):
    with open(trajectory_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["iteration"]
            + [f"{e}_count" for e in ELEMENTS]
            + ["Nvac_1", "Nvac_2", "Nvac_3", "Nvac_avg"]
            + ["Tensile_strength"]
            + ["Deltas", "LLM_Message"]
        )

# ======================================================
# Main loop
# ======================================================

for i in range(NUM_ITER):

    print(f"\n===== ITERATION {i+1} =====")

    nvac_list = []

    # ---------------------------------------------
    # Run 3 PKA simulations
    # ---------------------------------------------
    for run_id, input_file in enumerate(PKA_INPUTS, start=1):

        print(f"\n--- Running PKA {run_id}: {input_file} ---")

        subprocess.run(
            ["mpirun", "-np", "24", "lmp_rocky9", "-in", input_file],
            check=True
        )

        shutil.copy("proj.out", f"proj_iter_{i+1:02d}_pka{run_id}.out")
        shutil.copy("dump.first.txt", f"dump_first_iter_{i+1:02d}_pka{run_id}.txt")
        shutil.copy("all.out", f"all_out_iter_{i+1:02d}_pka{run_id}.out")

        nvac = get_nvac()
        nvac_list.append(nvac)

        print(f"PKA {run_id} → Nvac = {nvac}")

    nvac_avg = sum(nvac_list) / len(nvac_list)
    print(f"\nAverage Nvac = {nvac_avg:.2f}")

    # ---------------------------------------------
    # Run tensile simulation
    # ---------------------------------------------
    print("\n--- Running tensile simulation ---")

    subprocess.run(
        ["mpirun", "-np", "24", "lmp_rocky9", "-in", TENSION_INPUT],
        check=True
    )

    tensile_strength = get_max_stress("load.1")
    print(f"Tensile strength = {tensile_strength:.2f} GPa")

    shutil.copy("load.1", f"load_iter_{i+1:02d}.1")

    # ---------------------------------------------
    # Composition count
    # ---------------------------------------------
    counts = count_atom_types("data")

    # ---------------------------------------------
    # LLM decision
    # ---------------------------------------------
    deltas, llm_msg = ask_llm(
        csv_path=trajectory_file,
        Nvac_avg=nvac_avg,
        tensile_strength=tensile_strength,
        total_iterations=NUM_ITER
    )

    # ---------------------------------------------
    # Write CSV
    # ---------------------------------------------
    with open(trajectory_file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [i + 1]
            + [counts[e] for e in ELEMENTS]
            + nvac_list
            + [nvac_avg]
            + [tensile_strength]
            + [str(deltas), llm_msg]
        )

    # ---------------------------------------------
    # Apply composition update
    # ---------------------------------------------
    change_composition("data", deltas)

