from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import pandas as pd  # optional
except Exception:  # pandas not installed or not needed
    pd = None


@dataclass
class SectionHit:
    library: str
    label: str
    section: Dict[str, Any]


class SectionDB:
    """
    Loads a combined JSON created by your converter:
      Property Libraries/json_out/_all_libraries_combined.json

    Core methods:
      db.get(label)                               -> first match found
      db.get(label, prefer=[...])                 -> use preferred libraries first
      db.find_all(label)                          -> all matches
      db.search("UKB1016", limit=20)              -> find labels containing text

    Convenience:
      db.prop(sec, "A")
      db.props(sec, ["A","I33","I22"])
      db.to_dataframe(labels=[...], keys=[...])   -> pandas DataFrame (optional)
    """

    def __init__(self, combined_json_path: str | Path):
        self.path = Path(combined_json_path).expanduser().resolve()
        self._data: Dict[str, Any] = {}
        self._libs: Dict[str, Dict[str, Any]] = {}

    def load(self) -> "SectionDB":
        if not self.path.exists():
            raise FileNotFoundError(f"Combined JSON not found: {self.path}")

        with self.path.open("r", encoding="utf-8") as f:
            self._data = json.load(f)

        self._libs = self._data.get("libraries", {})
        if not self._libs:
            raise ValueError("No libraries found in combined JSON. Check file content/format.")

        return self

    @property
    def libraries(self) -> List[str]:
        return sorted(self._libs.keys())

    def _iter_libraries_in_order(self, prefer: Optional[Iterable[str]] = None):
        """
        Yield (lib_name, lib_db) in an order:
        - preferred libraries first (if they exist)
        - then the rest alphabetical
        """
        if not self._libs:
            raise RuntimeError("DB not loaded. Call .load() first.")

        prefer_list = list(prefer) if prefer else []
        yielded = set()

        for lib_name in prefer_list:
            if lib_name in self._libs and lib_name not in yielded:
                yielded.add(lib_name)
                yield lib_name, self._libs[lib_name]

        for lib_name in sorted(self._libs.keys()):
            if lib_name not in yielded:
                yield lib_name, self._libs[lib_name]

    def get(
        self,
        label: str,
        library: Optional[str] = None,
        prefer: Optional[Iterable[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get one section record.
        - If library is provided, only search that library.
        - Else, search prefer-order if provided, otherwise first hit in default order.
        """
        if not self._libs:
            raise RuntimeError("DB not loaded. Call .load() first.")

        if library:
            lib = self._libs.get(library)
            if not lib:
                raise KeyError(f"Library not found: {library}")
            return lib.get("sections_by_label", {}).get(label)

        for _, lib_db in self._iter_libraries_in_order(prefer):
            sec = lib_db.get("sections_by_label", {}).get(label)
            if sec:
                return sec
        return None

    def get_with_source(
        self,
        label: str,
        prefer: Optional[Iterable[str]] = None,
    ) -> Optional[SectionHit]:
        """
        Same as get(), but returns which library it came from.
        """
        if not self._libs:
            raise RuntimeError("DB not loaded. Call .load() first.")

        for lib_name, lib_db in self._iter_libraries_in_order(prefer):
            sec = lib_db.get("sections_by_label", {}).get(label)
            if sec:
                return SectionHit(library=lib_name, label=label, section=sec)
        return None

    def find_all(self, label: str) -> List[SectionHit]:
        """
        Return all matches across libraries.
        """
        if not self._libs:
            raise RuntimeError("DB not loaded. Call .load() first.")

        hits: List[SectionHit] = []
        for lib_name, lib_db in self._libs.items():
            sec = lib_db.get("sections_by_label", {}).get(label)
            if sec:
                hits.append(SectionHit(library=lib_name, label=label, section=sec))
        return hits

    def search(self, text: str, limit: int = 50, prefer: Optional[Iterable[str]] = None) -> List[Tuple[str, str]]:
        """
        Search labels containing 'text' (case-insensitive).
        Returns list of (library, label), ordered by library preference if provided.
        """
        if not self._libs:
            raise RuntimeError("DB not loaded. Call .load() first.")

        t = text.lower()
        results: List[Tuple[str, str]] = []
        for lib_name, lib_db in self._iter_libraries_in_order(prefer):
            for label in lib_db.get("sections_by_label", {}).keys():
                if t in label.lower():
                    results.append((lib_name, label))
                    if len(results) >= limit:
                        return results
        return results

    # Put this near the top of the class (or right above prop/props)
    ALIASES = {
        "I33": "Iy",
        "I22": "Iz",
        "Z33": "Zy",
        "Z22": "Zz",
        "R33": "ry",
        "R22": "rz",
        "S33POS": "Wy_el_pos",
        "S33NEG": "Wy_el_neg",
        "S22POS": "Wz_el_pos",
        "S22NEG": "Wz_el_neg",
    }

    @staticmethod
    def prop(section: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Get one property from section record, with alias fallback.
        db.prop(sec, "Iy")
        db.prop(sec, "I33")  # will return Iy if I33 doesn't exist
        """
        if not section:
            return default

        props = section.get("properties", {})

        if key in props:
            return props[key]

        key2 = SectionDB.ALIASES.get(key)
        if key2 and key2 in props:
            return props[key2]

        return default

    @staticmethod
    def props(section: Dict[str, Any], keys: Iterable[str], default: Any = None) -> Dict[str, Any]:
        """
        Get multiple properties using prop(), so aliases work everywhere (including to_dataframe).
        db.props(sec, ["A","I33","I22"])
        """
        if not section:
            return {k: default for k in keys}

        return {k: SectionDB.prop(section, k, default) for k in keys}


    def units_note(self) -> str:
        """
        Returns the unit note from one library meta.
        """
        if not self._libs:
            raise RuntimeError("DB not loaded. Call .load() first.")
        any_lib = next(iter(self._libs.values()))
        return any_lib.get("meta", {}).get("note", "No unit note found.")

    def to_dataframe(
        self,
        labels: Optional[Iterable[str]] = None,
        keys: Optional[Iterable[str]] = None,
        prefer: Optional[Iterable[str]] = None,
    ):
        """
        Build a pandas DataFrame for quick tables.

        labels:
          - None -> uses labels from search results is not available; you should pass labels.
          - Iterable of labels you want.

        keys:
          - which property keys to include as columns (e.g. ["A","D","BF","TF","TW","I33","I22"])

        prefer:
          - library preference order for resolving duplicates
        """
        if pd is None:
            raise RuntimeError("pandas is not installed in this environment. Install pandas or don't use to_dataframe().")

        if labels is None:
            raise ValueError("labels must be provided (e.g. from db.search(...))")

        keys = list(keys) if keys else ["A", "D", "BF", "TF", "TW", "I33", "I22", "J"]

        rows = []
        for label in labels:
            hit = self.get_with_source(label, prefer=prefer)
            if not hit:
                rows.append({"library": None, "label": label, **{k: None for k in keys}})
                continue

            sec = hit.section
            row = {
                "library": hit.library,
                "label": hit.label,
                "type": sec.get("type"),
                "designation": sec.get("designation"),
            }
            row.update(self.props(sec, keys))
            rows.append(row)

        return pd.DataFrame(rows)


def default_db_path() -> Path:
    """
    Path to the section database, relative to this file.
    Resolves to: <repo>/Property Libraries/json_out/_all_libraries_combined.json
    Works cross-platform (Mac, Windows) as long as the repo structure is intact.
    """
    return (
        Path(__file__).parent
        / "Property Libraries"
        / "json_out"
        / "_all_libraries_combined.json"
    )
