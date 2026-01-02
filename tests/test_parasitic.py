# tests/test_parasitic.py
# Parasitic Absorption 모듈 테스트

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from parasitic.absorber import ParasiticAbsorber, Stage, SUPPORTED


class TestSupportedSystems:
    """지원 시스템 테스트"""
    
    def test_supported_systems_exist(self):
        """지원 시스템 목록 존재"""
        assert len(SUPPORTED) > 0
        assert len(SUPPORTED) >= 5
    
    def test_supported_systems_have_cost(self):
        """모든 시스템에 비용 정보"""
        for sys_id, info in SUPPORTED.items():
            assert "name" in info
            assert "cost" in info
            assert info["cost"] >= 0
    
    def test_toss_pos_in_supported(self):
        """토스 POS 지원"""
        assert "toss_pos" in SUPPORTED
        assert SUPPORTED["toss_pos"]["cost"] == 50000
    
    def test_baemin_pos_in_supported(self):
        """배민포스 지원"""
        assert "baemin_pos" in SUPPORTED
        assert SUPPORTED["baemin_pos"]["cost"] == 88000


class TestParasiticAbsorber:
    """Parasitic Absorber 테스트"""
    
    def setup_method(self):
        self.absorber = ParasiticAbsorber()
    
    def test_add_connector(self):
        """커넥터 추가"""
        cid = self.absorber.add("toss_pos")
        
        assert cid is not None
        assert "toss_pos" in cid
        assert cid in self.absorber.connectors
    
    def test_add_sets_parasitic_stage(self):
        """추가 시 기생 단계"""
        cid = self.absorber.add("toss_pos")
        
        assert self.absorber.status[cid] == Stage.PARASITIC
    
    def test_start_parasitic(self):
        """기생 시작"""
        cid = self.absorber.add("toss_pos")
        result = self.absorber.start_parasitic(cid)
        
        assert result["success"] is True
        assert result["stage"] == "PARASITIC"
        assert self.absorber.status[cid] == Stage.PARASITIC
    
    def test_start_parasitic_invalid_id(self):
        """잘못된 ID로 기생 시작"""
        result = self.absorber.start_parasitic("invalid_id")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_absorb_requires_sync_count(self):
        """흡수는 동기화 10회 필요"""
        cid = self.absorber.add("toss_pos")
        
        # 동기화 없이 흡수 시도
        result = self.absorber.absorb(cid)
        assert result["success"] is False
        assert "동기화 부족" in result["error"]
    
    def test_absorb_after_sync(self):
        """동기화 후 흡수"""
        cid = self.absorber.add("toss_pos")
        
        # 10회 동기화
        for _ in range(10):
            self.absorber.increment_sync(cid)
        
        result = self.absorber.absorb(cid)
        assert result["success"] is True
        assert result["stage"] == "ABSORBING"
        assert self.absorber.status[cid] == Stage.ABSORBING
    
    def test_replace_requires_absorbing(self):
        """대체는 흡수 완료 필요"""
        cid = self.absorber.add("toss_pos")
        
        # 흡수 없이 대체 시도
        result = self.absorber.replace(cid)
        assert result["success"] is False
    
    def test_replace_after_absorb(self):
        """흡수 후 대체"""
        cid = self.absorber.add("toss_pos")
        
        # 동기화 + 흡수
        for _ in range(10):
            self.absorber.increment_sync(cid)
        self.absorber.absorb(cid)
        
        result = self.absorber.replace(cid)
        assert result["success"] is True
        assert result["stage"] == "REPLACING"
        assert "monthly_savings" in result
    
    def test_replace_returns_savings(self):
        """대체 시 절감액 반환"""
        cid = self.absorber.add("baemin_pos")  # 88,000원
        
        for _ in range(10):
            self.absorber.increment_sync(cid)
        self.absorber.absorb(cid)
        
        result = self.absorber.replace(cid)
        assert result["monthly_savings"] == 88000
    
    def test_complete_requires_replacing(self):
        """완료는 대체 준비 필요"""
        cid = self.absorber.add("toss_pos")
        
        # 대체 준비 없이 완료 시도
        result = self.absorber.complete(cid)
        assert result["success"] is False
    
    def test_complete_full_flow(self):
        """전체 흐름: 기생 → 흡수 → 대체 → 완료"""
        cid = self.absorber.add("toss_pos")
        
        # 1. 기생
        self.absorber.start_parasitic(cid)
        assert self.absorber.status[cid] == Stage.PARASITIC
        
        # 2. 동기화
        for _ in range(10):
            self.absorber.increment_sync(cid)
        
        # 3. 흡수
        self.absorber.absorb(cid)
        assert self.absorber.status[cid] == Stage.ABSORBING
        
        # 4. 대체 준비
        self.absorber.replace(cid)
        assert self.absorber.status[cid] == Stage.REPLACING
        
        # 5. 완료
        result = self.absorber.complete(cid)
        assert result["success"] is True
        assert result["stage"] == "REPLACED"
        assert self.absorber.status[cid] == Stage.REPLACED
    
    def test_increment_sync(self):
        """동기화 카운트 증가"""
        cid = self.absorber.add("toss_pos")
        
        self.absorber.increment_sync(cid)
        self.absorber.increment_sync(cid)
        self.absorber.increment_sync(cid)
        
        assert self.absorber.connectors[cid]["sync_count"] == 3
    
    def test_get_status(self):
        """전체 상태 조회"""
        cid1 = self.absorber.add("toss_pos")
        cid2 = self.absorber.add("baemin_pos")
        
        status = self.absorber.get_status()
        
        assert status["total"] == 2
        assert cid1 in status["connectors"]
        assert cid2 in status["connectors"]
    
    def test_get_status_replaced_count(self):
        """대체 완료 수 카운트"""
        cid = self.absorber.add("toss_pos")
        
        # 전체 흐름 실행
        for _ in range(10):
            self.absorber.increment_sync(cid)
        self.absorber.absorb(cid)
        self.absorber.replace(cid)
        self.absorber.complete(cid)
        
        status = self.absorber.get_status()
        assert status["replaced"] == 1


