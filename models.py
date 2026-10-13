import uuid

class Order:
    def __init__(self, user_id, cart_id, address_id, payment_method):
        self.id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
        self.user_id = user_id
        self.cart_id = cart_id
        self.address_id = address_id
        self.payment_method = payment_method
        self.status = "PLACED"
        self.total_amount = 349.00
        self.estimated_delivery_minutes = 25
        self.etag = str(uuid.uuid4())

    def as_json(self):
        return {
            "orderId": self.id,
            "status": self.status,
            "totalAmount": self.total_amount,
            "estimatedDeliveryMinutes": self.estimated_delivery_minutes
        }