# Webhook API Documentation

## Overview

API cho nhà cung cấp để quản lý sản phẩm và tài liệu.

**Base URL:** `http://localhost:8082`

**Response Format:**
```json
{
    "status": "00",
    "message": "SUCCESS",
    "data": { ... }
}
```

---

## Product APIs

### 1. Create Product

Tạo sản phẩm mới.

**Endpoint:** `POST /webhook/products`

**Request Body:**
```json
{
    "sku": "SKU001",
    "name": "iPhone 15 Pro",
    "price": 999.99,
    "currency": "USD",
    "stock": 100,
    "merchant_id": 1
}
```

| Field       | Type     | Required | Description                     |
|-------------|----------|----------|---------------------------------|
| sku         | string   | Yes      | Mã sản phẩm (unique)            |
| name        | string   | Yes      | Tên sản phẩm                    |
| price       | float    | Yes      | Giá (> 0)                       |
| currency    | string   | No       | Đơn vị tiền tệ (default: USD)   |
| stock       | int      | Yes      | Số lượng tồn kho (>= 0)         |
| merchant_id | int      | Yes      | ID của merchant sở hữu sản phẩm |

**Response Success (201):**
```json
{
    "status": "00",
    "message": "Product created successfully",
    "data": {
        "sku": "SKU001",
        "name": "iPhone 15 Pro",
        "price": 999.99,
        "currency": "USD",
        "stock": 100
    }
}
```

**Response Error (409 - Conflict):**
```json
{
    "status": "01",
    "message": "Product with SKU 'SKU001' already exists",
    "data": null
}
```

---

### 2. Update Product

Cập nhật thông tin sản phẩm.

**Endpoint:** `PUT /webhook/products/{sku}`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| sku | string | Mã sản phẩm |

**Request Body:**
```json
{
    "name": "iPhone 15 Pro Max",
    "price": 1199.99,
    "stock": 50,
    "merchant_id": 1
}
```

| Field       | Type     | Required | Description                     |
|-------------|----------|----------|---------------------------------|
| name        | string   | No       | Tên sản phẩm mới                |
| price       | float    | No       | Giá mới (> 0)                   |
| currency    | string   | No       | Đơn vị tiền tệ mới              |
| stock       | int      | No       | Số lượng tồn kho mới (>= 0)     |
| merchant_id | int      | No       | ID của merchant sở hữu sản phẩm |

**Response Success (200):**
```json
{
    "status": "00",
    "message": "Product updated successfully",
    "data": {
        "sku": "SKU001",
        "name": "iPhone 15 Pro Max",
        "price": 1199.99,
        "currency": "USD",
        "stock": 50
    }
}
```

**Response Error (404):**
```json
{
    "status": "02",
    "message": "Product with SKU 'SKU001' not found",
    "data": null
}
```

---

### 3. Get Product

Lấy thông tin sản phẩm theo SKU.

**Endpoint:** `GET /webhook/products/{sku}?merchant_id={merchant_id}`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| sku | string | Mã sản phẩm |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| merchant_id | int | Yes | ID của merchant để xác thực quyền truy cập |

**Response Success (200):**
```json
{
    "status": "00",
    "message": "SUCCESS",
    "data": {
        "sku": "SKU001",
        "name": "iPhone 15 Pro",
        "price": 999.99,
        "currency": "USD",
        "stock": 100
    }
}
```

**Response Error (404):**
```json
{
    "status": "02",
    "message": "Product 'SKU001' not found",
    "data": null
}
```

---

### 4. List Products

Lấy danh sách tất cả sản phẩm của merchant.

**Endpoint:** `GET /webhook/products?merchant_id={merchant_id}`

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| merchant_id | int | Yes | ID của merchant để lấy danh sách sản phẩm |

**Response Success (200):**
```json
{
    "status": "00",
    "message": "SUCCESS",
    "data": [
        {
            "sku": "SKU001",
            "name": "iPhone 15 Pro",
            "price": 999.99,
            "currency": "USD",
            "stock": 100
        },
        {
            "sku": "SKU002",
            "name": "Samsung Galaxy S24",
            "price": 899.99,
            "currency": "USD",
            "stock": 150
        }
    ]
}
```

---

### 5. Delete Product

Xóa sản phẩm theo SKU. Yêu cầu merchant_id để xác thực quyền sở hữu.

**Endpoint:** `DELETE /webhook/products/{sku}?merchant_id={merchant_id}`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| sku | string | Mã sản phẩm |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| merchant_id | int | Yes | ID của merchant để xác thực quyền xóa |

**Response Success (200):**
```json
{
    "status": "00",
    "message": "Product deleted successfully",
    "data": null
}
```

**Response Error (404):**
```json
{
    "status": "02",
    "message": "Product 'SKU001' not found",
    "data": null
}
```

**Response Error (403 - Forbidden):**
```json
{
    "status": "01",
    "message": "You do not have permission to delete this product",
    "data": null
}
```

---

## Document APIs

### 1. Create Document

Thêm tài liệu vào vector database. Sử dụng `product_sku` từ response của API tạo product để liên kết.

**Endpoint:** `POST /webhook/documents`

**Request Body:**
```json
{
    "text": "iPhone 15 Pro features A17 Pro chip, titanium design, and advanced camera system.",
    "title": "iPhone 15 Pro Product Guide",
    "product_sku": "SKU001",
    "chunk_id": 1,
    "merchant_id": 1
}
```

| Field       | Type    | Required | Description                          |
|-------------|---------|----------|--------------------------------------|
| text        | string  | Yes      | Nội dung tài liệu                    |
| title       | string  | Yes      | Tiêu đề tài liệu                     |
| product_sku | string  | No       | SKU sản phẩm liên kết (phải tồn tại) |
| chunk_id    | int     | No       | ID chunk nếu tài liệu được chia nhỏ  |
| merchant_id | int     | No       | ID của merchant liên kết             |

**Response Success (201):**
```json
{
    "status": "00",
    "message": "Document inserted successfully",
    "data": {
        "id": 1234567890123456789,
        "text": "iPhone 15 Pro features A17 Pro chip...",
        "title": "iPhone 15 Pro Product Guide",
        "product_sku": "SKU001",
        "chunk_id": 1,
        "message": "Document inserted successfully with ID 1234567890123456789"
    }
}
```

**Response Error (404 - Product not found):**
```json
{
    "status": "02",
    "message": "Product with SKU 'SKU001' not found. Create product first.",
    "data": null
}
```