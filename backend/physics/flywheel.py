#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                    🔄 AUTUS PILLAR 1: Flywheel Engine                                     ║
║                                                                                           ║
║  목적: Bezos Flywheel - 자가 강화 성장 루프                                                ║
║                                                                                           ║
║  핵심 개념:                                                                                ║
║  비전 → 투자 → 성장 → 수익 → 재투자 → 더 큰 성장 (무한 루프)                               ║
║                                                                                           ║
║  계산:                                                                                     ║
║  - Flywheel Velocity: 루프 회전 속도                                                       ║
║  - Flywheel Momentum: 누적 관성                                                            ║
║  - Reinvestment Ratio: 재투자 비율                                                         ║
║                                                                                           ║
║  ⚠️ 기존 PIPELINE v1.3 LOCK 영향 없음 - 독립 모듈                                          ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Flywheel 단계 정의
# ═══════════════════════════════════════════════════════════════════════════════════════════

FLYWHEEL_STAGES = [
    "INVEST",      # 투자 (시간/돈/노력)
    "GROW",        # 성장 (고객/매출 증가)
    "PROFIT",      # 수익 (순이익)
    "REINVEST",    # 재투자 (다시 투자)
]

# 이벤트 타입 → Flywheel 단계 매핑
EVENT_TO_STAGE = {
    # INVEST 단계
    "COST_SAVED": "INVEST",      # 비용 절감 = 투자 여력
    
    # GROW 단계
    "CONTRACT_SIGNED": "GROW",   # 계약 = 성장
    "REFERRAL_TO_CONTRACT": "GROW",
    
    # PROFIT 단계
    "CASH_IN": "PROFIT",         # 현금 유입 = 수익
    "MRR": "PROFIT",             # 반복 수익 = 수익
    "INVEST_CONFIRMED": "PROFIT",
    
    # REINVEST 단계 (별도 추적)
    "DELIVERY_COMPLETE": "REINVEST",  # 완료 = 다음 투자 준비
    "INVOICE_ISSUED": "REINVEST",
}


@dataclass
class FlywheelState:
    """Flywheel 현재 상태"""
    week_id: str
    invest_krw: float = 0.0
    grow_krw: float = 0.0
    profit_krw: float = 0.0
    reinvest_krw: float = 0.0
    
    @property
    def total_flow(self) -> float:
        """전체 흐름"""
        return self.invest_krw + self.grow_krw + self.profit_krw + self.reinvest_krw
    
    @property
    def velocity(self) -> float:
        """
        Flywheel 속도 = 각 단계 균형도
        
        모든 단계가 균등하면 속도 최대 (1.0)
        한 단계만 있으면 속도 최소 (0.25)
        """
        stages = [self.invest_krw, self.grow_krw, self.profit_krw, self.reinvest_krw]
        total = sum(stages)
        if total <= 0:
            return 0.0
        
        # 엔트로피 기반 균형도
        ratios = [s / total for s in stages if s > 0]
        if not ratios:
            return 0.0
        
        # 완벽 균형 = 0.25씩 = 엔트로피 최대
        entropy = -sum(r * np.log(r + 1e-9) for r in ratios)
        max_entropy = np.log(4)  # 4단계 균등
        
        return entropy / max_entropy
    
    @property
    def reinvestment_ratio(self) -> float:
        """재투자 비율 = reinvest / profit"""
        if self.profit_krw <= 0:
            return 0.0
        return self.reinvest_krw / self.profit_krw
    
    @property
    def stage_status(self) -> str:
        """현재 주력 단계"""
        stages = {
            "INVEST": self.invest_krw,
            "GROW": self.grow_krw,
            "PROFIT": self.profit_krw,
            "REINVEST": self.reinvest_krw,
        }
        if max(stages.values()) <= 0:
            return "IDLE"
        return max(stages, key=stages.get)


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Flywheel 계산
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_flywheel_state(
    money_events: pd.DataFrame,
    week_id: str = None
) -> FlywheelState:
    """
    이벤트에서 Flywheel 상태 계산
    
    PIPELINE의 money_events를 받아서 각 단계별 금액 집계
    """
    if money_events.empty:
        return FlywheelState(week_id=week_id or "")
    
    # 이벤트 타입 → 단계 매핑
    df = money_events.copy()
    df["flywheel_stage"] = df["event_type"].map(EVENT_TO_STAGE).fillna("UNKNOWN")
    
    # 단계별 집계
    stage_sum = df.groupby("flywheel_stage")["amount_krw"].sum().to_dict()
    
    return FlywheelState(
        week_id=week_id or "",
        invest_krw=stage_sum.get("INVEST", 0),
        grow_krw=stage_sum.get("GROW", 0),
        profit_krw=stage_sum.get("PROFIT", 0),
        reinvest_krw=stage_sum.get("REINVEST", 0),
    )


