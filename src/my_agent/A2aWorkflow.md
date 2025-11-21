# A2A (Agent-to-Agent) Payment Workflow

## Overview

Hệ thống sử dụng giao thức A2A để giao tiếp giữa **Salesperson Agent** và **Payment Agent** trong quá trình xử lý thanh toán.

---

## Schemas

### 1. Enums

| Enum | Giá trị | Mô tả |
|------|---------|-------|
| **PaymentStatus** | `PENDING`, `SUCCESS`, `FAILED`, `CANCELLED` | Trạng thái thanh toán |
| **PaymentChannel** | `redirect`, `qr` | Kênh thanh toán |
| **NextActionType** | `NONE`, `ASK_USER`, `REDIRECT`, `SHOW_QR` | Hành động tiếp theo |
| **PaymentAction** | `CREATE_ORDER`, `QUERY_STATUS`, `CANCEL` | Loại action |
| **PaymentMethodType** | `PAYGATE` | Loại phương thức thanh toán |
| **ProtocolVersion** | `A2A_V1` | Phiên bản giao thức |

---

### 2. PaymentRequest

Yêu cầu thanh toán từ Salesperson Agent gửi đến Payment Agent.

```python
class PaymentRequest(BaseModel):
    protocol: ProtocolVersion       # Phiên bản giao thức (A2A_V1)
    context_id: str                 # ID giao dịch duy nhất
    from_agent: str                 # "salesperson_agent"
    to_agent: str                   # "payment_agent"
    action: PaymentAction           # CREATE_ORDER / QUERY_STATUS / CANCEL

    items: List[PaymentItem]        # Danh sách sản phẩm
    customer: CustomerInfo          # Thông tin khách hàng
    method: PaymentMethod           # Phương thức thanh toán

    note: Optional[str]             # Ghi chú
    metadata: Optional[Dict]        # Metadata bổ sung
```

**Ví dụ:**
```json
{
    "protocol": "A2A_V1",
    "context_id": "sale-abc-123",
    "from_agent": "salesperson_agent",
    "to_agent": "payment_agent",
    "action": "CREATE_ORDER",
    "items": [
        {
            "sku": "SKU001",
            "name": "iPhone 15 Pro",
            "quantity": 1,
            "unit_price": 999.99,
            "currency": "USD"
        }
    ],
    "customer": {
        "name": "Nguyen Van A",
        "email": "a@example.com",
        "phone": "+84123456789",
        "shipping_address": "123 ABC Street, HCM City"
    },
    "method": {
        "type": "PAYGATE",
        "channel": "redirect",
        "return_url": "https://shop.com/payment/return",
        "cancel_url": "https://shop.com/payment/cancel"
    }
}
```

---

### 3. PaymentResponse

Phản hồi từ Payment Agent trả về cho Salesperson Agent.

```python
class PaymentResponse(BaseModel):
    context_id: str                 # ID giao dịch (giống request)
    status: PaymentStatus           # PENDING / SUCCESS / FAILED / CANCELLED

    provider_name: Optional[str]    # Tên nhà cung cấp (nganluong, vnpay...)
    order_id: Optional[str]         # Mã đơn hàng từ provider
    pay_url: Optional[str]          # URL thanh toán (redirect channel)
    qr_code_url: Optional[str]      # URL hình QR (qr channel)
    expires_at: Optional[str]       # Thời gian hết hạn (ISO 8601)

    next_action: NextAction         # Hành động tiếp theo cho client
```

**Ví dụ (Redirect Channel):**
```json
{
    "context_id": "sale-abc-123",
    "status": "PENDING",
    "provider_name": "nganluong",
    "order_id": "ORD-12345",
    "pay_url": "https://checkout.nganluong.vn/pay/ORD-12345",
    "qr_code_url": null,
    "expires_at": "2024-01-15T10:30:00Z",
    "next_action": {
        "type": "REDIRECT",
        "url": "https://checkout.nganluong.vn/pay/ORD-12345",
        "expires_at": "2024-01-15T10:30:00Z"
    }
}
```

