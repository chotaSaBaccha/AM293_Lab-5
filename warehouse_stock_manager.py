
"""Manage warehouse inventory, stock reports, and adjustments."""

import hashlib
import json
import os
from datetime import datetime

warehouse_stock = {}
AUDIT_FILE = "warehouse_audit.log"
SUPERVISOR_PASSWORD = os.environ.get("WAREHOUSE_SUPERVISOR_PASSWORD")


def add_stock(sku="default", qty=0, history=None):
    """Add stock for a valid SKU and optionally record receipt history."""
    if not isinstance(sku, str) or not sku.strip():
        raise ValueError("SKU must be a non-empty string.")

    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 0:
        raise ValueError("Quantity must be a non-negative integer.")

    if history is None:
        history = []

    warehouse_stock[sku] = warehouse_stock.get(sku, 0) + qty
    history.append(
        f"{datetime.now()}: Received {qty} units of {sku}"
    )


def remove_stock(sku, qty):
    """Remove stock without silently ignoring invalid operations."""
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 0:
        raise ValueError("Quantity must be a non-negative integer.")

    if sku not in warehouse_stock:
        return

    if qty >= warehouse_stock[sku]:
        del warehouse_stock[sku]
    else:
        warehouse_stock[sku] -= qty


def get_stock(sku):
    """Return the available quantity for a SKU, or zero if absent."""
    return warehouse_stock.get(sku, 0)


def sku_checksum(sku):
    """Return a short SHA-256 fingerprint for a printed SKU label."""
    return hashlib.sha256(sku.encode("utf-8")).hexdigest()[:6]


def load_stock(file="warehouse.json"):
    """Load and validate warehouse inventory from a JSON file."""
    with open(file, "r", encoding="utf-8") as stock_file:
        loaded_stock = json.load(stock_file)

    if not isinstance(loaded_stock, dict):
        raise ValueError("Warehouse data must be a JSON object.")

    for sku, quantity in loaded_stock.items():
        if (
            not isinstance(sku, str)
            or not isinstance(quantity, int)
            or isinstance(quantity, bool)
            or quantity < 0
        ):
            raise ValueError("Warehouse data contains invalid stock.")

    warehouse_stock.clear()
    warehouse_stock.update(loaded_stock)


def save_stock(file="warehouse.json"):
    """Save warehouse inventory to a JSON file."""
    with open(file, "w", encoding="utf-8") as stock_file:
        json.dump(warehouse_stock, stock_file, indent=4)


def print_report():
    """Print the warehouse stock report."""
    print("Warehouse Stock Report")

    for sku, quantity in warehouse_stock.items():
        checksum = sku_checksum(sku)
        print(f"{sku} -> {quantity} units [chk: {checksum}]")


def check_reorder(threshold=10):
    """Return SKUs with stock below the specified threshold."""
    if not isinstance(threshold, int) or isinstance(threshold, bool):
        raise ValueError("Threshold must be an integer.")

    return [
        sku
        for sku, quantity in warehouse_stock.items()
        if quantity < threshold
    ]


def apply_adjustment(sku, adjustment, password):
    """Apply a supervisor-authorized numeric stock adjustment."""
    if not SUPERVISOR_PASSWORD or password != SUPERVISOR_PASSWORD:
        raise PermissionError("Invalid or missing supervisor password.")

    if (
        not isinstance(adjustment, int)
        or isinstance(adjustment, bool)
    ):
        raise ValueError("Adjustment must be an integer.")

    current = warehouse_stock.get(sku, 0)
    new_quantity = current + adjustment

    if new_quantity < 0:
        raise ValueError("Stock quantity cannot be negative.")

    warehouse_stock[sku] = new_quantity

    with open(AUDIT_FILE, "a", encoding="utf-8") as audit_file:
        audit_file.write(
            f"Adjusted {sku} by {adjustment} units "
            f"at {datetime.now().isoformat()}\n"
        )


def main():
    """Run a sample warehouse inventory workflow."""
    add_stock("WID-001", 40)
    add_stock("WID-002", 4)
    add_stock("WID-404", 15)

    remove_stock("WID-001", 12)
    remove_stock("GHOST-9", 1)
    remove_stock("WID-001", 500)

    print("WID-002 stock:", get_stock("WID-002"))
    print("Needs reorder:", check_reorder())

    password = SUPERVISOR_PASSWORD
    if password:
        apply_adjustment("WID-002", 25, password)

    save_stock()
    load_stock()
    print_report()
    print("Stock audit complete.")


if __name__ == "__main__":
    main()