def compute_flywheel_momentum(
    history: List[FlywheelState],
    decay: float = 0.9
) -> Dict:
    """
    Flywheel 모멘텀 계산 (누적 관성)
    
    과거 속도의 지수 가중 평균
    decay가 높을수록 관성이 오래 유지
    """
    if not history:
        return {
            "momentum": 0.0,
            "trend": "STARTING",
            "weeks_accelerating": 0,
        }
    
    # 지수 가중 평균
    weights = [decay ** i for i in range(len(history))]
    weights = weights[::-1]  # 최근 것에 더 높은 가중치
    total_weight = sum(weights)
    
    momentum = sum(
        h.velocity * w
        for h, w in zip(history, weights)
    ) / total_weight
    
    # 트렌드 판단
    if len(history) >= 2:
        recent = history[-1].velocity
        prev = history[-2].velocity
        if recent > prev * 1.1:
            trend = "ACCELERATING"
        elif recent < prev * 0.9:
            trend = "DECELERATING"
        else:
            trend = "STEADY"
    else:
        trend = "STARTING"
    
    # 연속 가속 주차 수
    weeks_acc = 0
    for i in range(len(history) - 1, 0, -1):
        if history[i].velocity > history[i-1].velocity:
            weeks_acc += 1
        else:
            break
    
    return {
        "momentum": momentum,
        "trend": trend,
        "weeks_accelerating": weeks_acc,
        "current_velocity": history[-1].velocity if history else 0,
    }


def compute_flywheel_score(state: FlywheelState, momentum: Dict) -> Dict:
    """
    Flywheel 종합 점수
    
    점수 = velocity × 0.4 + reinvestment_ratio × 0.3 + momentum × 0.3
    """
    velocity = state.velocity
    reinvest = min(1.0, state.reinvestment_ratio)  # cap at 1.0
    mom = momentum.get("momentum", 0)
    
    score = velocity * 0.4 + reinvest * 0.3 + mom * 0.3
    
    # 상태 판단
    if score >= 0.7:
        status = "SPINNING_FAST"
        advice = "Flywheel 고속 회전 중. 유지하세요."
    elif score >= 0.5:
        status = "GAINING_SPEED"
        advice = "속도 붙는 중. 재투자 비율 높이세요."
    elif score >= 0.3:
        status = "SLOW"
        advice = "느림. 병목 단계를 찾아 해결하세요."
    else:
        status = "STUCK"
        advice = "정체. 전 단계 점검 필요."
    
    # 병목 찾기
    stages = {
        "INVEST": state.invest_krw,
        "GROW": state.grow_krw,
        "PROFIT": state.profit_krw,
        "REINVEST": state.reinvest_krw,
    }
    total = sum(stages.values())
    if total > 0:
        ratios = {k: v / total for k, v in stages.items()}
        bottleneck = min(ratios, key=ratios.get)
    else:
        bottleneck = "ALL"
    
    return {
        "flywheel_score": score,
        "velocity": velocity,
        "reinvestment_ratio": state.reinvestment_ratio,
        "momentum": mom,
        "status": status,
        "advice": advice,
        "bottleneck": bottleneck,
        "stage_status": state.stage_status,
    }


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Flywheel 예측
# ═══════════════════════════════════════════════════════════════════════════════════════════

def project_flywheel_growth(
    current_state: FlywheelState,
    weeks_ahead: int = 12,
    growth_rate: float = 0.05,
    reinvest_rate: float = 0.3
) -> List[Dict]:
    """
    Flywheel 성장 예측
    
    복리 효과: 재투자 → 성장 가속
    """
    projections = []
    
    profit = current_state.profit_krw
    velocity = current_state.velocity
    
    for week in range(1, weeks_ahead + 1):
        # 재투자 효과
        reinvest = profit * reinvest_rate
        
        # 성장률 (재투자에 비례해서 증가)
        effective_growth = growth_rate * (1 + reinvest_rate)
        
        # 다음 주 수익 예측
        profit = profit * (1 + effective_growth)
        
        # 속도도 점진 증가
        velocity = min(1.0, velocity * 1.02)
        
        projections.append({
            "week": week,
            "projected_profit": profit,
            "projected_velocity": velocity,
            "cumulative_growth": ((profit / current_state.profit_krw) - 1) * 100 if current_state.profit_krw > 0 else 0,
        })
    
    return projections


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 통합 함수
# ═══════════════════════════════════════════════════════════════════════════════════════════

def analyze_flywheel(
    money_events: pd.DataFrame,
    history: List[FlywheelState] = None,
    week_id: str = None
) -> Dict:
    """
    Flywheel 전체 분석
    
    PIPELINE 실행 후 호출하면 됨
    """
    # 현재 상태
    state = compute_flywheel_state(money_events, week_id)
    
    # 모멘텀 (이력 필요)
    if history is None:
        history = []
    history_with_current = history + [state]
    momentum = compute_flywheel_momentum(history_with_current)
    
    # 종합 점수
    score = compute_flywheel_score(state, momentum)
    
    # 예측
    projection = project_flywheel_growth(state, weeks_ahead=12)
    
    return {
        "state": {
            "invest_krw": state.invest_krw,
            "grow_krw": state.grow_krw,
            "profit_krw": state.profit_krw,
            "reinvest_krw": state.reinvest_krw,
            "total_flow": state.total_flow,
        },
        "score": score,
        "momentum": momentum,
        "projection_12w": projection[-1] if projection else None,
    }