class TestStageEnum:
    """Stage Enum 테스트"""
    
    def test_stage_values(self):
        """단계 값 확인"""
        assert Stage.PARASITIC.value == "parasitic"
        assert Stage.ABSORBING.value == "absorbing"
        assert Stage.REPLACING.value == "replacing"
        assert Stage.REPLACED.value == "replaced"
    
    def test_stage_count(self):
        """4단계 존재"""
        assert len(Stage) == 4

# tests/test_parasitic.py
# Parasitic Absorption 모듈 테스트

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from parasitic.absorber import ParasiticAbsorber, Stage, SUPPORTED


class TestSupportedSystems:
    """지원 시스템 테스트"""
    
    def test_supported_systems_exist(self):
        """지원 시스템 목록 존재"""
        assert len(SUPPORTED) > 0
        assert len(SUPPORTED) >= 5
    
    def test_supported_systems_have_cost(self):
        """모든 시스템에 비용 정보"""
        for sys_id, info in SUPPORTED.items():
            assert "name" in info
            assert "cost" in info
            assert info["cost"] >= 0
    
    def test_toss_pos_in_supported(self):
        """토스 POS 지원"""
        assert "toss_pos" in SUPPORTED
        assert SUPPORTED["toss_pos"]["cost"] == 50000
    
    def test_baemin_pos_in_supported(self):
        """배민포스 지원"""
        assert "baemin_pos" in SUPPORTED
        assert SUPPORTED["baemin_pos"]["cost"] == 88000


