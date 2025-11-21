from __future__ import annotations

import uuid

from google.adk.tools import FunctionTool

from src.config import RETURN_URL, CANCEL_URL
from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.utils.app_string import *


async def find_product(query: str) -> str:
    """
    Find product by SKU or substring of name.
    """
    from src.data.operations.product_ops import find_products_list_by_substring

    query = query.lower()
    results = find_products_list_by_substring(query)

    return ResponseFormat(data=results).to_json()


async def calc_shipping(weight: float, distance: float) -> str:
    """
    Calculate shipping cost based on weight (kg) and distance (km).
    """
    base_cost = 5.0  # base cost in USD
    weight_factor = 1.0  # cost per kg
    distance_factor = 0.5  # cost per km

    cost = base_cost + (weight * weight_factor) + (distance * distance_factor)
    return ResponseFormat(data=round(cost, 2)).to_json()


async def reserve_stock(sku: str, quantity: int) -> str:
    """
    Reserve stock for a given SKU and quantity.
    """
    from src.data.operations.product_ops import find_product_by_sku, update_product_stock

    product = find_product_by_sku(sku)

    if not product:
        return ResponseFormat(status=Status.PRODUCT_NOT_FOUND, data=False, message=PRODUCT_NOT_FOUND).to_json()

    if product.stock < quantity:
        return ResponseFormat(status=Status.QUANTITY_EXCEEDED, data=False, message=QUANTITY_EXCEEDED).to_json()

    result = update_product_stock(sku, product.stock - quantity)

    return ResponseFormat(data=result).to_json()


async def generate_context_id(prefix: str) -> str:
    """Create a unique correlation identifier used to track payment requests."""
    context_id = f"{prefix}-{uuid.uuid4()}"
    return ResponseFormat(data=context_id).to_json()


async def generate_return_url(context_id: str) -> str:
    """Build the return URL that the payment gateway should redirect to."""
    return_url = f"{RETURN_URL}?cid={context_id}"
    return ResponseFormat(data=return_url).to_json()


async def generate_cancel_url(context_id: str) -> str:
    """Build the cancel URL that the payment gateway should redirect to."""
    cancel_url = f"{CANCEL_URL}?cid={context_id}"
    return ResponseFormat(data=cancel_url).to_json()


print("Initializing ADK tool for salesperson...")
find_product_tool = FunctionTool(find_product)
calc_shipping_tool = FunctionTool(calc_shipping)
reserve_stock_tool = FunctionTool(reserve_stock)
generate_context_id_tool = FunctionTool(generate_context_id)
generate_return_url_tool = FunctionTool(generate_return_url)
generate_cancel_url_tool = FunctionTool(generate_cancel_url)
ADK_TOOLS_FOR_SALESPERSON = {
    find_product_tool.name: find_product_tool,
    calc_shipping_tool.name: calc_shipping_tool,
    reserve_stock_tool.name: reserve_stock_tool,
    generate_context_id_tool.name: generate_context_id_tool,
    generate_return_url_tool.name: generate_return_url_tool,
    generate_cancel_url_tool.name: generate_cancel_url_tool,
}
for adk_tool in ADK_TOOLS_FOR_SALESPERSON.values():
    print(f"ADK tool '{adk_tool.name}' initialized and ready to be exposed via MCP.")