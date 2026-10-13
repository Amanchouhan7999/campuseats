# In-memory storage for orders
orders_db = {}

# In-memory storage for idempotency keys to safely replay identical requests
idempotency_store = {}