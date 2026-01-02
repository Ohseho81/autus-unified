#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                    🧬 AUTUS PIPELINE v1.3 FINAL - Synergy                                 ║
║                                                                                           ║
║  v1.1 업그레이드:                                                                          ║
║  ✅ SOLO baseline 기반 uplift 계산                                                         ║
║  ✅ Group Synergy (k=3~4) 추가                                                             ║
║                                                                                           ║
║  v1.2 업그레이드:                                                                          ║
║  ✅ 파티션 기반 계산 (customer_id, project_id)                                             ║
║                                                                                           ║
║  v1.3 업그레이드:                                                                          ║
║  ✅ 프로젝트 가중치 기반 시너지 합산                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import itertools
from typing import Dict, Tuple, Optional
from .config import CFG


# ═══════════════════════════════════════════════════════════════════════════════════════════
# v1.0: Basic Pair Coin Rate (Deprecated)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_pair_synergy_v0(money: pd.DataFrame) -> pd.DataFrame:
    """v0: 단순 Pair Coin Rate 계산 (deprecated)"""
    ev = money[["event_id", "people_tags", "amount_krw", "effective_minutes"]].drop_duplicates()
    rows = []
    
    for _, r in ev.iterrows():
        tags = [t.strip() for t in str(r["people_tags"]).split(";") if t.strip()]
        if len(tags) < 2:
            continue
        
        for i, j in itertools.combinations(sorted(tags), 2):
            rows.append({
                "i": i,
                "j": j,
                "event_id": r["event_id"],
                "amount_krw": float(r["amount_krw"]),
                "minutes": float(r["effective_minutes"]),
            })
    
    if not rows:
        return pd.DataFrame(columns=["i", "j", "pair_coin_rate_per_min", "pair_coin_rate_per_hr", "events"])
    
    df = pd.DataFrame(rows)
    g = df.groupby(["i", "j"], as_index=False).agg(
        amount_krw=("amount_krw", "sum"),
        minutes=("minutes", "sum"),
        events=("event_id", "nunique"),
    )
    
    g["pair_coin_rate_per_min"] = g["amount_krw"] / (g["minutes"] + 1e-9)
    g["pair_coin_rate_per_hr"] = g["pair_coin_rate_per_min"] * 60.0
    
    return g