**Ví dụ (QR Channel):**
```json
{
    "context_id": "sale-abc-456",
    "status": "PENDING",
    "provider_name": "vnpay",
    "order_id": "ORD-67890",
    "pay_url": null,
    "qr_code_url": "https://qr.vnpay.vn/ORD-67890.png",
    "expires_at": "2024-01-15T10:30:00Z",
    "next_action": {
        "type": "SHOW_QR",
        "qr_code_url": "https://qr.vnpay.vn/ORD-67890.png",
        "expires_at": "2024-01-15T10:30:00Z"
    }
}
```

---

### 4. QueryStatusRequest

Yêu cầu tra cứu trạng thái thanh toán.

```python
class QueryStatusRequest(BaseModel):
    protocol: ProtocolVersion       # A2A_V1
    context_id: str                 # ID giao dịch cần tra cứu
    from_agent: str                 # "salesperson_agent"
    to_agent: str                   # "payment_agent"
    action: PaymentAction           # QUERY_STATUS
```

**Ví dụ:**
```json
{
    "protocol": "A2A_V1",
    "context_id": "sale-abc-123",
    "from_agent": "salesperson_agent",
    "to_agent": "payment_agent",
    "action": "QUERY_STATUS"
}
```

---

### 5. Sub-Schemas

#### PaymentItem
```python
class PaymentItem(BaseModel):
    sku: str            # Mã sản phẩm
    name: str           # Tên sản phẩm
    quantity: int       # Số lượng (> 0)
    unit_price: float   # Đơn giá (>= 0)
    currency: str       # Đơn vị tiền tệ (default: USD)
```

#### CustomerInfo
```python
class CustomerInfo(BaseModel):
    name: Optional[str]             # Tên khách hàng
    email: Optional[EmailStr]       # Email
    phone: Optional[str]            # Số điện thoại
    shipping_address: Optional[str] # Địa chỉ giao hàng
```

#### PaymentMethod
```python
class PaymentMethod(BaseModel):
    type: PaymentMethodType         # PAYGATE
    channel: PaymentChannel         # redirect / qr
    return_url: Optional[str]       # URL callback khi thanh toán thành công
    cancel_url: Optional[str]       # URL callback khi hủy thanh toán
```

#### NextAction
```python
class NextAction(BaseModel):
    type: NextActionType            # NONE / ASK_USER / REDIRECT / SHOW_QR
    expires_at: Optional[str]       # Thời gian hết hạn
    url: Optional[str]              # URL redirect (type=REDIRECT)
    qr_code_url: Optional[str]      # URL QR code (type=SHOW_QR)
```

---

## Workflow

### Flow Diagram

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   User/Client   │         │ Salesperson     │         │ Payment Agent   │
│                 │         │ Agent           │         │                 │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │ 1. Chọn sản phẩm,        │                           │
         │    nhập thông tin        │                           │
         │ ─────────────────────────>│                           │
         │                           │                           │
         │                           │ 2. PaymentRequest         │
         │                           │   action=CREATE_ORDER     │
         │                           │ ─────────────────────────>│
         │                           │                           │
         │                           │                           │ 3. Validate request
         │                           │                           │    Tạo Order trong DB
         │                           │                           │    Gọi Payment Gateway
         │                           │                           │
         │                           │ 4. PaymentResponse        │
         │                           │   status=PENDING          │
         │                           │   next_action=REDIRECT    │
         │                           │ <─────────────────────────│
         │                           │                           │
         │ 5. Redirect user         │                           │
         │    to pay_url            │                           │
         │ <─────────────────────────│                           │
         │                           │                           │
         │ 6. User thực hiện        │                           │
         │    thanh toán trên       │                           │
         │    Payment Gateway       │                           │
         │ ══════════════════════════════════════════════════════│
         │                           │                           │
         │ 7. Gateway callback      │                           │
         │    to return_url         │                           │
         │ ─────────────────────────>│                           │
         │                           │                           │
         │                           │ 8. QueryStatusRequest     │
         │                           │   action=QUERY_STATUS     │
         │                           │ ─────────────────────────>│
         │                           │                           │
         │                           │                           │ 9. Query DB/Gateway
         │                           │                           │
         │                           │ 10. PaymentResponse       │
         │                           │    status=SUCCESS/FAILED  │
         │                           │ <─────────────────────────│
         │                           │                           │
         │ 11. Hiển thị kết quả     │                           │
         │     thanh toán           │                           │
         │ <─────────────────────────│                           │
