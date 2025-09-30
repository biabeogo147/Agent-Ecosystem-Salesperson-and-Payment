from data.product.model import ProductModel
 
def _to_dict(product: ProductModel):
    return {
        "sku": product.sku,
        "name": product.name,
        "price": product.price,
        "currency": product.currency,
        "stock": product.stock
    }