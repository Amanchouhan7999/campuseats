# CampusEats Web Services — Comprehensive Project Notes

**Course:** CS543 Web Services  
**Team ID:** TEAM-07  
**Team Members:**  
- Student 1 Shirish (Roll No: 20252651056)  
- Student 2 Deepamoni (Roll No: 20252651016)  
- Student 3 Aman Chouhan (Roll No: 20252651006)  
- Student 4 Sanu Swarnakar (Roll No: 20252651048)

---

## Part 1: Assignment 4 — REST Service Modeling & Network Resilience

### 1.1 Resource Table
| Method | URL | What It Does | Success Code | Failure Codes |
|---|---|---|---|---|
| `POST` | `/orders` | Creates a new CampusEats order from a validated cart | `201 Created` | `400`, `401`, `422`, `429` |
| `GET` | `/orders` | Lists and filters existing orders by status via query param | `200 OK` | `400`, `401`, `429` |
| `GET` | `/orders/{orderId}` | Fetches detailed representation of a specific order | `200 OK` | `304`, `401`, `404`, `429` |
| `POST` | `/orders/{orderId}/cancellation` | State-changing sub-resource operation to cancel an active order | `200 OK` | `401`, `404`, `409`, `412`, `422`, `429` |

---

### 1.2 A5 Hard Choice Justification
*   **The Operation:** `cancelOrder(orderId, reason)`
*   **Rejection:** Originally, this operation looked like an RPC-style procedure call: `POST /cancelOrder` or `POST /orders/123?action=cancel`. We rejected this because exposing verbs directly in the URI breaks RESTful resource-oriented modeling. We also rejected `DELETE /orders/{orderId}` because in a domain like food delivery, cancelling an order does not hard-delete the database record; the order transitions into a `CANCELLED` state and generates audit logs, refund workflows, and rider notifications.
*   **Resolution:** We resolved this by modeling cancellation as a durable sub-resource: `POST /orders/{orderId}/cancellation`. Creating a cancellation record modifies the lifecycle state of the parent order resource in a pure RESTful manner without leaking procedural verbs into the endpoint URI.

---

### 1.3 D3 Outbound Dependency Hardening & Fallback Reasoning
*   **Outbound Call:** The `Orders` service makes a HTTP call to the downstream `Payments` service (`POST /charge`) when an order is created.
*   **Hardening Strategy:** The outbound HTTP client uses a 2.0-second socket timeout paired with exponential backoff retries with random jitter (3 retries). Retries are strictly restricted to transient network errors and server errors (`500`, `502`, `503`, `504`). Client errors (`4xx`) are never retried. Outbound requests carry an `Idempotency-Key` header so that repeated network calls do not result in double charges.
*   **Fallback Reasoning:** If the `Payments` gateway remains unreachable after all retries exhaust, the `Orders` service accepts the order into a `PENDING_PAYMENT` state rather than failing with an unhandled exception or returning an HTTP 500. 
*   **Justification:** Complete failure would discard the student's assembled cart and force a full re-order attempt during peak campus lunch hours. Degrading the order state allows asynchronous payment processing workers to retry charging the user in the background while keeping the ordering pipeline alive.

---

### 1.4 Assignment 4 Questions & Answers

#### Q1: Count the lines in your Assignment 3 WSDL and in your openapi.yaml. What is the difference actually made of? Name two things the WSDL declared that the OpenAPI file does not need to.
*   **Line Count Comparison:** `partner.wsdl` (~115 lines) vs `openapi.yaml` (~260 lines).
*   **What the Difference is Made Of:** The WSDL is dominated by verbose XML namespace declarations (`xmlns:soap`, `xmlns:tns`, `xmlns:xsd`), explicit message parameter mappings, and multi-layered binding hierarchies. OpenAPI is longer primarily because it explicitly documents every possible HTTP status code (`201`, `304`, `401`, `404`, `406`, `409`, `412`, `422`, `429`), inline schemas, and response header definitions.
*   **Two Things WSDL Declared that OpenAPI Does Not Need To:**
    1.  **`<wsdl:binding>` Protocol Specs:** WSDL requires explicit protocol binding details (e.g., SOAP over HTTP using `style="document"` and explicit `soapAction` attributes). OpenAPI inherently assumes HTTP semantics.
    2.  **`<wsdl:portType>` / Abstract Interface Wrappers:** WSDL separates abstract operation signatures (`portType`) from concrete network endpoints (`port`/`service`). OpenAPI binds paths directly to HTTP methods and server base URLs without abstract interface layers.

