# A2A (Agent-to-Agent) Payment Workflow

## Overview

Hệ thống sử dụng giao thức A2A để giao tiếp giữa **Salesperson Agent** và **Payment Agent** trong quá trình xử lý thanh toán.

---

## Enum

| Enum | Giá trị | Mô tả |
|------|---------|-------|
| **PaymentStatus** | `PENDING`, `SUCCESS`, `FAILED`, `CANCELLED` | Trạng thái thanh toán |
| **PaymentChannel** | `redirect`, `qr` | Kênh thanh toán |
| **NextActionType** | `NONE`, `ASK_USER`, `REDIRECT`, `SHOW_QR` | Hành động tiếp theo |
| **PaymentAction** | `CREATE_ORDER`, `QUERY_STATUS`, `CANCEL` | Loại action |
| **PaymentMethodType** | `PAYGATE` | Loại phương thức thanh toán |
| **ProtocolVersion** | `A2A_V1` | Phiên bản giao thức |

---

## Workflow

```mermaid
sequenceDiagram
    autonumber

    participant U as User/Client
    participant S as Salesperson Agent
    participant P as Payment Agent
    participant G as Payment Gateway

    rect rgb(220, 245, 255)
        Note over U,S: Tạo đơn hàng

        U ->> S: Chọn sản phẩm, nhập thông tin
        S ->> P: PaymentRequest<br/>action=CREATE_ORDER
        P ->> G: Validate request -> Tạo Order trong DB<br/>Gọi Payment Gateway
        P -->> S: PaymentResponse<br/>status=PENDING<br/>next_action=REDIRECT
        S -->> U: Redirect user đến pay_url
    end

    rect rgb(255, 240, 220)
        Note over U,G: Thanh toán

        U ->> G: User thanh toán trên Payment Gateway
    end

    rect rgb(230, 255, 230)
        Note over P,G: Xác nhận trạng thái đơn hàng

        G -->> P: Callback to return_url / notify_url
        P ->> G: Query Order Status
        G -->> P: Order Status<br/>status=SUCCESS / FAILED
        P -->> S: PaymentResponse<br/>status=SUCCESS / FAILED
        S -->> U: Hiển thị kết quả thanh toán
    end
```