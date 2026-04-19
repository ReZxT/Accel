import httpx
from pint import UnitRegistry, UndefinedUnitError, DimensionalityError

_ureg = UnitRegistry()
_ureg.default_format = "~P"  # compact format


async def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a value between physical units (length, weight, temperature, speed, area, volume, etc.)."""
    try:
        qty = value * _ureg(from_unit)
        result = qty.to(to_unit)
        mag = result.magnitude
        if isinstance(mag, float) and mag == int(mag) and abs(mag) < 1e12:
            mag = int(mag)
        return f"{value} {from_unit} = {mag} {to_unit}"
    except UndefinedUnitError as e:
        return f"Unknown unit: {e}"
    except DimensionalityError:
        return f"Cannot convert {from_unit} to {to_unit} (incompatible dimensions)"
    except Exception as e:
        return f"Conversion error: {e}"


async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """Convert between currencies using live exchange rates (requires internet)."""
    from_c = from_currency.upper()
    to_c = to_currency.upper()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"https://open.er-api.com/v6/latest/{from_c}")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Currency fetch failed: {e}"

    if data.get("result") != "success":
        return f"API error: {data.get('error-type', 'unknown')}"

    rates = data.get("rates", {})
    rate = rates.get(to_c)
    if rate is None:
        available = ", ".join(sorted(rates.keys())[:20])
        return f"Unknown currency '{to_c}'. Some available: {available}..."

    result = amount * rate
    return f"{amount} {from_c} = {result:.4f} {to_c} (rate: 1 {from_c} = {rate} {to_c}, updated: {data.get('time_last_update_utc', 'unknown')})"
