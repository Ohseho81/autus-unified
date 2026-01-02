# backend/autosync/n8n_generator.py
# n8n 워크플로우 생성 (간소화)

from typing import Dict
import json


def generate_workflow(system_id: str, name: str, mapping: Dict) -> Dict:
    """n8n 워크플로우 JSON 생성"""
    
    # 매핑에서 코드 생성
    id_paths = mapping.get("node_id", ["id"])
    if isinstance(id_paths, list):
        id_code = " || ".join([f"data.{p}" for p in id_paths])
    else:
        id_code = f"data.{id_paths}"
    
    val_cfg = mapping.get("value", ["amount", 1])
    val_path = val_cfg[0] if isinstance(val_cfg, list) else val_cfg
    divisor = val_cfg[1] if isinstance(val_cfg, list) and len(val_cfg) > 1 else 1
    
    code = f'''const data = $input.item.json.body || $input.item.json;
const FORBIDDEN = ['name','email','phone','description'];
FORBIDDEN.forEach(f => delete data[f]);
const nodeId = String({id_code} || 'anon');
const value = parseFloat(data.{val_path} || 0) / {divisor};
const event = (data.type || data.event || '').toLowerCase();
const flowType = event.includes('refund') ? 'outflow' : 'inflow';
return [{{ json: {{ node_id: nodeId, value, flow_type: flowType, source: '{system_id}' }} }}];'''
    
    return {
        "name": f"AUTUS - {name}",
        "nodes": [
            {
                "parameters": {"httpMethod": "POST", "path": f"autosync-{system_id}"},
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "position": [250, 300]
            },
            {
                "parameters": {"functionCode": code},
                "name": "Transform",
                "type": "n8n-nodes-base.function",
                "position": [450, 300]
            }
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Transform", "type": "main", "index": 0}]]}
        }
    }


def save_workflow(workflow: Dict, path: str):
    """JSON 파일로 저장"""
    with open(path, 'w') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
