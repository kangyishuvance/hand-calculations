# Hand Calculations Repository

Jupyter Notebook-based structural engineering calculation sheets. Uses `handcalcs` to render Python as LaTeX equations for professional PDF reports. Follows Eurocodes (EC2, EC3, EC7).

## Project Structure

```
calc_setup.py          # Bootstrap module — all notebooks do `from calc_setup import *`
steel_helpers.py       # Steel design utilities (conversions, buckling, bolt calcs)
sections_db.py         # Section database (SectionDB class, loads JSON master DB)
XML_properties_parsing.py  # Parse CSI/ETABS XML into DataFrames
convert_notebooks_to_pdf.py  # Batch notebook → PDF conversion
Property Libraries/    # 37 section libraries (XML + preprocessed JSON)
  json_out/_all_libraries_combined.json  # Master DB loaded by SectionDB
exports/               # Generated PDF/HTML reports
img/                   # Reference images used in notebooks
scripts/               # export_report.sh (nbconvert → Chrome → PDF)
```

## Key Libraries

| Library | Purpose |
|---------|---------|
| `handcalcs` | Renders Python as LaTeX equations (`%%render` magic) |
| `forallpeople` | SI unit awareness (`mm`, `kN`, `MPa`, etc.) |
| `structuralcodes` | EC2/EC3/EC7 design code implementations |
| `pandas` | Section property tables |
| `openpyxl` | Read load combination Excel files |
| `nbconvert` | Export notebooks to HTML/PDF |

## Notebook Pattern

Every notebook follows this structure:
1. `from calc_setup import *` (optionally followed by `set_design_code()`)
2. Variable definitions and helper functions
3. `%%render` cells for typeset calculations
4. Results and code-check outputs

## Running / Exporting

```bash
# Export a single notebook to PDF
make report NOTEBOOK=Steel_beam_Calculator.ipynb

# Custom output directory and name
make report NOTEBOOK=X.ipynb OUTDIR=./exports NAME=my_report

# Show all make targets
make help
```

The export pipeline: `jupyter nbconvert` → HTML (no input cells) → Chrome/Chromium headless → PDF

## Section Database

```python
db = SectionDB(default_db_path()).load()

sec = db.get("UKB1016X305X487", prefer=prefer)          # Preferred library order
hit = db.get_with_source(label, prefer=prefer)           # Returns (library, label, section)
results = db.search("UKB1016", limit=50)                 # Substring search
df = db.to_dataframe(labels=[...], keys=["A","Iy","Iz"]) # Pandas table
```

- All section properties stored in **mm basis** (mm, mm², mm³, mm⁴)
- Property key aliases: `I33` ↔ `Iy`, `I22` ↔ `Iz`, `Z33` ↔ `Zy`
- Preferred library order: `["BSShapes2006", "ArcelorMittal_British", "ArcelorMittal_Europe"]`

## Units Convention

Use `forallpeople` units throughout:
```python
L   = 5000 * mm     # or 5 * m
fy  = 355 * MPa
P   = 150 * kN
```

## Variable Naming Conventions

- Units explicit in name: `tf_mm`, `fy_MPa`, `I_mm4`, `W_el_mm3`, `L_eff_mm`
- Greek letters: `lambda_` (slenderness), `phi_c` (capacity reduction), `alpha_lt` (LTB factor)
- Axes: `Iy`/`I33` = major axis, `Iz`/`I22` = minor axis
- Section geometry: `bf` (flange width), `tf` (flange thickness), `tw` (web thickness), `d`/`D` (depth)

## Design Codes

```python
set_design_code('ec2_2004')           # Concrete (default)
set_design_code('en_1992_1_1_2023')   # Concrete (newer)
conc = create_concrete(fck=30 * MPa)
```

EC3 (steel) and EC7 (foundations/bearing capacity) are also used.