# ═══════════════════════════════════════════════════════════════════════════════════════════
# v1.1: Pair Synergy Uplift (SOLO baseline)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_pair_synergy_uplift(money: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """
    v1.1: Pair Synergy Uplift 계산
    
    uplift = EventRate - (BaseRate_i + BaseRate_j) / 2
    
    입력:
    - money: 비폭발 이벤트 (unique event rows)
    - baseline: [person_id, base_rate_per_min]
    
    출력:
    - i, j, synergy_uplift_per_min, synergy_uplift_per_hr, events, minutes
    """
    base = baseline.set_index("person_id")["base_rate_per_min"].to_dict()
    
    ev = money[["event_id", "people_tags", "amount_krw", "effective_minutes"]].drop_duplicates()
    rows = []
    
    for _, r in ev.iterrows():
        tags = [t.strip() for t in str(r["people_tags"]).split(";") if t.strip()]
        if len(tags) != 2:  # pair only
            continue
        
        event_rate = float(r["amount_krw"]) / (float(r["effective_minutes"]) + 1e-9)
        
        for i, j in itertools.combinations(sorted(tags), 2):
            bi = float(base.get(i, 0.0))
            bj = float(base.get(j, 0.0))
            baseline_avg = (bi + bj) / 2.0
            uplift = event_rate - baseline_avg
            
            rows.append({
                "i": i,
                "j": j,
                "event_id": r["event_id"],
                "uplift_per_min": uplift,
                "minutes": float(r["effective_minutes"]),
            })
    
    if not rows:
        return pd.DataFrame(columns=["i", "j", "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"])
    
    df = pd.DataFrame(rows)
    df["uplift_weighted"] = df["uplift_per_min"] * df["minutes"]
    
    g = df.groupby(["i", "j"], as_index=False).agg(
        uplift_sum=("uplift_weighted", "sum"),
        minutes=("minutes", "sum"),
        events=("event_id", "nunique"),
    )
    g["synergy_uplift_per_min"] = g["uplift_sum"] / (g["minutes"] + 1e-9)
    g["synergy_uplift_per_hr"] = g["synergy_uplift_per_min"] * 60.0
    
    return g[["i", "j", "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"]]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# v1.1: Group Synergy Uplift (k=3~4)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_group_synergy_uplift(
    money: pd.DataFrame,
    baseline: pd.DataFrame,
    k_min: int = 3,
    k_max: int = 4
) -> pd.DataFrame:
    """
    v1.1: Group Synergy Uplift (k=3..k_max) 계산
    
    uplift = EventRate - (Σ BaseRate_i) / k
    
    출력:
    - group_key: "P01;P03;P07" (sorted)
    - k: 그룹 크기
    - synergy_uplift_per_min
    - synergy_uplift_per_hr
    - events
    - minutes
    """
    base = baseline.set_index("person_id")["base_rate_per_min"].to_dict()
    
    ev = money[["event_id", "people_tags", "amount_krw", "effective_minutes"]].drop_duplicates()
    rows = []
    
    for _, r in ev.iterrows():
        tags = [t.strip() for t in str(r["people_tags"]).split(";") if t.strip()]
        k = len(tags)
        if k < k_min or k > k_max:
            continue
        
        tags_sorted = sorted(tags)
        group_key = ";".join(tags_sorted)
        
        event_rate = float(r["amount_krw"]) / (float(r["effective_minutes"]) + 1e-9)
        base_rate = sum(float(base.get(pid, 0.0)) for pid in tags_sorted) / float(k)
        
        uplift = event_rate - base_rate
        minutes = float(r["effective_minutes"])
        
        rows.append({
            "group_key": group_key,
            "k": k,
            "event_id": r["event_id"],
            "uplift_per_min": uplift,
            "minutes": minutes
        })
    
    if not rows:
        return pd.DataFrame(columns=["group_key", "k", "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"])
    
    df = pd.DataFrame(rows)
    df["uplift_weighted"] = df["uplift_per_min"] * df["minutes"]
    
    g = df.groupby(["group_key", "k"], as_index=False).agg(
        uplift_sum=("uplift_weighted", "sum"),
        minutes=("minutes", "sum"),
        events=("event_id", "nunique"),
    )
    g["synergy_uplift_per_min"] = g["uplift_sum"] / (g["minutes"] + 1e-9)
    g["synergy_uplift_per_hr"] = g["synergy_uplift_per_min"] * 60.0
    
    return g[["group_key", "k", "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"]]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# v1.2: Partitioned Pair Synergy (by customer_id, project_id)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_pair_synergy_uplift_partitioned(money: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    """
    v1.2: 파티션 기반 Pair Synergy Uplift
    
    파티션: (customer_id, project_id)
    """
    base = baseline.set_index("person_id")["base_rate_per_min"].to_dict()
    
    ev = money[["event_id", "customer_id", "project_id", "people_tags", "amount_krw", "effective_minutes"]].drop_duplicates()
    rows = []
    
    for _, r in ev.iterrows():
        tags = [t.strip() for t in str(r["people_tags"]).split(";") if t.strip()]
        if len(tags) != 2:
            continue
        
        part = (str(r["customer_id"]), str(r["project_id"]))
        event_rate = float(r["amount_krw"]) / (float(r["effective_minutes"]) + 1e-9)
        
        for i, j in itertools.combinations(sorted(tags), 2):
            bi = float(base.get(i, 0.0))
            bj = float(base.get(j, 0.0))
            uplift = event_rate - (bi + bj) / 2.0
            
            rows.append({
                "customer_id": part[0],
                "project_id": part[1],
                "i": i,
                "j": j,
                "event_id": r["event_id"],
                "uplift_per_min": uplift,
                "minutes": float(r["effective_minutes"]),
            })
    
    if not rows:
        return pd.DataFrame(columns=[
            "customer_id", "project_id", "i", "j",
            "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"
        ])
    
    df = pd.DataFrame(rows)
    df["uplift_weighted"] = df["uplift_per_min"] * df["minutes"]
    
    g = df.groupby(["customer_id", "project_id", "i", "j"], as_index=False).agg(
        uplift_sum=("uplift_weighted", "sum"),
        minutes=("minutes", "sum"),
        events=("event_id", "nunique"),
    )
    g["synergy_uplift_per_min"] = g["uplift_sum"] / (g["minutes"] + 1e-9)
    g["synergy_uplift_per_hr"] = g["synergy_uplift_per_min"] * 60.0
    
    return g[["customer_id", "project_id", "i", "j", "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"]]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# v1.2: Partitioned Group Synergy (by customer_id, project_id)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_group_synergy_uplift_partitioned(
    money: pd.DataFrame,
    baseline: pd.DataFrame,
    k_min: int = 3,
    k_max: int = 4
) -> pd.DataFrame:
    """
    v1.2: 파티션 기반 Group Synergy Uplift
    
    파티션: (customer_id, project_id)
    """
    base = baseline.set_index("person_id")["base_rate_per_min"].to_dict()
    
    ev = money[["event_id", "customer_id", "project_id", "people_tags", "amount_krw", "effective_minutes"]].drop_duplicates()
    rows = []
    
    for _, r in ev.iterrows():
        tags = [t.strip() for t in str(r["people_tags"]).split(";") if t.strip()]
        k = len(tags)
        if k < k_min or k > k_max:
            continue
        
        part = (str(r["customer_id"]), str(r["project_id"]))
        tags_sorted = sorted(tags)
        group_key = ";".join(tags_sorted)
        
        event_rate = float(r["amount_krw"]) / (float(r["effective_minutes"]) + 1e-9)
        base_rate = sum(float(base.get(pid, 0.0)) for pid in tags_sorted) / float(k)
        
        uplift = event_rate - base_rate
        minutes = float(r["effective_minutes"])
        
        rows.append({
            "customer_id": part[0],
            "project_id": part[1],
            "group_key": group_key,
            "k": k,
            "event_id": r["event_id"],
            "uplift_per_min": uplift,
            "minutes": minutes
        })
    
    if not rows:
        return pd.DataFrame(columns=[
            "customer_id", "project_id", "group_key", "k",
            "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"
        ])
    
    df = pd.DataFrame(rows)
    df["uplift_weighted"] = df["uplift_per_min"] * df["minutes"]
    
    g = df.groupby(["customer_id", "project_id", "group_key", "k"], as_index=False).agg(
        uplift_sum=("uplift_weighted", "sum"),
        minutes=("minutes", "sum"),
        events=("event_id", "nunique"),
    )
    g["synergy_uplift_per_min"] = g["uplift_sum"] / (g["minutes"] + 1e-9)
    g["synergy_uplift_per_hr"] = g["synergy_uplift_per_min"] * 60.0
    
    return g[["customer_id", "project_id", "group_key", "k", "synergy_uplift_per_min", "synergy_uplift_per_hr", "events", "minutes"]]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# v1.3: Aggregate Synergy with Project Weights
# ═══════════════════════════════════════════════════════════════════════════════════════════

def aggregate_synergy_with_project_weights(
    pair_part: pd.DataFrame,
    group_part: pd.DataFrame,
    project_weights: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    v1.3: 프로젝트 가중치로 시너지 합산
    
    최종 Synergy = Σ (synergy_p × weight_p)
    
    입력:
    - pair_part: 파티션 기반 pair synergy
    - group_part: 파티션 기반 group synergy
    - project_weights: [customer_id, project_id, weight]
    
    출력:
    - pair_synergy: [i, j, synergy_uplift_per_min]
    - group_synergy: [group_key, k, synergy_uplift_per_min]
    """
    # ─── Pair Synergy ───
    if pair_part.empty:
        pair_synergy = pd.DataFrame(columns=["i", "j", "synergy_uplift_per_min"])
    else:
        p = pair_part.merge(
            project_weights,
            on=["customer_id", "project_id"],
            how="left"
        ).fillna({"weight": 0.0})
        
        # weight가 0인 경우 기본값 부여 (미등록 프로젝트)
        if (p["weight"] == 0).all():
            p["weight"] = 1.0 / len(p) if len(p) > 0 else 0.0
        
        p["weighted_uplift"] = p["synergy_uplift_per_min"] * p["weight"]
        
        pair_synergy = p.groupby(["i", "j"], as_index=False).agg(
            synergy_uplift_per_min=("weighted_uplift", "sum")
        )
    
    # ─── Group Synergy ───
    if group_part.empty:
        group_synergy = pd.DataFrame(columns=["group_key", "k", "synergy_uplift_per_min"])
    else:
        g = group_part.merge(
            project_weights,
            on=["customer_id", "project_id"],
            how="left"
        ).fillna({"weight": 0.0})
        
        # weight가 0인 경우 기본값 부여
        if (g["weight"] == 0).all():
            g["weight"] = 1.0 / len(g) if len(g) > 0 else 0.0
        
        g["weighted_uplift"] = g["synergy_uplift_per_min"] * g["weight"]
        
        group_synergy = g.groupby(["group_key", "k"], as_index=False).agg(
            synergy_uplift_per_min=("weighted_uplift", "sum")
        )
    
    return pair_synergy, group_synergy


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Indirect Score Calculation
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_indirect_scores(
    person: pd.DataFrame,
    edges: pd.DataFrame,
    lambda_decay: float
) -> pd.DataFrame:
    """간접 기여 점수 계산"""
    if edges is None or edges.empty:
        person = person.copy()
        person["indirect_per_min"] = 0.0
        person["score_per_min"] = person["coin_rate_per_min"]
        person["score_per_hr"] = person["score_per_min"] * 60.0
        return person
    
    p_map = person.set_index("person_id")["coin_rate_per_min"].to_dict()
    
    rows = []
    for _, e in edges.iterrows():
        i = str(e["from_id"]).strip()
        j = str(e["to_id"]).strip()
        w = float(e["link_strength"])
        
        indirect_add = p_map.get(j, 0.0) * w * lambda_decay
        rows.append({"person_id": i, "indirect_add": indirect_add})
    
    if rows:
        df = pd.DataFrame(rows)
        ind = df.groupby("person_id", as_index=False)["indirect_add"].sum()
        ind = ind.rename(columns={"indirect_add": "indirect_per_min"})
    else:
        ind = pd.DataFrame(columns=["person_id", "indirect_per_min"])
    
    out = person.merge(ind, on="person_id", how="left")
    out["indirect_per_min"] = out["indirect_per_min"].fillna(0.0)
    out["score_per_min"] = out["coin_rate_per_min"] + out["indirect_per_min"]
    out["score_per_hr"] = out["score_per_min"] * 60.0
    
    return out


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════════════════

def get_top_synergy_pairs(synergy: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """상위 시너지 페어 추출"""
    if synergy.empty:
        return synergy
    
    col = "synergy_uplift_per_min" if "synergy_uplift_per_min" in synergy.columns else "uplift"
    return synergy.nlargest(top_n, col)


def get_negative_synergy_pairs(synergy: pd.DataFrame) -> pd.DataFrame:
    """부정적 시너지 페어 추출"""
    if synergy.empty:
        return synergy
    
    col = "synergy_uplift_per_min" if "synergy_uplift_per_min" in synergy.columns else "uplift"
    return synergy[synergy[col] < 0]
