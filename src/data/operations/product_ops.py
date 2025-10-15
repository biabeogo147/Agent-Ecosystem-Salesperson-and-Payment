from data.connection import PostgresConnection
from data.models.product import Product

def find_products_list_by_substring(query_string: str):
    """
    Find product by SKU or substring of name.
    """
    connection = PostgresConnection(database="product_db")
    session = connection.get_session()
    
    query_string = f"%{query_string.lower()}%"
    
    results = session.query(Product).filter(
        (Product.sku.ilike(query_string)) |
        (Product.name.ilike(query_string))
    ).all()

    lst_product = [product.to_dict() for product in results]
    
    print("Results from DB query: ", lst_product)
    
    session.close()
    
    return lst_product
        