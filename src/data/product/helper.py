from data.product.model import ProductModel

def _to_dict(product: ProductModel):
    print("Price type: ", type(product.price))
    return {
        "sku": product.sku,
        "name": product.name,
        "price": float(product.price),
        "currency": product.currency,
        "stock": product.stock
    }