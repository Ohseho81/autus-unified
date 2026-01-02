# 🎯 AUTUS 프로젝트 - Cursor 작업 지시서

## 📍 현재 상태 (2026-01-02)

프로젝트가 `autus-unified` 폴더로 통합되었습니다.
이전 6개 분산 폴더 → 1개 통합 폴더

---

## 🚀 즉시 실행 명령어

### 1. 프로젝트 열기
```bash
cd /path/to/autus-unified
cursor .
```

### 2. 의존성 설치
```bash
cd backend
pip install -r requirements.txt
```

### 3. 서버 실행
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 테스트 실행
```bash
cd ..
pytest tests/ -v
```

### 5. Docker 실행
```bash
docker-compose up -d
```

---

## 📁 프로젝트 구조

```
autus-unified/
├── backend/                 # FastAPI 백엔드
│   ├── main.py              # 메인 API (열어서 확인)
│   ├── auth/                # 🆕 JWT + API Key 인증
│   ├── webhooks/            # Stripe/Shopify/토스
│   ├── autosync/            # 30+ SaaS 자동 감지
│   ├── crewai/              # AI 분석
│   ├── parasitic/           # 🆕 실제 SaaS API 연동
│   ├── physics/             # 물리 엔진
│   └── integrations/        # Zero Meaning, Neo4j
│
├── frontend/
│   ├── physics-map-unified.html  # 🆕 통합 Physics Map
│   ├── physics-map/              # 기존 15개 버전 (참고용)
│   └── dashboards/               # 대시보드들
│
├── tests/                   # 🆕 144개 테스트
├── n8n/                     # 워크플로우 7개
├── monitoring/              # Prometheus + Grafana
└── docker-compose.yml
```

---

## ✅ 완료된 작업 (오늘)

### 1. 테스트 코드 (144개)
- `tests/test_api.py` - API 엔드포인트 테스트
- `tests/test_auth.py` - 인증 테스트
- `tests/test_autosync.py` - AutoSync 테스트
- `tests/test_crewai.py` - CrewAI 테스트
- `tests/test_parasitic.py` - Parasitic 테스트
- `tests/test_webhooks.py` - Webhook 테스트
- `tests/test_integrations.py` - 통합 테스트

### 2. API 인증 (`backend/auth/`)
- JWT 토큰 발급/검증
- API Key 인증
- Rate Limiting (100 req/분)
- 스코프 기반 권한 (read, write, admin)

### 3. Parasitic 실제 API (`backend/parasitic/`)
- `saas_clients.py` - 실제 SaaS API 클라이언트
  - TossPOSClient
  - BaeminPOSClient
  - NaverBookingClient
  - GymSystemClient
- `absorber.py` - 동기화/흡수/대체 로직

### 4. Physics Map 통합
- `frontend/physics-map-unified.html` - D3.js 기반 통합 버전

---

## 🔴 남은 작업

### 우선순위 1: 배포
```bash
# Railway CLI 설치
npm install -g @railway/cli

# 로그인 및 배포
railway login
railway init
railway up
```

### 우선순위 2: 프론트엔드 React 전환
```
frontend/physics-map-unified.html → React 컴포넌트로 전환
```

### 우선순위 3: 실제 SaaS 연동 테스트
```
1. 토스 POS API 키 발급
2. backend/parasitic/saas_clients.py에 실제 키 설정
3. /parasitic/sync/{id} 테스트
```

---

## 🔑 테스트 계정

### JWT 로그인
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### API Key
```
X-API-Key: autus_dev_key_123
```

---

## 📊 API 엔드포인트

### 인증
- `POST /auth/login` - 로그인
- `POST /auth/api-key` - API Key 생성 (admin)
- `GET /auth/me` - 현재 인증 정보

### Webhooks
- `POST /webhook/stripe`
- `POST /webhook/shopify`
- `POST /webhook/toss`
- `POST /webhook/universal`

### AutoSync
- `GET /autosync/systems` - 지원 시스템
- `POST /autosync/detect` - 자동 감지
- `POST /autosync/transform` - 데이터 변환

### CrewAI
- `POST /crewai/analyze` - 전체 분석
- `POST /crewai/quick-delete` - 삭제 분석
- `POST /crewai/quick-automate` - 자동화 분석

### Parasitic
- `POST /parasitic/connect` - 연동 시작
- `POST /parasitic/credentials` - 인증 설정
- `POST /parasitic/sync/{id}` - 🆕 실제 동기화
- `POST /parasitic/absorb/{id}` - 흡수
- `POST /parasitic/replace/{id}` - 대체

---

## 💡 Cursor에서 할 일

1. **터미널 열기**: `Ctrl+`` 
2. **서버 실행**: `cd backend && uvicorn main:app --reload`
3. **브라우저**: `http://localhost:8000/docs` (Swagger UI)
4. **Physics Map**: `frontend/physics-map-unified.html` 열기

---

## 🎯 핵심 파일 (먼저 열어볼 것)

1. `backend/main.py` - API 전체 구조
2. `backend/auth/middleware.py` - 인증 로직
3. `backend/parasitic/saas_clients.py` - SaaS API 연동
4. `tests/test_api.py` - API 테스트 예시
5. `frontend/physics-map-unified.html` - 통합 UI

---

## 📈 완성도

| 모듈 | 상태 |
|------|------|
| 백엔드 API | 85% ✅ |
| 인증 | 100% ✅ |
| 테스트 | 70% ✅ |
| Physics Map | 70% ✅ |
| 배포 | 0% ⏳ |

**전체: ~80%**