#### Q2: Quote one soap:Fault from your Assignment 3 work and show the status code and problem body that replaced it. Why is returning that error inside a 200 OK a problem for the network in between?
*   **Assignment 3 `soap:Fault` Quote:**
    ```xml
    <soap:Envelope xmlns:soap="[http://schemas.xmlsoap.org/soap/envelope/](http://schemas.xmlsoap.org/soap/envelope/)">
      <soap:Body>
        <soap:Fault>
          <faultcode>soap:Client</faultcode>
          <faultstring>PAYMENT_DECLINED</faultstring>
          <detail>Insufficient balance in user wallet CE-STU-33217.</detail>
        </soap:Fault>
      </soap:Body>
    </soap:Envelope>
    ```
*   **Replacement HTTP Status & Problem Details Body:**
    *   **Status Code:** `422 Unprocessable Entity`
    *   **Body:**
        ```json
        {
          "type": "payment-declined",
          "title": "Unprocessable Entity",
          "status": 422,
          "detail": "Insufficient balance in user wallet CE-STU-33217."
        }
        ```
*   **Network Impact of Error inside 200 OK:** Returning business failures inside an `HTTP 200 OK` tricks middleboxes, API gateways, load balancers, and HTTP reverse caches. Caching proxies will treat the failure envelope as a successful response and cache it, serving cached "Payment Declined" errors to subsequent valid requests. Additionally, network monitoring tools (e.g., Prometheus, Datadog) fail to track real error rates because all traffic appears as successful 200 OK transport.

#### Q3: Which of UDDI's three moves (publish, find, bind) still exist in your new setup, and which disappeared? Explain what took over.
*   **Publish:** **Exists.** Developers publish contract specifications (`openapi.yaml`) to centralized developer portals, Swagger Hub, or internal service registries.
*   **Bind:** **Exists.** Clients bind to the REST API dynamically by auto-generating client SDKs or HTTP request definitions directly from the published OpenAPI specification.
*   **Find:** **Disappeared in its UDDI form.** Dynamic runtime lookup via UDDI registries (searching by business category or taxonomy at runtime) proved overly complex and fragile in distributed systems.
*   **What Took Over:** Static compile-time discovery via OpenAPI contracts paired with cloud-native runtime Service Discovery frameworks (such as Kubernetes DNS, Consul, AWS Cloud Map) or environment variable routing (`PAYMENTS_API_URL`).

#### Q4: Your XML Schema was enforced before your code ran; your OpenAPI schema is not. Name the specific function in your code that now carries that responsibility, and one failure that would get through if you had not written it.
*   **Specific Function:** `validate_order(body)` inside `app.py`.
*   **Failure that Would Get Through:** If `validate_order()` were omitted, a request with missing required payload attributes (e.g., omitting `cartId` or submitting `paymentMethod: "BITCOIN"`) would pass through HTTP parsing and trigger an unhandled internal Python `KeyError` or a database constraint crash (`500 Internal Server Error`).

#### Q5: Name one part of your service where you would still choose the SOAP stack over REST, and state exactly what guarantee you would be buying.
*   **Service Part:** Settlement and clearing interactions with external banking partners (e.g., core interbank ledger settlements).
*   **Guarantees Bought:**
    1.  **WS-AtomicTransaction:** Provides ACID transactional guarantees across distributed system boundaries (two-phase commit protocol across heterogeneous banking networks).
    2.  **WS-Security (Message-Level Security):** Guarantees end-to-end non-repudiation, field-level encryption, and digital signatures that persist across intermediate proxies and message brokers, whereas HTTPS/TLS only encrypts point-to-point transport.

