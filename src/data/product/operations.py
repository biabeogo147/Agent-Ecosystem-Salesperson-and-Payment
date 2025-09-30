from data.connection import PostgresConnection
from data.product.model import ProductModel
from data.product.helper import _to_dict
    
def find_products_list_by_substring(query_string: str):
    """
    Find product by SKU or substring of name.
    """
    connection = PostgresConnection(database="product_db")
    session = connection.get_session()
    
    query_string = f"%{query_string.lower()}%"
    
    results = session.query(ProductModel).filter(
        (ProductModel.sku.ilike(query_string)) | 
        (ProductModel.name.ilike(query_string))
    ).all()
    
    session.close()
    
    return [_to_dict(product) for product in results]
        