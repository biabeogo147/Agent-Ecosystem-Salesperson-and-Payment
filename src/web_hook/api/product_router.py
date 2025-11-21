from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.web_hook.schemas import ProductCreate, ProductUpdate
from src.web_hook.services import (
    create_product,
    update_product,
    get_product,
    get_all_products,
    delete_product,
)

router = APIRouter(prefix="/webhook/products", tags=["Products"])


@router.post("")
async def create_product_endpoint(data: ProductCreate):
    """Create a new product. Returns the created product with its SKU."""
    try:
        product = create_product(data)
        return JSONResponse(
            status_code=201,
            content=ResponseFormat(
                status=Status.SUCCESS,
                message="Product created successfully",
                data=product.to_dict()
            ).to_dict()
        )
    except ValueError as e:
        return JSONResponse(
            status_code=409,
            content=ResponseFormat(
                status=Status.FAILURE,
                message=str(e),
                data=None
            ).to_dict()
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ResponseFormat(
                status=Status.UNKNOWN_ERROR,
                message=str(e),
                data=None
            ).to_dict()
        )


@router.put("/{sku}")
async def update_product_endpoint(sku: str, data: ProductUpdate):
    """Update an existing product by SKU."""
    try:
        product = update_product(sku, data)
        return JSONResponse(
            content=ResponseFormat(
                status=Status.SUCCESS,
                message="Product updated successfully",
                data=product.to_dict()
            ).to_dict()
        )
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content=ResponseFormat(
                status=Status.PRODUCT_NOT_FOUND,
                message=str(e),
                data=None
            ).to_dict()
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content=ResponseFormat(
                status=Status.UNKNOWN_ERROR,
                message=str(e),
                data=None
            ).to_dict()
        )


@router.get("/{sku}")
async def get_product_endpoint(sku: str):
    """Get a product by SKU."""
    product = get_product(sku)
    if not product:
        return JSONResponse(
            status_code=404,
            content=ResponseFormat(
                status=Status.PRODUCT_NOT_FOUND,
                message=f"Product '{sku}' not found",
                data=None
            ).to_dict()
        )
    return JSONResponse(
        content=ResponseFormat(
            status=Status.SUCCESS,
            message="SUCCESS",
            data=product.to_dict()
        ).to_dict()
    )


@router.get("")
async def list_products_endpoint():
    """List all products."""
    products = get_all_products()
    return JSONResponse(
        content=ResponseFormat(
            status=Status.SUCCESS,
            message="SUCCESS",
            data=[p.to_dict() for p in products]
        ).to_dict()
    )


@router.delete("/{sku}")
async def delete_product_endpoint(sku: str):
    """Delete a product by SKU."""
    if not delete_product(sku):
        return JSONResponse(
            status_code=404,
            content=ResponseFormat(
                status=Status.PRODUCT_NOT_FOUND,
                message=f"Product '{sku}' not found",
                data=None
            ).to_dict()
        )
    return JSONResponse(
        status_code=200,
        content=ResponseFormat(
            status=Status.SUCCESS,
            message="Product deleted successfully",
            data=None
        ).to_dict()
    )