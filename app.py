<<<<<<< HEAD
from flask import Flask, request, jsonify, make_response
from models import Order
from store import orders_db, idempotency_store
from errors import problem
import uuid
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

app = Flask(__name__)

def validate_order(body):
    errors = []
    required_fields = ["userId", "cartId", "deliveryAddressId", "paymentMethod"]
    for field in required_fields:
        if field not in body or not str(body[field]).strip():
            errors.append({"field": field, "message": f"'{field}' is required"})
    
    if "paymentMethod" in body and body["paymentMethod"] not in ["UPI", "CARD", "WALLET"]:
        errors.append({"field": "paymentMethod", "message": "paymentMethod must be UPI, CARD, or WALLET"})
        
    return errors

@app.before_request
def check_auth_and_accept():
    if request.method not in ["OPTIONS"] and not request.headers.get("Authorization"):
        return problem("unauthorized", "Unauthorized", 401, "Missing or invalid Bearer token.")
    
    if request.headers.get("Accept") and "application/xml" in request.headers.get("Accept"):
        return problem("not-acceptable", "Not Acceptable", 406, "XML is not supported.")

@app.after_request
def set_global_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Access-Control-Allow-Origin'] = '*'
    if response.status_code != 204 and not response.headers.get('Content-Type'):
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response

@app.route('/orders', methods=['POST', 'OPTIONS'])
def create_order():
    if request.method == 'OPTIONS':
        res = make_response()
        res.headers['Allow'] = 'OPTIONS, POST, GET'
        return res

    idempotency_key = request.headers.get('Idempotency-Key')
    if idempotency_key and idempotency_key in idempotency_store:
        cached_response = idempotency_store[idempotency_key]
        return jsonify(cached_response), 201, {'Location': f'/orders/{cached_response["orderId"]}'}

    body = request.get_json(silent=True)
    if body is None:
        return problem("malformed-request", "Bad Request", 400, "Invalid JSON body.")

    validation_errors = validate_order(body)
    if validation_errors:
        return problem("validation-error", "Unprocessable Entity", 422, "Field validation failed.", validation_errors)

    # Create new order matching OpenAPI schema
    new_order = Order(
        user_id=body["userId"],
        cart_id=body["cartId"],
        address_id=body["deliveryAddressId"],
        payment_method=body["paymentMethod"]
    )
    orders_db[new_order.id] = new_order

    # Resilient outbound call
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retry))
    payment_url = os.environ.get('PAYMENTS_API_URL', 'http://localhost:5001/charge')
    try:
        session.post(payment_url, json={"amount": 349.00}, timeout=2.0)
    except requests.exceptions.RequestException:
        pass

    response_body = new_order.as_json()
    if idempotency_key:
        idempotency_store[idempotency_key] = response_body

    return jsonify(response_body), 201, {'Location': f'/orders/{new_order.id}'}

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    order = orders_db.get(order_id)
    if not order:
        return problem("order-not-found", "Not Found", 404, f"Order {order_id} does not exist.")

    if request.headers.get('If-None-Match') == order.etag:
        return '', 304

    response = make_response(jsonify(order.as_json()), 200)
    response.headers['ETag'] = order.etag
    response.headers['Cache-Control'] = 'public, max-age=60'
    return response

@app.route('/orders/<order_id>/cancellation', methods=['POST'])
def cancel_order(order_id):
    order = orders_db.get(order_id)
    if not order:
        return problem("order-not-found", "Not Found", 404, f"Order {order_id} does not exist.")

    if request.headers.get('If-Match') and request.headers.get('If-Match') != order.etag:
        return problem("precondition-failed", "Precondition Failed", 412, "ETag mismatch.")

    body = request.get_json(silent=True) or {}
    if "reason" not in body:
        return problem("validation-error", "Unprocessable Entity", 422, "Reason is required.", [{"field": "reason", "message": "'reason' is required"}])

    if order.status == "CANCELLED":
        return problem("illegal-transition", "Conflict", 409, "Order is already cancelled.")

    order.status = "CANCELLED"
    order.etag = str(uuid.uuid4())
    
    return jsonify({
        "orderId": order.id,
        "status": "CANCELLED",
        "refundInitiated": True
    }), 200

if __name__ == '__main__':
    app.run(port=5000)
=======
import hashlib
from flask import request, jsonify, Response

# --- Caching & Idempotency Helpers ---

idempotency_cache = {}

def generate_etag(data_dict):
    """Generate an MD5 hash of the dictionary to use as an ETag."""
    # Ensure stable sorting so identical dictionaries produce the same hash
    data_string = str(sorted(data_dict.items())).encode('utf-8')
    return hashlib.md5(data_string).hexdigest()


# --- Route Implementations ---

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    order = store.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
        
    current_etag = generate_etag(order)
    client_etag = request.headers.get('If-None-Match')
    
    # Return 304 if the client already has the latest version
    if client_etag == current_etag:
        return Response(status=304)
        
    response = jsonify(order)
    response.headers['ETag'] = current_etag
    return response, 200


@app.route('/orders/<order_id>', methods=['PUT'])
def update_order(order_id):
    order = store.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    current_etag = generate_etag(order)
    client_etag = request.headers.get('If-Match')

    # Return 412 if the client is trying to update an outdated version
    if client_etag and client_etag != current_etag:
        return jsonify({"error": "Precondition Failed: ETag mismatch"}), 412

    update_data = request.json
    updated_order = store.update_order(order_id, update_data)
    
    new_etag = generate_etag(updated_order)
    response = jsonify(updated_order)
    response.headers['ETag'] = new_etag
    return response, 200


@app.route('/orders', methods=['POST'])
def create_order():
    idempotency_key = request.headers.get('Idempotency-Key')
    
    # Check for a cached response using the Idempotency-Key
    if idempotency_key and idempotency_key in idempotency_cache:
        cached = idempotency_cache[idempotency_key]
        return jsonify(cached['body']), cached['status']

    order_data = request.json
    new_order = store.create_order(order_data)
    
    # Cache the successful response to prevent future duplicates
    if idempotency_key:
        idempotency_cache[idempotency_key] = {
            'body': new_order,
            'status': 201
        }
        
    return jsonify(new_order), 201
>>>>>>> ff9ff9fc84cb723a73cc4e7b6420825c544d8720