---

## Part 2: Assignment 5 — HTTP Methods, Headers & Caching Strategy

### 2.1 CampusEats Method Map
| Action | HTTP Method | URL Path | Resource / Sub-Resource | Safe? | Idempotent? |
|---|---|---|---|---|---|
| Create Order | `POST` | `/orders` | Resource Collection | No | No (Made safe via `Idempotency-Key`) |
| Filter/List Orders | `GET` | `/orders?status=PLACED` | Query Filtered Collection | Yes | Yes |
| Read Order | `GET` | `/orders/{orderId}` | Individual Resource | Yes | Yes |
| Cancel Order | `POST` | `/orders/{orderId}/cancellation` | Sub-Resource Action | No | Yes (via `If-Match` ETag check) |
| Inspect Options | `OPTIONS` | `/orders` | Resource Options | Yes | Yes |

---

### 2.2 Headers Table
| Endpoint | Required Request Headers | Returned Response Headers |
|---|---|---|
| `POST /orders` | `Authorization`, `Content-Type`, `Idempotency-Key` (Optional) | `Content-Type`, `Location`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Access-Control-Allow-Origin` |
| `GET /orders` | `Authorization`, `Accept` | `Content-Type`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Access-Control-Allow-Origin` |
| `GET /orders/{orderId}` | `Authorization`, `Accept`, `If-None-Match` (Optional) | `Content-Type`, `ETag`, `Cache-Control`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Access-Control-Allow-Origin` |
| `POST /orders/{orderId}/cancellation` | `Authorization`, `Content-Type`, `If-Match` (Optional) | `Content-Type`, `ETag`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Access-Control-Allow-Origin` |
| `OPTIONS /orders` | `Origin`, `Access-Control-Request-Method` | `Allow`, `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers` |

---

### 2.3 Safe-Retry Plan
| Risky Endpoint | Risk Identified | Retry Mechanism Applied | Justification |
|---|---|---|---|
| `POST /orders` | Network disconnect after server processing leads to duplicate orders & charges. | `Idempotency-Key` Header | Server stores `Idempotency-Key` alongside result. On retry, original `201 Created` payload is returned without re-executing order placement. |
| `GET /orders/{orderId}` | Network timeout during large payload retrieval. | Natural Retry + Conditional GET (`If-None-Match`) | `GET` is inherently safe and idempotent. Using `If-None-Match` returns `304 Not Modified` if data was already cached locally. |
| `POST /orders/{orderId}/cancellation` | Concurrent cancellation attempts from multiple client devices. | Conditional Write (`If-Match` ETag) | Requires client to send last known ETag. If state was altered concurrently, server rejects retry with `412 Precondition Failed`. |

---

### 2.4 Complete HTTP Exchange Sample
```http
=== REQUEST ===
POST /orders HTTP/1.1
Host: localhost:5000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30...
Content-Type: application/json
Idempotency-Key: order-abc-123
User-Agent: curl/8.4.0
Accept: application/json

{
  "userId": "CE-STU-33217",
  "cartId": "CART-1001",
  "deliveryAddressId": "ADDR-204",
  "paymentMethod": "UPI"
}

=== RESPONSE ===
HTTP/1.1 201 CREATED
Server: Werkzeug/3.1.9 Python/3.12.10
Date: Tue, 13 Oct 2026 17:39:22 GMT
Content-Type: application/json
Content-Length: 93
Location: /orders/ORD-6B1F11
X-Content-Type-Options: nosniff
Strict-Transport-Security: max-age=31536000; includeSubDomains
Access-Control-Allow-Origin: *
Connection: close

{
  "estimatedDeliveryMinutes": 25,
  "orderId": "ORD-6B1F11",
  "status": "PLACED",
  "totalAmount": 349.0
}