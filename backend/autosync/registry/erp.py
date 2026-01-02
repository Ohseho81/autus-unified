# backend/autosync/registry/erp.py
# 교육/스포츠 ERP 시스템 매핑

ERP_SYSTEMS = {
    "highclass": {
        "name": "하이클래스",
        "detection": {
            "cookies": ["HIGHCLASS_"],
            "domains": ["highclass.com", "api.highclass.com"]
        },
        "mapping": {
            "node_id": ["student_id", "member_id"],
            "value": ["payment", "tuition", "amount"],
            "timestamp": ["created_at"]
        },
        "webhook_events": ["student.created", "payment.success"]
    },
    
    "class101": {
        "name": "클래스101",
        "detection": {
            "cookies": ["class101_"],
            "domains": ["class101.net", "api.class101.net"]
        },
        "mapping": {
            "node_id": ["customer.id", "user_id"],
            "value": ["order.amount", "price"],
            "timestamp": ["purchased_at"]
        }
    },
    
    "academy_plus": {
        "name": "아카데미플러스",
        "detection": {
            "domains": ["academyplus.co.kr"]
        },
        "mapping": {
            "node_id": ["member_no"],
            "value": ["pay_amount"],
            "timestamp": ["pay_date"]
        }
    },
    
    "classmate": {
        "name": "클래스메이트",
        "detection": {
            "domains": ["classmate.co.kr"]
        },
        "mapping": {
            "node_id": ["student_id"],
            "value": ["tuition"],
            "timestamp": ["reg_date"]
        }
    },
    
    "gymbox": {
        "name": "짐박스",
        "detection": {
            "domains": ["gymbox.co.kr"]
        },
        "mapping": {
            "node_id": ["member_id"],
            "value": ["membership_fee"],
            "timestamp": ["join_date"]
        }
    }
}
