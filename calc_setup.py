"""
calc_setup.py  –  Common initialisation for hand-calculation notebooks.

Usage (single cell at the top of any notebook):
    from calc_setup import *

This re-exports everything a calc sheet needs:
  • forallpeople unit symbols  (mm, kN, MPa, m, kg …)
  • math helpers               (pi, sqrt, tan, radians, exp)
  • handcalcs render magic     (%%render already registered)
  • handcalc decorator
  • structuralcodes helpers    (set_design_code, create_concrete)
  • sections database          (db, prefer, SectionDB, default_db_path)

To use a different design code in one notebook, call after the import:
    set_design_code('en_1992_1_1_2023')
"""

# ── Path setup ─────────────────────────────────────────────────────────────────
import sys, os
_CALC_DIR = os.path.dirname(os.path.abspath(__file__))
if _CALC_DIR not in sys.path:
    sys.path.insert(0, _CALC_DIR)

# ── Imports ────────────────────────────────────────────────────────────────────
import handcalcs.render          # registers the %%render / %%render params magic
from handcalcs import render
import handcalcs
from handcalcs.decorator import handcalc

import forallpeople as si

from structuralcodes import set_design_code
from structuralcodes.materials.concrete import create_concrete

from math import pi, sqrt, tan, radians, exp

from sections_db import SectionDB

# ── 1. Units ───────────────────────────────────────────────────────────────────
# top_level=True injects unit names (mm, kN, MPa …) into this module's
# namespace so they are re-exported when you do `from calc_setup import *`.
si.environment('structural', top_level=True)

# ── 2. Design code (default: EC2 2004) ────────────────────────────────────────
set_design_code('ec2_2004')

# ── 3. handcalcs display options ──────────────────────────────────────────────
handcalcs.set_option("display_precision", 3)
handcalcs.set_option("underscore_subscripts", True)
handcalcs.set_option("custom_symbols", {
    "Lambda_": r"\Lambda",   # uppercase Λ
    "lambda_": r"\lambda",   # lowercase λ
    "V_dot":   r"\dot{V}",
    "N_star":  r"N^{*}",
})

# ── 4. Section database ────────────────────────────────────────────────────────
_DB_JSON = r"C:\Users\vance\Documents\Scripts\Hand_calculations\Property Libraries\json_out\_all_libraries_combined.json"
db = SectionDB(_DB_JSON).load()
prefer = ["BSShapes2006", "ArcelorMittal_British", "ArcelorMittal_Europe"]

print("Calc environment ready.")
