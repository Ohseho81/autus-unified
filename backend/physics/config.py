# backend/physics/config.py
# Physics 설정

class CFG:
    """물리 엔진 설정"""
    
    # 시너지 계산
    SYNERGY_THRESHOLD = 0.1
    MAX_GROUP_SIZE = 4
    MIN_PAIR_COUNT = 3
    
    # 플라이휠
    FLYWHEEL_MOMENTUM_DECAY = 0.95
    FLYWHEEL_ACCELERATION = 1.05
    
    # 에너지
    ENERGY_CONSERVATION = True
    MAX_ENERGY_TRANSFER = 1000000
    
    # 시간
    DEFAULT_TIME_WINDOW = 30  # days
    PREDICTION_HORIZON = 90  # days