class TestParasiticAbsorber:
    """Parasitic Absorber 테스트"""
    
    def setup_method(self):
        self.absorber = ParasiticAbsorber()
    
    def test_add_connector(self):
        """커넥터 추가"""
        cid = self.absorber.add("toss_pos")
        
        assert cid is not None
        assert "toss_pos" in cid
        assert cid in self.absorber.connectors
    
    def test_add_sets_parasitic_stage(self):
        """추가 시 기생 단계"""
        cid = self.absorber.add("toss_pos")
        
        assert self.absorber.status[cid] == Stage.PARASITIC
    
    def test_start_parasitic(self):
        """기생 시작"""
        cid = self.absorber.add("toss_pos")
        result = self.absorber.start_parasitic(cid)
        
        assert result["success"] is True
        assert result["stage"] == "PARASITIC"
        assert self.absorber.status[cid] == Stage.PARASITIC
    
    def test_start_parasitic_invalid_id(self):
        """잘못된 ID로 기생 시작"""
        result = self.absorber.start_parasitic("invalid_id")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_absorb_requires_sync_count(self):
        """흡수는 동기화 10회 필요"""
        cid = self.absorber.add("toss_pos")
        
        # 동기화 없이 흡수 시도
        result = self.absorber.absorb(cid)
        assert result["success"] is False
        assert "동기화 부족" in result["error"]
    
    def test_absorb_after_sync(self):
        """동기화 후 흡수"""
        cid = self.absorber.add("toss_pos")
        
        # 10회 동기화
        for _ in range(10):
            self.absorber.increment_sync(cid)
        
        result = self.absorber.absorb(cid)
        assert result["success"] is True
        assert result["stage"] == "ABSORBING"
        assert self.absorber.status[cid] == Stage.ABSORBING
    
    def test_replace_requires_absorbing(self):
        """대체는 흡수 완료 필요"""
        cid = self.absorber.add("toss_pos")
        
        # 흡수 없이 대체 시도
        result = self.absorber.replace(cid)
        assert result["success"] is False
    
    def test_replace_after_absorb(self):
        """흡수 후 대체"""
        cid = self.absorber.add("toss_pos")
        
        # 동기화 + 흡수
        for _ in range(10):
            self.absorber.increment_sync(cid)
        self.absorber.absorb(cid)
        
        result = self.absorber.replace(cid)
        assert result["success"] is True
        assert result["stage"] == "REPLACING"
        assert "monthly_savings" in result
    
    def test_replace_returns_savings(self):
        """대체 시 절감액 반환"""
        cid = self.absorber.add("baemin_pos")  # 88,000원
        
        for _ in range(10):
            self.absorber.increment_sync(cid)
        self.absorber.absorb(cid)
        
        result = self.absorber.replace(cid)
        assert result["monthly_savings"] == 88000
    
    def test_complete_requires_replacing(self):
        """완료는 대체 준비 필요"""
        cid = self.absorber.add("toss_pos")
        
        # 대체 준비 없이 완료 시도
        result = self.absorber.complete(cid)
        assert result["success"] is False
    
    def test_complete_full_flow(self):
        """전체 흐름: 기생 → 흡수 → 대체 → 완료"""
        cid = self.absorber.add("toss_pos")
        
        # 1. 기생
        self.absorber.start_parasitic(cid)
        assert self.absorber.status[cid] == Stage.PARASITIC
        
        # 2. 동기화
        for _ in range(10):
            self.absorber.increment_sync(cid)
        
        # 3. 흡수
        self.absorber.absorb(cid)
        assert self.absorber.status[cid] == Stage.ABSORBING
        
        # 4. 대체 준비
        self.absorber.replace(cid)
        assert self.absorber.status[cid] == Stage.REPLACING
        
        # 5. 완료
        result = self.absorber.complete(cid)
        assert result["success"] is True
        assert result["stage"] == "REPLACED"
        assert self.absorber.status[cid] == Stage.REPLACED
    
    def test_increment_sync(self):
        """동기화 카운트 증가"""
        cid = self.absorber.add("toss_pos")
        
        self.absorber.increment_sync(cid)
        self.absorber.increment_sync(cid)
        self.absorber.increment_sync(cid)
        
        assert self.absorber.connectors[cid]["sync_count"] == 3
    
    def test_get_status(self):
        """전체 상태 조회"""
        cid1 = self.absorber.add("toss_pos")
        cid2 = self.absorber.add("baemin_pos")
        
        status = self.absorber.get_status()
        
        assert status["total"] == 2
        assert cid1 in status["connectors"]
        assert cid2 in status["connectors"]
    
    def test_get_status_replaced_count(self):
        """대체 완료 수 카운트"""
        cid = self.absorber.add("toss_pos")
        
        # 전체 흐름 실행
        for _ in range(10):
            self.absorber.increment_sync(cid)
        self.absorber.absorb(cid)
        self.absorber.replace(cid)
        self.absorber.complete(cid)
        
        status = self.absorber.get_status()
        assert status["replaced"] == 1


class TestStageEnum:
    """Stage Enum 테스트"""
    
    def test_stage_values(self):
        """단계 값 확인"""
        assert Stage.PARASITIC.value == "parasitic"
        assert Stage.ABSORBING.value == "absorbing"
        assert Stage.REPLACING.value == "replacing"
        assert Stage.REPLACED.value == "replaced"
    
    def test_stage_count(self):
        """4단계 존재"""
        assert len(Stage) == 4


