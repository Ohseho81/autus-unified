# backend/autosync/registry/others.py
# 예약/POS/회계 시스템 매핑

BOOKING_SYSTEMS = {
    "naver_booking": {
        "name": "네이버예약",
        "detection": {
            "domains": ["booking.naver.com"]
        },
        "mapping": {
            "node_id": ["booking_id", "customer_id"],
            "value": ["total_price"],
            "timestamp": ["booking_date"]
        }
    },
    
    "table_manager": {
        "name": "테이블매니저",
        "detection": {
            "domains": ["tablemanager.io"]
        },
        "mapping": {
            "node_id": ["guest_id"],
            "value": ["deposit"],
            "timestamp": ["reservation_time"]
        }
    }
}

POS_SYSTEMS = {
    "toss_pos": {
        "name": "토스 POS",
        "detection": {
            "domains": ["toss.im/pos"]
        },
        "mapping": {
            "node_id": ["order_id"],
            "value": ["total"],
            "timestamp": ["paid_at"]
        }
    },
    
    "baemin_pos": {
        "name": "배민포스",
        "detection": {
            "domains": ["ceo.baemin.com"]
        },
        "mapping": {
            "node_id": ["order_no"],
            "value": ["order_amount"],
            "timestamp": ["order_time"]
        }
    }
}

ACCOUNTING_SYSTEMS = {
    "quickbooks": {
        "name": "QuickBooks",
        "detection": {
            "domains": ["quickbooks.intuit.com"]
        },
        "mapping": {
            "node_id": ["CustomerRef.value"],
            "value": ["TotalAmt"],
            "timestamp": ["TxnDate"]
        }
    },
    
    "xero": {
        "name": "Xero",
        "detection": {
            "domains": ["xero.com", "api.xero.com"]
        },
        "mapping": {
            "node_id": ["ContactID"],
            "value": ["Total"],
            "timestamp": ["Date"]
        }
    }
}
