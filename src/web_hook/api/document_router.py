from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.web_hook import webhook_logger as logger
from src.utils.status import Status
from src.utils.response_format import ResponseFormat

from src.web_hook.services.product_service import get_product
from src.web_hook.schemas.document_schemas import DocumentCreate
from src.web_hook.services.document_service import insert_document

router = APIRouter(prefix="/webhook/documents", tags=["Documents"])


@router.post("")
async def create_document_endpoint(data: DocumentCreate):
    """
    Insert a document into the vector database.
    Use product_sku from the product creation response to link documents to products.
    """
    try:
        product = get_product(data.product_sku, data.merchant_id)
        if not product:
            return JSONResponse(
                status_code=404,
                content=ResponseFormat(
                    status=Status.PRODUCT_NOT_FOUND,
                    message=f"Product with SKU '{data.product_sku}' not found. Create product first.",
                    data=None
                ).to_dict()
            )
        logger.info(f"Product found: {product.sku} - {product.name}")

        result = insert_document(data)
        return JSONResponse(
            status_code=201,
            content=ResponseFormat(
                status=Status.SUCCESS,
                message="Document inserted successfully",
                data=result
            ).to_dict()
        )
    except RuntimeError as e:
        return JSONResponse(
            status_code=500,
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