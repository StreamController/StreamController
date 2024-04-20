from fontTools import ttLib
import matplotlib.colors

def font_family_from_path(path: str) -> str:
    """
    source: https://gist.github.com/pklaus/dce37521579513c574d0
    """
    FONT_SPECIFIER_NAME_ID = 4
    FONT_SPECIFIER_FAMILY_ID = 1
    if path in [None, ""]: return ""

    font = ttLib.TTFont(path)
    """Get the short name from the font's names table"""
    name = ""
    family = ""
    for record in font['name'].names:
        if b'\x00' in record.string:
            name_str = record.string.decode('utf-16-be')
        else:   
            name_str = record.string.decode('utf-8')
        if record.nameID == FONT_SPECIFIER_NAME_ID and not name:
            name = name_str
        elif record.nameID == FONT_SPECIFIER_FAMILY_ID and not family: 
            family = name_str
        if name and family: break
    return family

def hex_to_rgba255(color_hex: str) -> list[int]:
    if color_hex in [None, ""]: return None
    rbga = matplotlib.colors.to_rgba(color_hex)
    return [int(x * 255) for x in rbga]