# llm_decision.py
# Robust autonomous decision engine for alloy optimization

import os
import re
import csv
import json
import openai
from elements import ELEMENTS

# ======================================================
# Starting composition
# ======================================================

STARTING_COMPOSITION = {
    "Al": 323,
    "Co": 0,
    "Cu": 323,
    "Cr": 2016,
    "Fe": 2015,
    "Mn": 1210,
    "Ni": 2016,
    "Ti": 161,
}

# ======================================================
# API config
# ======================================================

API_KEY = os.getenv("LLM_API_KEY")
BASE_URL = "https://ai-incubator-api.pnnl.gov"
MODEL = "gpt-5-birthright"

client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)

TOTAL_ATOMS = 8064
MAX_RETRIES = 25

# ======================================================
# Bounds
# ======================================================

BOUNDS = {
    "Fe": (1613, 2822),
    "Cr": (1613, 2822),
    "Ni": (1613, 2822),
    "Mn": (806, 2419),
    "Cu": (0, 564),
    "Al": (0, 1209),
    "Ti": (0, 806),
    "Co": (0, 0),
}

# ======================================================
# Helpers
# ======================================================

def read_history(csv_path):
    history = []
    try:
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            history = list(reader)
    except FileNotFoundError:
        pass
    return history


# ------------------------------------------------------
# FLEXIBLE PARSER (absolute or delta compatible)
# ------------------------------------------------------

def parse_deltas(text, current):

    values = {}

    for el in ELEMENTS:
        pattern = rf"{el}[^-\d+]*([-+]?\d+)"
        m = re.search(pattern, text, re.I)
        if m:
            values[el] = int(m.group(1))

    if not values:
        return {el: 0 for el in ELEMENTS}

    # detect absolute vs delta
    # if any value large → treat as absolute composition
    if any(abs(v) > 300 for v in values.values()):

        deltas = {}
        for el in ELEMENTS:
            new_val = values.get(el, current[el])
            deltas[el] = new_val - current[el]

        return deltas

    # otherwise treat as delta values
    return {el: values.get(el, 0) for el in ELEMENTS}


# ------------------------------------------------------

def valid_bounds(new_counts):
    for el, (lo, hi) in BOUNDS.items():
        if new_counts[el] < lo or new_counts[el] > hi:
            return False
    return True


def feasible_deltas(deltas, current):
    for el, d in deltas.items():
        if d < 0 and abs(d) > current[el]:
            return False
    return True


def delta_limits(iteration, stagnated):

    if iteration <= 20:
        return 5, 25
    elif iteration < 150:
        return 5, 120
    else:
        return 10, 200 if stagnated else 150


def valid_delta_size(deltas, iteration, stagnated):

    lo, hi = delta_limits(iteration, stagnated)

    nonzero = [abs(d) for d in deltas.values() if d != 0]
    if not nonzero:
        return False

    return all(lo <= x <= hi for x in nonzero)


def detect_stagnation(history, window=6):

    if len(history) < window + 1:
        return False

    recent = history[-window:]
    prev = history[-(window + 1)]

    best_nvac = min(float(r["Nvac_avg"]) for r in recent)
    best_strength = max(float(r["Tensile_strength"]) for r in recent)

    return not (
        best_nvac < float(prev["Nvac_avg"])
        or best_strength > float(prev["Tensile_strength"])
    )


# ======================================================
# MAIN DECISION FUNCTION
# ======================================================

def ask_llm(csv_path="trajectory.csv",
            Nvac_avg=None,
            tensile_strength=None,
            total_iterations=150):

    history = read_history(csv_path)
    iteration = len(history) + 1
    stagnated = detect_stagnation(history)

    # ----------------------------------
    # Current composition
    # ----------------------------------

    if history:
        last = history[-1]
        current = {el: int(last[f"{el}_count"]) for el in ELEMENTS}
    else:
        current = STARTING_COMPOSITION.copy()

    lo_d, hi_d = delta_limits(iteration, stagnated)

    # ----------------------------------
    # Prompt
    # ----------------------------------

    prompt = f"""
You are optimizing alloy composition.

Goal:
Minimize vacancies AND maximize tensile strength.

Latest:
Vacancies = {Nvac_avg}
Strength = {tensile_strength} GPa

Current composition:
{current}

Constraints:
- total atoms must stay {TOTAL_ATOMS}
- one element must increase
- one must decrease
- change size between {lo_d} and {hi_d}
- Co must stay zero

Return ONLY JSON with composition values:

{{
"Al": int,
"Co": 0,
"Cu": int,
"Cr": int,
"Fe": int,
"Mn": int,
"Ni": int,
"Ti": int,
"reason": "short explanation"
}}
"""

    # ======================================================
    # LLM LOOP
    # ======================================================

    for attempt in range(MAX_RETRIES):

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
            )

        except Exception as e:
            print("LLM error:", e)
            continue

        text = response.choices[0].message.content.strip()

        # ---------- JSON parse ----------
        try:
            j = json.loads(text)
            deltas = {el: int(j.get(el, 0)) - current[el] for el in ELEMENTS}
        except:
            deltas = parse_deltas(text, current)

        deltas["Co"] = 0

        # ---------- VALIDATION ----------

        if sum(deltas.values()) != 0:
            print("Rejected: sum != 0", deltas)
            continue

        if not feasible_deltas(deltas, current):
            print("Rejected: infeasible removal", deltas)
            continue

        if not valid_delta_size(deltas, iteration, stagnated):
            print("Rejected: delta size invalid", deltas)
            continue

        new_counts = {el: current[el] + deltas[el] for el in ELEMENTS}

        if not valid_bounds(new_counts):
            print("Rejected: bounds violated", new_counts)
            continue

        print("Accepted move:", deltas)
        return deltas, text

    # ======================================================
    # FALLBACK (rare now)
    # ======================================================

    print("⚠ Using fallback move")

    fallback = {el: 0 for el in ELEMENTS}
    fallback["Fe"] = -50
    fallback["Mn"] = +50

    return fallback, "Fallback move used"
