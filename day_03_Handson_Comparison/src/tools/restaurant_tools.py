import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "mock_data.json"

# Friendly aliases for easier lookup from natural language prompts.
ITEM_ALIASES: Dict[str, str] = {
    "GA2": "I001",
    "GA4": "I002",
    "BURGER": "I003",
    "FRIES": "I004",
    "PEPSI": "I005",
    "SALAD": "I006",
    "NUGGETS": "I007",
    "CHEESE_BALLS": "I008",
}

COMBO_ALIASES: Dict[str, str] = {
    "PERSONAL": "C001",
    "FF2": "C002",
    "FAMILY": "C003",
}


def _load_data() -> Dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


_DATA = _load_data()
_ITEM_LIST: List[Dict[str, Any]] = _DATA.get("items", [])
_COMBO_LIST: List[Dict[str, Any]] = _DATA.get("combos", [])
_BEST_SELLER_RAW: Dict[str, Any] = _DATA.get("best_seller", {})

ITEMS: Dict[str, Dict[str, Any]] = {item["id"]: item for item in _ITEM_LIST}
COMBOS: Dict[str, Dict[str, Any]] = {combo["id"]: combo for combo in _COMBO_LIST}


def _normalize_key(value: str) -> str:
    return value.strip().upper().replace(" ", "_")


def _strip_accents(value: str) -> str:
    normalized = "".join(
        ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn"
    )
    return normalized.replace("đ", "d").replace("Đ", "D")


def _find_item(value: str) -> Optional[Dict[str, Any]]:
    key = _normalize_key(value)
    mapped_key = ITEM_ALIASES.get(key, key)

    if mapped_key in ITEMS:
        return ITEMS[mapped_key]

    value_lower = value.strip().lower()
    value_plain = _strip_accents(value_lower)
    for item in ITEMS.values():
        item_name = item["name_vi"].lower()
        if item_name == value_lower or _strip_accents(item_name) == value_plain:
            return item
    return None


def get_item(item: str) -> Dict[str, Any]:
    """Get menu item details by code or exact name."""
    found = _find_item(item)
    if not found:
        return {
            "ok": False,
            "message": f"Item '{item}' not found.",
        }
    return {
        "ok": True,
        "item": found,
    }


def get_best_seller() -> Dict[str, Any]:
    """Get the top-selling available item."""
    best_id = _BEST_SELLER_RAW.get("item_id")
    best = ITEMS.get(best_id) if best_id else None

    if not best:
        available_items = [item for item in ITEMS.values() if item.get("available")]
        best = max(available_items, key=lambda x: x.get("stock", 0))

    return {
        "ok": True,
        "item": best,
        "reason": _BEST_SELLER_RAW.get("reason_vi"),
    }


def get_best_five() -> Dict[str, Any]:
    """Get top-5 available items.

    The mock data only defines one explicit best seller, so the remaining
    candidates are ranked by stock as a practical popularity proxy.
    """
    available_items = [item for item in ITEMS.values() if item.get("available")]
    sorted_items = sorted(available_items, key=lambda x: x.get("stock", 0), reverse=True)

    best_id = _BEST_SELLER_RAW.get("item_id")
    if best_id and best_id in ITEMS:
        best_item = ITEMS[best_id]
        sorted_items = [i for i in sorted_items if i["id"] != best_id]
        sorted_items.insert(0, best_item)

    return {
        "ok": True,
        "items": sorted_items[:5],
    }


def get_combo(combo_name: Optional[str] = None) -> Dict[str, Any]:
    """Get all combos or one combo by name."""
    if not combo_name:
        return {
            "ok": True,
            "combos": list(COMBOS.values()),
        }

    key = _normalize_key(combo_name)
    mapped_key = COMBO_ALIASES.get(key, key)
    combo = COMBOS.get(mapped_key)

    if not combo:
        normalized_query = combo_name.strip().lower()
        normalized_query_plain = _strip_accents(normalized_query)
        for c in COMBOS.values():
            combo_name_vi = c.get("name_vi", "").lower()
            if combo_name_vi == normalized_query or _strip_accents(combo_name_vi) == normalized_query_plain:
                combo = c
                break

    if not combo:
        return {
            "ok": False,
            "message": f"Combo '{combo_name}' not found.",
        }

    return {
        "ok": True,
        "combo": combo,
    }


def check_freeship(total_amount: int, city: str = "Ha Noi") -> Dict[str, Any]:
    """Check shipping availability and freeship based on city and bill total."""
    city_normalized = city.strip().lower()
    in_hanoi = city_normalized in {"ha noi", "hanoi"}

    if not in_hanoi:
        return {
            "ok": True,
            "deliverable": False,
            "freeship": False,
            "threshold": 200000,
            "message": "Delivery is only available in Ha Noi.",
        }

    freeship = total_amount >= 200000
    return {
        "ok": True,
        "deliverable": True,
        "freeship": freeship,
        "threshold": 200000,
        "remaining_for_freeship": 0 if freeship else 200000 - total_amount,
    }


def _tool_get_item(args: str) -> Dict[str, Any]:
    return get_item(args)


def _tool_get_best_seller(_: str = "") -> Dict[str, Any]:
    return get_best_seller()


def _tool_get_best_five(_: str = "") -> Dict[str, Any]:
    return get_best_five()


def _tool_get_combo(args: str) -> Dict[str, Any]:
    arg = args.strip()
    return get_combo(arg if arg else None)


def _tool_check_freeship(args: str) -> Dict[str, Any]:
    # Supported formats:
    # - "200000"
    # - "200000,Ha Noi"
    # - "Ha Noi,200000"
    raw = args.strip()
    if not raw:
        return {
            "ok": False,
            "message": "Missing args. Expected: total_amount[,city]",
        }

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    total_amount: Optional[int] = None
    city = "Ha Noi"

    for part in parts:
        digits = part.replace(".", "").replace("_", "")
        if digits.isdigit() and total_amount is None:
            total_amount = int(digits)
        else:
            city = part

    if total_amount is None:
        return {
            "ok": False,
            "message": "Could not parse total_amount from args.",
        }

    return check_freeship(total_amount=total_amount, city=city)


TOOL_REGISTRY: List[Dict[str, Any]] = [
    {
        "name": "get_item",
        "description": "Get an item by code or exact name. Input: item_code_or_name",
        "func": _tool_get_item,
    },
    {
        "name": "get_best_seller",
        "description": "Get the best-selling available menu item. No input needed.",
        "func": _tool_get_best_seller,
    },
    {
        "name": "get_best_five",
        "description": "Get top 5 best-selling available menu items. No input needed.",
        "func": _tool_get_best_five,
    },
    {
        "name": "get_combo",
        "description": "Get combo details by combo name. Empty input returns all combos.",
        "func": _tool_get_combo,
    },
    {
        "name": "check_freeship",
        "description": "Check delivery and freeship by total amount and city. Input: 'amount[,city]'.",
        "func": _tool_check_freeship,
    },
]