```

---

### Flow Steps

#### Phase 1: Tạo đơn hàng (Create Order)

| Step | Actor | Action |
|------|-------|--------|
| 1 | User | Chọn sản phẩm, nhập thông tin khách hàng |
| 2 | Salesperson Agent | Tạo `PaymentRequest` với `action=CREATE_ORDER` |
| 3 | Payment Agent | Validate request, tạo Order trong DB, gọi Payment Gateway |
| 4 | Payment Agent | Trả về `PaymentResponse` với `status=PENDING`, `next_action` |
| 5 | Salesperson Agent | Redirect user đến `pay_url` hoặc hiển thị QR code |

#### Phase 2: Thanh toán (Payment)

| Step | Actor | Action |
|------|-------|--------|
| 6 | User | Thực hiện thanh toán trên trang Payment Gateway |
| 7 | Payment Gateway | Callback về `return_url` sau khi thanh toán |

#### Phase 3: Xác nhận (Confirmation)

| Step | Actor | Action |
|------|-------|--------|
| 8 | Salesperson Agent | Gửi `QueryStatusRequest` để kiểm tra trạng thái |
| 9 | Payment Agent | Query DB hoặc Gateway để lấy trạng thái mới nhất |
| 10 | Payment Agent | Trả về `PaymentResponse` với `status=SUCCESS/FAILED` |
| 11 | Salesperson Agent | Hiển thị kết quả thanh toán cho user |

---

## Payment Channels

### 1. Redirect Channel

Chuyển hướng user đến trang thanh toán của Payment Gateway.

```
User → Salesperson Agent → Payment Agent → Payment Gateway
                                              ↓
User ← Salesperson Agent ← return_url ← Payment Gateway
```

**Khi nào sử dụng:**
- Web browser
- Mobile app với WebView
- Thanh toán thẻ tín dụng, ví điện tử

### 2. QR Channel

Hiển thị QR code để user quét và thanh toán.

```
User (scan QR) → Payment Gateway
                      ↓
User ← Salesperson Agent ← Webhook ← Payment Gateway
```

**Khi nào sử dụng:**
- POS tại cửa hàng
- Thanh toán qua app ngân hàng
- VNPay QR, MoMo QR

---

## Status Transitions

```
                    ┌──────────────┐
                    │   PENDING    │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ SUCCESS  │    │  FAILED  │    │CANCELLED │
    └──────────┘    └──────────┘    └──────────┘
```

| Status | Mô tả |
|--------|-------|
| `PENDING` | Đang chờ thanh toán |
| `SUCCESS` | Thanh toán thành công |
| `FAILED` | Thanh toán thất bại |
| `CANCELLED` | User hủy thanh toán |

---

## Error Handling

| Error | Response |
|-------|----------|
| Product not found | `status=02`, message="Product not found" |
| Order not found | `status=11`, message="Order not found" |
| Invalid request | `status=08`, message="Invalid params" |
| Gateway error | `status=99`, message="Unknown error" |

---

## File Structure

```
src/my_agent/my_a2a_common/
├── __init__.py
├── constants.py                    # Các hằng số
└── payment_schemas/
    ├── __init__.py
    ├── payment_request.py          # PaymentRequest
    ├── payment_response.py         # PaymentResponse
    ├── query_status_request.py     # QueryStatusRequest
    ├── payment_item.py             # PaymentItem
    ├── customer_info.py            # CustomerInfo
    ├── payment_method.py           # PaymentMethod
    ├── next_action.py              # NextAction
    └── payment_enums/
        ├── __init__.py
        ├── payment_status.py       # PaymentStatus
        ├── payment_channel.py      # PaymentChannel
        ├── payment_action.py       # PaymentAction
        ├── next_action_type.py     # NextActionType
        ├── payment_method_type.py  # PaymentMethodType
        └── protocol_version.py     # ProtocolVersion
```