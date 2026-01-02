# backend/autosync/registry/payment.py
# 결제 시스템 매핑

PAYMENT_SYSTEMS = {
    "stripe": {
        "name": "Stripe",
        "detection": {
            "cookies": ["__stripe_mid", "__stripe_sid"],
            "domains": ["stripe.com", "js.stripe.com"],
            "api_patterns": ["sk_live_", "sk_test_"]
        },
        "mapping": {
            "node_id": ["customer", "id"],
            "value": ["amount", 100],
            "timestamp": ["created"]
        },
        "webhook_events": ["payment_intent.succeeded", "charge.refunded"]
    },
    
    "toss": {
        "name": "토스페이먼츠",
        "detection": {
            "cookies": ["toss_"],
            "domains": ["pay.toss.im", "api.tosspayments.com"],
            "api_patterns": ["test_sk_", "live_sk_"]
        },
        "mapping": {
            "node_id": ["orderId"],
            "value": ["totalAmount", 1],
            "timestamp": ["approvedAt"]
        },
        "webhook_events": ["DONE", "CANCELED"]
    },
    
    "kakaopay": {
        "name": "카카오페이",
        "detection": {
            "cookies": ["kakao_"],
            "domains": ["kapi.kakao.com", "online-pay.kakao.com"]
        },
        "mapping": {
            "node_id": ["partner_user_id"],
            "value": ["amount.total", 1],
            "timestamp": ["approved_at"]
        }
    },
    
    "shopify": {
        "name": "Shopify",
        "detection": {
            "cookies": ["_shopify_"],
            "domains": ["myshopify.com", "shopify.com"]
        },
        "mapping": {
            "node_id": ["customer.id", "id"],
            "value": ["total_price", 1],
            "timestamp": ["created_at"]
        },
        "webhook_events": ["orders/create", "orders/paid"]
    }
}
