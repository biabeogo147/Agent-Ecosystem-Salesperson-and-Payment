from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.utils.response_format import ResponseFormat
from src.utils.status import Status
from src.web_hook.schemas.product_schemas import ProductCreate, ProductUpdate
from src.web_hook.services.product_service import (
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
        product = await create_product(data)
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
        product = await update_product(sku, data)
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
async def get_product_endpoint(sku: str, merchant_id: int):
    """Get a product by SKU."""
    product = await get_product(sku, merchant_id)
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
async def list_products_endpoint(merchant_id: int):
    """List all products."""
    products = await get_all_products(merchant_id)
    return JSONResponse(
        content=ResponseFormat(
            status=Status.SUCCESS,
            message="SUCCESS",
            data=[p.to_dict() for p in products]
        ).to_dict()
    )


@router.delete("/{sku}")
async def delete_product_endpoint(sku: str, merchant_id: int):
    """Delete a product by SKU. Requires merchant_id to verify ownership."""
    try:
        if not await delete_product(sku, merchant_id):
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
    except ValueError as e:
         return JSONResponse(
            status_code=403,
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