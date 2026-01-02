"""
═══════════════════════════════════════════════════════════════════════════════
AUTUS CrewAI Driver - LLM Router
═══════════════════════════════════════════════════════════════════════════════
역할별 LLM 모델 선택 및 API 키 검증
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import yaml
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LLMTarget:
    """LLM 타겟 정보"""
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 4000
    description: str = ""


@dataclass
class RoleConfig:
    """역할 설정"""
    name: str
    llm: LLMTarget


# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER → ENV VAR MAPPING
# ─────────────────────────────────────────────────────────────────────────────

PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def load_roles_config(path: str = "llm_roles.yaml") -> dict:
    """YAML 설정 파일 로드"""
    config_path = Path(path)
    
    if not config_path.exists():
        # 기본 설정 반환
        return {
            "roles": {
                "planner": {"provider": "openai", "model": "gpt-4.1", "temperature": 0.3},
                "executor": {"provider": "openai", "model": "gpt-4.1", "temperature": 0.2},
                "reviewer": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.1},
            },
            "routing": {
                "task_profile_to_roles": {
                    "DEFAULT": ["planner", "executor", "reviewer"]
                }
            },
            "defaults": {
                "budget_usd": 5.0,
                "time_limit_seconds": 1800,
                "token_limit": 8000,
            }
        }
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_roles(task_profile: str, cfg: dict) -> List[str]:
    """태스크 프로필에 따른 역할 목록 선택"""
    routing = cfg.get("routing", {}).get("task_profile_to_roles", {})
    
    # 정확한 매칭 시도
    if task_profile in routing:
        return routing[task_profile]
    
    # 폴백: DEFAULT
    if "DEFAULT" in routing:
        return routing["DEFAULT"]
    
    # 최종 폴백
    return ["planner", "executor", "reviewer"]


def get_llm_target(role: str, cfg: dict) -> LLMTarget:
    """역할에 해당하는 LLM 타겟 반환"""
    roles_cfg = cfg.get("roles", {})
    
    if role not in roles_cfg:
        # 기본값 반환
        return LLMTarget(
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.2,
            max_tokens=4000,
            description=f"Fallback for role: {role}"
        )
    
    role_cfg = roles_cfg[role]
    return LLMTarget(
        provider=role_cfg.get("provider", "openai"),
        model=role_cfg.get("model", "gpt-4.1-mini"),
        temperature=role_cfg.get("temperature", 0.2),
        max_tokens=role_cfg.get("max_tokens", 4000),
        description=role_cfg.get("description", "")
    )


def get_role_configs(task_profile: str, cfg: dict) -> List[RoleConfig]:
    """태스크 프로필에 따른 전체 역할 설정 반환"""
    roles = pick_roles(task_profile, cfg)
    configs = []
    
    for role in roles:
        llm = get_llm_target(role, cfg)
        configs.append(RoleConfig(name=role, llm=llm))
    
    return configs


def ensure_api_key(provider: str) -> None:
    """API 키 환경변수 확인"""
    env_var = PROVIDER_ENV_VARS.get(provider.lower())
    
    if not env_var:
        raise ValueError(f"Unknown provider: {provider}")
    
    if not os.getenv(env_var):
        raise RuntimeError(f"Missing environment variable: {env_var}")


def validate_all_keys(roles: List[str], cfg: dict) -> Dict[str, bool]:
    """모든 역할의 API 키 유효성 검사"""
    results = {}
    
    for role in roles:
        llm = get_llm_target(role, cfg)
        env_var = PROVIDER_ENV_VARS.get(llm.provider.lower())
        
        if env_var:
            results[role] = bool(os.getenv(env_var))
        else:
            results[role] = False
    
    return results


def get_available_providers() -> Dict[str, bool]:
    """사용 가능한 프로바이더 목록"""
    return {
        provider: bool(os.getenv(env_var))
        for provider, env_var in PROVIDER_ENV_VARS.items()
    }


def get_defaults(cfg: dict) -> dict:
    """기본 설정값 반환"""
    return cfg.get("defaults", {
        "budget_usd": 5.0,
        "time_limit_seconds": 1800,
        "token_limit": 8000,
    })


# ─────────────────────────────────────────────────────────────────────────────
# USAGE EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 설정 로드
    cfg = load_roles_config()
    
    print("=== LLM Router Test ===\n")
    
    # 사용 가능한 프로바이더
    print("Available Providers:")
    for provider, available in get_available_providers().items():
        status = "✅" if available else "❌"
        print(f"  {status} {provider}")
    
    print()
    
    # 태스크 프로필별 역할
    profiles = ["COST_OPTIMIZATION_V1", "CONTRACT_RISK_CHECK_V1", "UNKNOWN_PROFILE"]
    
    for profile in profiles:
        print(f"Profile: {profile}")
        roles = pick_roles(profile, cfg)
        print(f"  Roles: {roles}")
        
        for role in roles:
            llm = get_llm_target(role, cfg)
            print(f"    {role}: {llm.provider}/{llm.model}")
        print()
