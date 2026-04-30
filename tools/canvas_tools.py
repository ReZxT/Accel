_COLOR_MAP = {
    "red": "red", "blue": "blue", "green": "green", "yellow": "yellow",
    "orange": "orange", "purple": "violet", "violet": "violet", "grey": "grey",
    "gray": "grey", "black": "black", "white": "white", "light-blue": "light-blue",
    "cyan": "light-blue", "teal": "green", "pink": "red",
}
_SIZE_MAP = {"small": "s", "medium": "m", "large": "l", "xlarge": "xl", "extra-large": "xl"}
_GEO_MAP = {
    "oval": "oval", "rect": "rectangle", "box": "rectangle",
    "square": "rectangle", "hex": "hexagon", "rhombus": "rhombus",
}
_VALID_GEOS = {
    "cloud", "rectangle", "ellipse", "triangle", "diamond", "pentagon", "hexagon",
    "octagon", "star", "rhombus", "rhombus-2", "oval", "trapezoid",
    "arrow-right", "arrow-left", "arrow-up", "arrow-down", "x-box", "check-box", "heart",
}
# Map non-tldraw type names → (tldraw_type, geo_subtype)
_VALID_TYPES = {"geo", "text", "note", "arrow"}

def _normalise(shape: dict) -> dict:
    s = dict(shape)
    # Reject invalid types outright — model must use geo/text/note/arrow
    if s.get("type", "geo") not in _VALID_TYPES:
        return None
    # geo: map aliases and validate; guard against dict values
    if s.get("type") == "geo":
        geo = s.get("geo", "rectangle")
        if isinstance(geo, dict) or not isinstance(geo, str):
            return None
        geo = _GEO_MAP.get(geo, geo)
        if geo not in _VALID_GEOS:
            return None
        s["geo"] = geo
    # color
    color = s.get("color", "")
    if not isinstance(color, str) or color.startswith("#") or color not in _COLOR_MAP:
        s["color"] = _COLOR_MAP.get(color, "blue")
    else:
        s["color"] = _COLOR_MAP[color]
    # size
    size = s.get("size", "m")
    s["size"] = _SIZE_MAP.get(size, size if size in ("s","m","l","xl") else "m")
    # fill
    fill = s.get("fill")
    _valid_fills = {"none", "semi", "solid", "pattern", "fill"}
    if fill is True or fill == "solid":
        s["fill"] = "solid"
    elif fill in _valid_fills:
        s["fill"] = fill
    else:
        s["fill"] = "none"
    return s

def _cmd(command: str, data: dict, summary: str) -> dict:
    return {"__type": "canvas_command", "command": command, "data": data, "summary": summary}


async def canvas_draw(shapes=None, **kwargs) -> dict:
    """Draw shapes on the Architecture session canvas.

    VALID TYPES: "geo" | "note" | "text" | "arrow"  — nothing else is accepted.
    VALID GEO SUBTYPES: "rectangle"|"ellipse"|"triangle"|"diamond"|"cloud"|"pentagon"|"hexagon"|"octagon"|"star"|"oval"|"trapezoid"|"heart"|"rhombus"|"x-box"|"check-box"
    NO "circle" — use geo="ellipse" with equal w and h (e.g. w=150, h=150) for a circle.

    Each shape dict:
      type (required): one of the valid types above
      text (str): label or content
      x, y (int): canvas position (default 100,100; stack with ~150px gaps)
      color: "blue"|"red"|"green"|"yellow"|"orange"|"violet"|"grey"|"black"|"white"|"light-blue"
      --- geo only ---
      geo (required for type=geo): one of the valid geo subtypes above
      w, h (int): width and height in px (default 200×80)
      fill: "none"|"solid"|"semi"|"pattern"
      --- text/note ---
      size: "s"|"m"|"l"|"xl"

    Use notes for ideas/concepts, geo for diagrams, text for labels.
    Lay out left-to-right for sequences, top-to-bottom for hierarchies.
    """
    import json
    # Auto-wrap if model passed shape fields directly as kwargs instead of shapes=[...]
    if shapes is None and kwargs:
        shapes = [kwargs]
    elif isinstance(shapes, dict):
        shapes = [shapes]
    if isinstance(shapes, str):
        try:
            shapes = json.loads(shapes)
        except json.JSONDecodeError as e:
            return {"__type": "error", "text": f"Invalid shapes JSON: {e}"}
    if not shapes:
        return {"__type": "error", "text": "No shapes provided."}
    valid = []
    errors = []
    for s in shapes:
        n = _normalise(s)
        if n is None:
            t = s.get("type","?"); g = s.get("geo","")
            errors.append(f"invalid shape (type={t!r}, geo={g!r})")
        else:
            valid.append(n)
    if not valid:
        detail = "; ".join(errors)
        return {"__type": "error", "text": f"No valid shapes: {detail}. Use type geo/text/note/arrow; for circles use geo=ellipse."}
    shapes = valid
    summary = f"Drew {len(shapes)} shape(s): " + ", ".join(
        f"{s.get('type','?')}({s.get('text','')[:20]})" for s in shapes[:5]
    )
    return _cmd("tldraw:create_shapes", {"shapes": shapes}, summary)


async def canvas_clear() -> dict:
    """Clear everything from the canvas."""
    return _cmd("tldraw:clear", {}, "Canvas cleared.")


async def canvas_get_state() -> str:
    """Get the current contents of the canvas as a JSON description of all shapes. Use this before drawing to understand what's already there, or to read text the user drew."""
    # State is read by the UI and returned via the /canvas/state endpoint
    # This tool signals the UI to fetch and return state — the SSE mechanism handles the roundtrip
    return "Use screenshot_url('http://localhost/#architecture') to see the canvas visually. The canvas panel opens automatically for that session."
