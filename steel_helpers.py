from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Iterable

from sections_db import SectionDB, SectionHit


# -----------------------
# Small utility functions
# -----------------------

def mm4_to_m4(x_mm4: float) -> float:
    return x_mm4 * 1e-12

def mm3_to_m3(x_mm3: float) -> float:
    return x_mm3 * 1e-9

def mm2_to_m2(x_mm2: float) -> float:
    return x_mm2 * 1e-6

def Nmm_to_kNm(x_Nmm: float) -> float:
    return x_Nmm / 1e6

def kNm_to_Nmm(x_kNm: float) -> float:
    return x_kNm * 1e6

def MPa_to_N_per_mm2(x_MPa: float) -> float:
    return x_MPa  # 1 MPa = 1 N/mm2


@dataclass
class SectionProps:
    label: str
    library: str
    type: Optional[str]
    designation: Optional[str]

    # common props (mm-basis)
    A: float          # mm2
    Iy: float         # mm4 (assumed I33)
    Iz: float         # mm4 (assumed I22)
    Wy_el: Optional[float]  # mm3 (often Z or S depending on library)
    Wz_el: Optional[float]  # mm3
    Zpl_y: Optional[float]  # mm3
    Zpl_z: Optional[float]  # mm3
    d: Optional[float]      # mm
    bf: Optional[float]     # mm
    tf: Optional[float]     # mm
    tw: Optional[float]     # mm


def get_section_props(
    db: SectionDB,
    label: str,
    prefer: Optional[Iterable[str]] = None,
    Iy_key: str = "I33",
    Iz_key: str = "I22",
) -> SectionProps:
    """
    Pull a consistent set of properties from the section library.

    Notes:
    - Many CSI libraries use I33/I22.
    - Elastic modulus may be stored as Z33/Z22 or S33POS/S33NEG etc.
    - Plastic modulus may be Z33/Z22 in some libraries.
    """

    hit = db.get_with_source(label, prefer=prefer)
    if hit is None:
        raise KeyError(f"Section not found: {label}")

    sec = hit.section
    p = sec.get("properties", {})

    def g(key: str, default: Any = None):
        return p.get(key, default)

    # Try a few common keys for section moduli
    # Elastic:
    Wy_el = g("Z33") or g("S33POS") or g("S33NEG")
    Wz_el = g("Z22") or g("S22POS") or g("S22NEG")
    # Plastic (sometimes also Z33/Z22, depends on library)
    Zpl_y = g("Z33")  # fallback
    Zpl_z = g("Z22")  # fallback

    return SectionProps(
        label=label,
        library=hit.library,
        type=sec.get("type"),
        designation=sec.get("designation"),

        A=float(g("A")),
        Iy=float(g(Iy_key)),
        Iz=float(g(Iz_key)),
        Wy_el=float(Wy_el) if Wy_el is not None else None,
        Wz_el=float(Wz_el) if Wz_el is not None else None,
        Zpl_y=float(Zpl_y) if Zpl_y is not None else None,
        Zpl_z=float(Zpl_z) if Zpl_z is not None else None,
        d=g("D"),
        bf=g("BF"),
        tf=g("TF"),
        tw=g("TW"),
    )


# -----------------------
# 1) Beam bending helpers
# -----------------------

def M_yield_kNm(W_el_mm3: float, fy_MPa: float) -> float:
    """
    Simple yield moment: My = W_el * fy.
    Units: W_el in mm^3, fy in MPa (=N/mm^2). Result in kNm.
    """
    My_Nmm = W_el_mm3 * MPa_to_N_per_mm2(fy_MPa)
    return Nmm_to_kNm(My_Nmm)

def M_plastic_kNm(Z_pl_mm3: float, fy_MPa: float) -> float:
    """
    Simple plastic moment: Mpl = Zpl * fy.
    (No partial factors, no LTB reduction, just the core strength.)
    """
    Mpl_Nmm = Z_pl_mm3 * MPa_to_N_per_mm2(fy_MPa)
    return Nmm_to_kNm(Mpl_Nmm)

def section_class_hint(b_over_t: float) -> str:
    """
    Not Eurocode classification (needs c/t limits by element),
    but useful as a quick 'is this slender?' sanity check.
    """
    if b_over_t < 8:
        return "stocky-ish"
    if b_over_t < 12:
        return "normal"
    return "slender-ish"


# -------------------------
# 2) Column buckling helpers
# -------------------------

def radius_of_gyration_mm(I_mm4: float, A_mm2: float) -> float:
    return math.sqrt(I_mm4 / A_mm2)

def slenderness_lambda(L_eff_mm: float, r_mm: float) -> float:
    return L_eff_mm / r_mm

def euler_Ncr_kN(E_MPa: float, I_mm4: float, L_eff_mm: float) -> float:
    """
    Euler critical load: Ncr = pi^2 * E * I / L^2
    E in MPa (=N/mm^2), I in mm^4, L in mm -> N, then convert to kN
    """
    Ncr_N = (math.pi**2) * MPa_to_N_per_mm2(E_MPa) * I_mm4 / (L_eff_mm**2)
    return Ncr_N / 1000.0


# ---------------------------------
# 3) Connection / bolt group helpers
# ---------------------------------

def bolt_shear_capacity_kN(
    fub_MPa: float,
    As_mm2: float,
    gamma_M2: float = 1.25,
    alpha_v: float = 0.6,
    n_shear_planes: int = 1,
) -> float:
    """
    Very simplified EC3-ish bolt shear resistance form:
      Fv,Rd = alpha_v * fub * As / gamma_M2  (per shear plane)

    Returns kN.

    You MUST adapt alpha_v / As for your bolt type:
    - As = tensile stress area for threads in shear plane
    - or use shank area if threads are excluded
    """
    Fv_N = n_shear_planes * alpha_v * MPa_to_N_per_mm2(fub_MPa) * As_mm2 / gamma_M2
    return Fv_N / 1000.0

def bolt_group_shear_kN_per_bolt(V_total_kN: float, n_bolts: int) -> float:
    return V_total_kN / n_bolts

def bolt_group_moment_shear_kN(
    M_kNm: float,
    bolt_coords_mm: list[tuple[float, float]],
) -> list[float]:
    """
    Simplified elastic bolt group moment distribution about group centroid:
    Shear force in each bolt proportional to radius r_i:
      F_i = M * r_i / sum(r_j^2)

    Inputs:
      - M_kNm about z (out of plane), in kNm
      - bolt_coords_mm = [(x,y), ...] in mm in any reference frame

    Output:
      - list of bolt forces in kN due to moment only
    """
    if len(bolt_coords_mm) == 0:
        return []

    # centroid
    xs = [c[0] for c in bolt_coords_mm]
    ys = [c[1] for c in bolt_coords_mm]
    x0 = sum(xs) / len(xs)
    y0 = sum(ys) / len(ys)

    rs2 = []
    rs = []
    for x, y in bolt_coords_mm:
        dx = x - x0
        dy = y - y0
        r2 = dx*dx + dy*dy
        rs2.append(r2)
        rs.append(math.sqrt(r2))

    denom = sum(rs2)
    if denom == 0:
        return [0.0 for _ in bolt_coords_mm]

    M_Nmm = kNm_to_Nmm(M_kNm)
    # F_i in N: M * r / sum(r^2)
    forces_kN = [(M_Nmm * r / denom) / 1000.0 for r in rs]
    return forces_kN
