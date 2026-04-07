import json
import os
from typing import Any, Dict, List, Optional


# =========================
# Helpers
# =========================

def _coerce_data(data: Any) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data

    if isinstance(data, str):
        text = data.strip()
        if not text:
            raise ValueError("Empty data string.")
        if text.lower().endswith(".json") and os.path.isfile(text):
            with open(text, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON string.") from exc

    raise ValueError("Unsupported data type. Expected dict or JSON string/path.")


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _find_item_by_id(data: Dict[str, Any], item_id: str) -> Optional[Dict[str, Any]]:
    for item in data.get("items", []):
        if item.get("id") == item_id:
            return item
    return None


def _find_item_by_name(data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    name_norm = _normalize_text(name)
    for item in data.get("items", []):
        item_name = _normalize_text(item.get("name_vi", ""))
        if name_norm in item_name or item_name in name_norm:
            return item
    return None


def _find_combo_by_id(data: Dict[str, Any], combo_id: str) -> Optional[Dict[str, Any]]:
    for combo in data.get("combos", []):
        if combo.get("id") == combo_id:
            return combo
    return None


def _find_combo_by_name(data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    name_norm = _normalize_text(name)
    for combo in data.get("combos", []):
        combo_name = _normalize_text(combo.get("name_vi", ""))
        if name_norm in combo_name or combo_name in name_norm:
            return combo
    return None


def _find_discount_by_code(data: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    code = code.strip().upper()
    for discount in data.get("discounts", []):
        if discount.get("code", "").upper() == code:
            return discount
    return None


def _apply_discount(base_amount: int, discount: Dict[str, Any]) -> int:
    if discount.get("type") == "percentage":
        return int(base_amount * discount.get("value", 0) / 100)
    if discount.get("type") == "fixed":
        return min(int(discount.get("value", 0)), base_amount)
    return 0


def _format_currency(value: int) -> str:
    return f"{value:,} VND".replace(",", ".")


# =========================
# 1) get_item()
# =========================

def get_item(
    data: Dict[str, Any],
    item_id: Optional[str] = None,
    name: Optional[str] = None,
    category_vi: Optional[str] = None,
    available_only: bool = False,
) -> Dict[str, Any]:
    """
    Tìm món theo id, tên, hoặc category.
    """
    try:
        data = _coerce_data(data)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    results = []
    for item in data.get("items", []):
        if item_id and item.get("id") != item_id:
            continue
        if name and _normalize_text(name) not in _normalize_text(item.get("name_vi", "")):
            continue
        if category_vi and _normalize_text(category_vi) != _normalize_text(item.get("category_vi", "")):
            continue
        if available_only and not item.get("available", False):
            continue
        results.append(item)

    return {"success": True, "count": len(results), "items": results}


# =========================
# 2) get_combo()
# =========================

def get_combo(
    data: Dict[str, Any],
    combo_id: Optional[str] = None,
    name: Optional[str] = None,
    available_only: bool = False,
) -> Dict[str, Any]:
    """
    Tìm combo theo id hoặc tên.
    """
    try:
        data = _coerce_data(data)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    results = []
    for combo in data.get("combos", []):
        if combo_id and combo.get("id") != combo_id:
            continue
        if name:
            name_norm = _normalize_text(name)
            combo_name = _normalize_text(combo.get("name_vi", ""))
            if name_norm not in combo_name and combo_name not in name_norm:
                continue
        if available_only and not combo.get("available", False):
            continue
        results.append(combo)

    return {"success": True, "count": len(results), "combos": results}


# =========================
# 3) get_discount()
# =========================

def get_discount(
    data: Dict[str, Any],
    code: Optional[str] = None,
    active_only: bool = False,
) -> Dict[str, Any]:
    """
    Lấy discount theo code hoặc lấy toàn bộ discount.
    """
    try:
        data = _coerce_data(data)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    discounts = data.get("discounts", [])

    if code:
        discount = _find_discount_by_code(data, code)
        if not discount:
            return {"success": False, "message": f"Không tìm thấy mã giảm giá '{code}'."}
        if active_only and not discount.get("active", False):
            return {
                "success": False,
                "message": f"Mã giảm giá '{code}' hiện không còn hiệu lực.",
                "discount": discount,
            }
        return {"success": True, "discount": discount}

    results = []
    for d in discounts:
        if active_only and not d.get("active", False):
            continue
        results.append(d)

    return {"success": True, "count": len(results), "discounts": results}


# =========================
# 4) get_best_seller()
# =========================

def get_best_seller(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Trả về best seller.
    """
    try:
        data = _coerce_data(data)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    best_seller = data.get("best_seller")
    if not best_seller:
        return {"success": False, "message": "Best seller data not found."}

    item = _find_item_by_id(data, best_seller.get("item_id", ""))
    return {"success": True, "best_seller": best_seller, "item_detail": item}


# =========================
# Pricing + Stock helpers
# =========================

def _resolve_item(data: Dict[str, Any], item_ref: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    item_id = item_ref.get("item_id")
    name = item_ref.get("name")
    if item_id:
        return _find_item_by_id(data, item_id)
    if name:
        return _find_item_by_name(data, name)
    return None


def _resolve_combo(data: Dict[str, Any], combo_ref: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    combo_id = combo_ref.get("combo_id")
    name = combo_ref.get("name")
    if combo_id:
        return _find_combo_by_id(data, combo_id)
    if name:
        return _find_combo_by_name(data, name)
    return None


def _calculate_order(
    data: Dict[str, Any],
    order_items: List[Dict[str, Any]],
    order_combos: List[Dict[str, Any]],
) -> Dict[str, Any]:
    bill_details = {"items": [], "combos": []}
    subtotal_items = 0
    subtotal_combos = 0
    side_subtotal = 0

    required_by_item: Dict[str, int] = {}
    available_by_item: Dict[str, int] = {}
    name_by_item: Dict[str, str] = {}

    # ---- Items ----
    for order in order_items:
        quantity = int(order.get("quantity", 0))
        if quantity <= 0:
            return {"success": False, "message": "Số lượng món không hợp lệ."}

        item = _resolve_item(data, order)
        if not item:
            return {"success": False, "message": "Không tìm thấy món bạn yêu cầu."}
        if not item.get("available", False):
            return {"success": False, "message": f"Món '{item.get('name_vi')}' hiện không còn bán."}

        item_id = item.get("id")
        stock = int(item.get("stock", 0))
        required_by_item[item_id] = required_by_item.get(item_id, 0) + quantity
        available_by_item[item_id] = stock
        name_by_item[item_id] = item.get("name_vi", "")

        line_total = int(item.get("price", 0)) * quantity
        subtotal_items += line_total
        if item.get("category_vi") == "Món phụ":
            side_subtotal += line_total

        bill_details["items"].append(
            {
                "item_id": item.get("id"),
                "name_vi": item.get("name_vi"),
                "unit_price": item.get("price"),
                "quantity": quantity,
                "line_total": line_total,
            }
        )

    # ---- Combos ----
    for order in order_combos:
        quantity = int(order.get("quantity", 0))
        if quantity <= 0:
            return {"success": False, "message": "Số lượng combo không hợp lệ."}

        combo = _resolve_combo(data, order)
        if not combo:
            return {"success": False, "message": "Không tìm thấy combo bạn yêu cầu."}
        if not combo.get("available", False):
            return {"success": False, "message": f"Combo '{combo.get('name_vi')}' hiện không còn bán."}

        line_total = int(combo.get("combo_price", 0)) * quantity
        subtotal_combos += line_total

        bill_details["combos"].append(
            {
                "combo_id": combo.get("id"),
                "name_vi": combo.get("name_vi"),
                "unit_price": combo.get("combo_price"),
                "quantity": quantity,
                "line_total": line_total,
            }
        )

        # Accumulate stock requirements from items inside combo
        for combo_item in combo.get("items", []):
            combo_item_id = combo_item.get("item_id")
            combo_item_qty = int(combo_item.get("quantity", 0)) * quantity
            item = _find_item_by_id(data, combo_item_id)
            if not item:
                return {"success": False, "message": "Combo chứa món không tồn tại trong kho."}
            if not item.get("available", False):
                return {
                    "success": False,
                    "message": f"Món '{item.get('name_vi')}' trong combo hiện không còn bán.",
                }
            item_id = item.get("id")
            stock = int(item.get("stock", 0))
            required_by_item[item_id] = required_by_item.get(item_id, 0) + combo_item_qty
            available_by_item[item_id] = stock
            name_by_item[item_id] = item.get("name_vi", "")

    # ---- Stock check ----
    stock_details = []
    stock_ok = True
    for item_id, required_qty in required_by_item.items():
        available_qty = available_by_item.get(item_id, 0)
        is_enough = required_qty <= available_qty
        if not is_enough:
            stock_ok = False
        stock_details.append(
            {
                "item_id": item_id,
                "name_vi": name_by_item.get(item_id, ""),
                "required_qty": required_qty,
                "available_qty": available_qty,
                "is_enough": is_enough,
            }
        )

    if not stock_ok:
        shortage = next((d for d in stock_details if not d["is_enough"]), None)
        if shortage:
            return {
                "success": False,
                "message": (
                    f"Xin lỗi, món '{shortage['name_vi']}' không đủ hàng. "
                    f"Bạn cần {shortage['required_qty']} phần nhưng hiện chỉ còn {shortage['available_qty']} phần."
                ),
            }

    subtotal = subtotal_items + subtotal_combos

    return {
        "success": True,
        "bill_details": bill_details,
        "subtotal_items": subtotal_items,
        "subtotal_combos": subtotal_combos,
        "subtotal": subtotal,
        "side_subtotal": side_subtotal,
        "stock_check": {"ok": stock_ok, "details": stock_details},
    }


def _pick_best_discount(data: Dict[str, Any], subtotal: int, side_subtotal: int) -> Dict[str, Any]:
    best = {"discount": None, "discount_amount": 0}
    for d in data.get("discounts", []):
        if not d.get("active", False):
            continue
        min_order_value = int(d.get("min_order_value", 0))
        if subtotal < min_order_value:
            continue
        applicable_to_vi = d.get("applicable_to_vi", "Tất cả món")
        if applicable_to_vi == "Món phụ":
            base_amount = side_subtotal
        else:
            base_amount = subtotal
        discount_amount = _apply_discount(base_amount, d)
        if discount_amount > best["discount_amount"]:
            best = {"discount": d, "discount_amount": discount_amount}
    return best


# =========================
# 5) compare_items_vs_combo()
# =========================

def compare_items_vs_combo(
    data: Dict[str, Any],
    order_items: List[Dict[str, Any]],
    combo_id: str,
    combo_quantity: int = 1,
) -> Dict[str, Any]:
    """
    So sánh giá giữa gọi các món lẻ (order_items) và gọi combo.
    """
    try:
        data = _coerce_data(data)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    items_calc = _calculate_order(data, order_items, [])
    if not items_calc.get("success"):
        return items_calc

    combo_calc = _calculate_order(
        data,
        [],
        [{"combo_id": combo_id, "quantity": combo_quantity}],
    )
    if not combo_calc.get("success"):
        return combo_calc

    items_best = _pick_best_discount(data, items_calc["subtotal"], items_calc["side_subtotal"])
    combo_best = _pick_best_discount(data, combo_calc["subtotal"], combo_calc["side_subtotal"])

    items_total = items_calc["subtotal"] - items_best["discount_amount"]
    combo_total = combo_calc["subtotal"] - combo_best["discount_amount"]

    if items_total < combo_total:
        cheaper = "items"
    elif combo_total < items_total:
        cheaper = "combo"
    else:
        cheaper = "equal"

    return {
        "success": True,
        "items_option": {
            "bill_details": items_calc["bill_details"],
            "subtotal": items_calc["subtotal"],
            "best_discount": items_best["discount"],
            "discount_amount": items_best["discount_amount"],
            "total_after_discount": items_total,
            "stock_check": items_calc["stock_check"],
        },
        "combo_option": {
            "bill_details": combo_calc["bill_details"],
            "subtotal": combo_calc["subtotal"],
            "best_discount": combo_best["discount"],
            "discount_amount": combo_best["discount_amount"],
            "total_after_discount": combo_total,
            "stock_check": combo_calc["stock_check"],
        },
        "comparison": {
            "cheaper_option": cheaper,
            "difference": abs(items_total - combo_total),
        },
    }


# =========================
# 6) calculating_total_bill()
# =========================

def calculating_total_bill(
    data: Dict[str, Any],
    order_items: Optional[List[Dict[str, Any]]] = None,
    order_combos: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Tính tổng bill (tự động chọn mã giảm giá tốt nhất nếu có).
    """
    try:
        data = _coerce_data(data)
    except ValueError as exc:
        return {"success": False, "message": str(exc)}

    order_items = order_items or []
    order_combos = order_combos or []

    calc = _calculate_order(data, order_items, order_combos)
    if not calc.get("success"):
        return calc

    best = _pick_best_discount(data, calc["subtotal"], calc["side_subtotal"])
    discount = best["discount"]
    discount_amount = best["discount_amount"]
    total_after_discount = calc["subtotal"] - discount_amount

    applied_discount = None
    if discount:
        applied_discount = {
            "code": discount.get("code"),
            "type": discount.get("type"),
            "value": discount.get("value"),
            "discount_amount": discount_amount,
        }

    return {
        "success": True,
        "bill_details": calc["bill_details"],
        "subtotal_items": calc["subtotal_items"],
        "subtotal_combos": calc["subtotal_combos"],
        "subtotal": calc["subtotal"],
        "applied_discount": applied_discount,
        "discount_amount": discount_amount,
        "total_after_discount": total_after_discount,
        "grand_total": total_after_discount,
        "stock_check": calc["stock_check"],
    }
