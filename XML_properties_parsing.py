# csi_parser.py
import xml.etree.ElementTree as ET
import pandas as pd
import os

def _get_root_from_source(source):
    """
    Internal helper: Parses XML from either a file path or a raw string.
    """
    # CSI XML namespace
    ns = {'csi': 'http://www.csiamerica.com'}
    
    # Check if source is a file path that exists
    if os.path.isfile(source):
        tree = ET.parse(source)
        root = tree.getroot()
    else:
        # Assume it is a raw XML string
        root = ET.fromstring(source)
        
    return root, ns

def get_sections(source):
    """
    Extracts Steel Section properties from CSI XML.
    
    Args:
        source (str): Filepath to .xml OR raw XML string.
        
    Returns:
        pd.DataFrame: Index = Section Name, Cols = Standard engineering props (h, b, Iy, etc.)
    """
    root, ns = _get_root_from_source(source)
    data = []

    # Iterate through STEEL_I_SECTION (you can add other shapes like STEEL_BOX_SECTION here later)
    for section in root.findall('.//csi:STEEL_I_SECTION', ns):
        props = {}
        try:
            # Basic Geometry
            props['Name'] = section.find('csi:LABEL', ns).text
            props['h'] = float(section.find('csi:D', ns).text)     # Depth
            props['b'] = float(section.find('csi:BF', ns).text)    # Width
            props['tf'] = float(section.find('csi:TF', ns).text)   # Flange Thickness
            props['tw'] = float(section.find('csi:TW', ns).text)   # Web Thickness
            props['A'] = float(section.find('csi:A', ns).text)     # Area
            
            # Inertia (CSI 33 = Major/y-y, 22 = Minor/z-z)
            props['Iy'] = float(section.find('csi:I33', ns).text)
            props['Iz'] = float(section.find('csi:I22', ns).text)
            
            # Plastic Moduli
            props['Wpl_y'] = float(section.find('csi:Z33', ns).text)
            props['Wpl_z'] = float(section.find('csi:Z22', ns).text)
            
            # Elastic Moduli
            props['Wel_y'] = float(section.find('csi:S33POS', ns).text)
            props['Wel_z'] = float(section.find('csi:S22POS', ns).text)
            
            # Torsion / Gyration
            props['It'] = float(section.find('csi:J', ns).text)
            props['iy'] = float(section.find('csi:R33', ns).text)
            props['iz'] = float(section.find('csi:R22', ns).text)

        except AttributeError:
            continue # Skip incomplete sections
            
        data.append(props)

    df = pd.DataFrame(data)
    if not df.empty:
        df.set_index('Name', inplace=True)
        
    return df

def get_materials(source):
    """
    Extracts Material properties from CSI XML.
    
    Args:
        source (str): Filepath to .xml OR raw XML string.
        
    Returns:
        pd.DataFrame: Index = Grade, Cols = E, fy, fu, etc.
    """
    root, ns = _get_root_from_source(source)
    data = []

    for mat in root.findall('.//csi:material', ns):
        props = {}
        props['Grade'] = mat.get('grade')
        props['Type'] = mat.get('type')
        
        # Skip if not Steel or Concrete (can be expanded)
        if props['Type'] not in ['Steel', 'concrete']:
            continue

        try:
            # Common properties
            if mat.find('csi:modulusOfElasticity', ns) is not None:
                props['E'] = float(mat.find('csi:modulusOfElasticity', ns).text)
            
            if mat.find('csi:massDensity', ns) is not None:
                props['rho'] = float(mat.find('csi:massDensity', ns).text)

            # Steel Specific
            if props['Type'] == 'Steel':
                props['fy'] = float(mat.find('csi:minimumYieldStress', ns).text)
                props['fu'] = float(mat.find('csi:minimumTensileStress', ns).text)
            
            # Concrete Specific
            elif props['Type'] == 'concrete':
                props['fck'] = float(mat.find('csi:compressiveStrength', ns).text)
                
        except AttributeError:
            continue
            
        data.append(props)

    df = pd.DataFrame(data)
    if not df.empty:
        df.set_index('Grade', inplace=True)
        
    return df