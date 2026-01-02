# backend/autosync/registry/crm.py
# CRM 시스템 매핑

CRM_SYSTEMS = {
    "hubspot": {
        "name": "HubSpot",
        "detection": {
            "cookies": ["hubspotutk", "__hstc"],
            "domains": ["hubspot.com", "api.hubapi.com"]
        },
        "mapping": {
            "node_id": ["properties.hs_contact_id", "id"],
            "value": ["properties.hs_deal_amount", "amount"],
            "timestamp": ["properties.createdate"]
        },
        "webhook_events": ["contact.creation", "deal.creation"]
    },
    
    "salesforce": {
        "name": "Salesforce",
        "detection": {
            "cookies": ["sfdc_"],
            "domains": ["salesforce.com", "force.com"]
        },
        "mapping": {
            "node_id": ["AccountId", "Id"],
            "value": ["Amount"],
            "timestamp": ["CreatedDate"]
        }
    },
    
    "zoho": {
        "name": "Zoho CRM",
        "detection": {
            "domains": ["zoho.com", "crm.zoho.com"]
        },
        "mapping": {
            "node_id": ["Contact_Id"],
            "value": ["Amount"],
            "timestamp": ["Created_Time"]
        }
    },
    
    "pipedrive": {
        "name": "Pipedrive",
        "detection": {
            "domains": ["pipedrive.com"]
        },
        "mapping": {
            "node_id": ["person_id", "org_id"],
            "value": ["value", "amount"],
            "timestamp": ["add_time"]
        }
    }
}
