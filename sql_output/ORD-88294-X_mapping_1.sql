INSERT INTO "my_catalog"."my_schema"."order_header" ("currency", "customer_id", "discount_total", "email", "first_name", "full_name", "grand_total", "last_name", "order_date", "order_id", "order_lifecycle_event", "order_status", "phone", "shipping_total", "subtotal", "tax_total")
VALUES
    ('USD', 'CUST-4052', -50.0, 'alex.smith@example.com', 'Alex', 'Alex Smith', 475.6, 'Smith', '2023-10-27T14:30:00Z', 'ORD-88294-X', 'order_created', 'CREATED', '+1-555-010-9988', 15.0, 475.0, 35.6);
INSERT INTO "my_catalog"."my_schema"."order_item" ("item_type", "line_number", "line_total", "order_id", "product_name", "quantity", "sku", "unit_price")
VALUES
    ('SINGLE', 1, 165.0, 'ORD-88294-X', 'Premium Cotton Shirt - Blue/Large', 3, 'SKU-SHIRT-BLUE-L', 55.0),
    ('BUNDLE', 2, 240.0, 'ORD-88294-X', 'Fitness Starter Pack', 2, 'SKU-BNDL-GYM-SET', 120.0),
    ('SINGLE', 3, 70.0, 'ORD-88294-X', 'Midnight Edition Analog Watch', 1, 'SKU-WATCH-BLK', 70.0);
INSERT INTO "my_catalog"."my_schema"."order_item_component" ("component_name", "component_sku", "internal_cost_allocation", "line_number", "order_id", "quantity", "sku")
VALUES
    ('Eco-Friendly Yoga Mat', 'SKU-MAT-01', 70.0, 2, 'ORD-88294-X', 2, 'SKU-BNDL-GYM-SET'),
    ('Insulated Water Bottle', 'SKU-BTL-05', 50.0, 2, 'ORD-88294-X', 2, 'SKU-BNDL-GYM-SET');
INSERT INTO "my_catalog"."my_schema"."payment" ("amount", "auth_code", "card_type", "last_four", "payment_method", "payment_status")
VALUES
    (425.6, 'AUTH998822', 'MASTERCARD', '1234', 'CREDIT_CARD', 'AUTHORIZED');
INSERT INTO "my_catalog"."my_schema"."payment" ("amount", "coupon_code", "payment_method", "payment_status", "promotion_id")
VALUES
    (50.0, 'BOGO50', 'DISCOUNT_COUPON', 'APPLIED', 'BUNDLE_PROMO_2023');
INSERT INTO "my_catalog"."my_schema"."order_shipping" ("city", "country", "first_name", "last_name", "order_id", "postal_code", "state", "street")
VALUES
    ('Springfield', 'US', 'Alex', 'Smith', 'ORD-88294-X', '62704', 'IL', '123 Maple Avenue');
