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


async def canvas_screenshot() -> dict:
    """Capture the current canvas as an image. Use this to visually inspect what's drawn."""
    import httpx, base64
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8100/canvas/png", timeout=10)
            if r.status_code == 204:
                return {"__type": "error", "text": "Canvas is empty — nothing to screenshot yet."}
            r.raise_for_status()
    except Exception as e:
        return {"__type": "error", "text": f"Could not fetch canvas image: {e}"}
    b64 = base64.b64encode(r.content).decode()
    return {"__type": "image", "base64": b64, "mime_type": "image/png"}


async def canvas_clear() -> dict:
    """Clear everything from the canvas."""
    return _cmd("tldraw:clear", {}, "Canvas cleared.")


async def canvas_get_state() -> str:
    """Get the current contents of the canvas as a readable list of shapes. Use this before drawing to understand what's already there."""
    import httpx, json
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("http://localhost:8100/canvas/state", timeout=5)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Could not read canvas state: {e}"

    store = data.get("document", {}).get("store", {})
    shapes = [v for v in store.values() if v.get("typeName") == "shape"]
    if not shapes:
        return "Canvas is empty."

    lines = [f"{len(shapes)} shape(s) on canvas:"]
    for s in shapes:
        t = s.get("type", "?")
        x, y = round(s.get("x", 0)), round(s.get("y", 0))
        p = s.get("props", {})
        if t == "geo":
            lines.append(f"  geo({p.get('geo','?')}) at ({x},{y}) {round(p.get('w',0))}×{round(p.get('h',0))} color={p.get('color')} fill={p.get('fill')} text={p.get('text','')!r}")
        elif t == "text":
            lines.append(f"  text at ({x},{y}) size={p.get('size')} color={p.get('color')} text={p.get('text','')!r}")
        elif t == "note":
            lines.append(f"  note at ({x},{y}) color={p.get('color')} text={p.get('text','')!r}")
        elif t == "arrow":
            lines.append(f"  arrow at ({x},{y}) color={p.get('color')}")
        else:
            lines.append(f"  {t} at ({x},{y})")
    return "\n".join(lines)
