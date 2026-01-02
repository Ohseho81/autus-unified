# 🚀 AUTUS Unified v2.1.0

> 통합 AUTUS 프로젝트 - Money Physics OS

---

## 📁 구조

```
autus-unified/
├── backend/                    # Python FastAPI 백엔드
│   ├── main.py                 # 메인 API 서버
│   ├── Dockerfile              # Docker 이미지 빌드
│   ├── requirements.txt
│   │
│   ├── auth/                   # 인증 (JWT + API Key)
│   │   ├── middleware.py       # JWT/API Key 검증
│   │   └── api.py              # 인증 엔드포인트
│   │
│   ├── webhooks/               # SaaS Webhook 수신
│   │   ├── stripe_webhook.py
│   │   ├── shopify_webhook.py
│   │   ├── toss_webhook.py
│   │   └── universal_webhook.py
│   │
│   ├── autosync/               # 30+ SaaS 자동 감지/연동
│   │   ├── detector.py         # 자동 감지 로직
│   │   ├── transformer.py      # Zero Meaning 변환
│   │   └── registry/           # SaaS 레지스트리
│   │
│   ├── crewai/                 # AI 분석 (삭제/자동화/외부용역)
│   │   ├── agents.py           # CrewAI 에이전트
│   │   └── api.py              # 분석 API
│   │
│   ├── parasitic/              # 기생→흡수→대체 전략
│   │   ├── absorber.py         # 흡수 로직
│   │   ├── saas_clients.py     # 실제 SaaS API 클라이언트
│   │   └── api.py              # Parasitic API
│   │
│   ├── physics/                # 물리 엔진 (🆕 통합)
│   │   ├── router.py           # Physics API 라우터
│   │   ├── core.py             # 핵심 물리 로직
│   │   ├── physics_engine.py   # 엔진 구현
│   │   ├── synergy.py          # 시너지 계산
│   │   └── flywheel.py         # 플라이휠 시뮬레이션
│   │
│   ├── websocket/              # 실시간 WebSocket
│   │   ├── manager.py          # 연결 관리
│   │   └── api.py              # WebSocket 엔드포인트
│   │
│   ├── llm/                    # LLM 라우터
│   │   └── llm_router.py
│   │
│   └── integrations/           # 외부 연동
│       ├── zero_meaning.py     # Zero Meaning 변환기
│       └── neo4j_client.py     # Neo4j 클라이언트
│
├── frontend/                   # 프론트엔드
│   ├── index.html
│   ├── physics-map-unified.html  # 통합 Physics Map
│   ├── PhysicsMapGlobal.jsx
│   │
│   ├── physics-map/            # Physics Map 버전들
│   │   ├── physics_map_threejs.html
│   │   ├── physics_map_d3.html
│   │   └── ...
│   │
│   └── dashboards/             # 대시보드
│       ├── automation_dashboard.html
│       ├── flywheel_bezos.html
│       └── ...
│
├── n8n/                        # n8n 워크플로우
│   ├── stripe_webhook.json
│   ├── toss_virtual_account.json
│   ├── crewai_analysis.json
│   └── error_handler.json
│
├── monitoring/                 # 모니터링
│   ├── prometheus.yml
│   ├── docker-compose.monitoring.yml
│   └── grafana/
│
├── tests/                      # 테스트
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_auth.py
│   ├── test_autosync.py
│   ├── test_crewai.py
│   ├── test_parasitic.py
│   ├── test_webhooks.py
│   └── test_websocket.py
│
├── docker-compose.yml          # 메인 Docker Compose
├── env-template.txt            # 환경변수 템플릿
└── pytest.ini
```

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
cp env-template.txt .env
# .env 파일을 열어 실제 값으로 수정
```

### 2. 로컬 실행

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# http://localhost:8000/docs
```

### 3. Docker 실행

```bash
docker-compose up -d
# API: http://localhost:8000
# n8n: http://localhost:5678
# Neo4j: http://localhost:7474
```

### 4. 테스트 실행

```bash
pytest tests/ -v
```

---

## 🔑 인증

### JWT 토큰

```bash
# 로그인
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# API 호출
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

### API Key

```bash
curl http://localhost:8000/auth/me \
  -H "X-API-Key: autus_dev_key_123"
```

**테스트 계정:**
- `admin` / `admin123` (모든 권한)
- `user` / `user123` (read, write)
- `readonly` / `readonly123` (read만)

---

## 📊 핵심 API

### Authentication
| 엔드포인트 | 설명 |
|-----------|------|
| `POST /auth/login` | JWT 토큰 발급 |
| `POST /auth/api-key` | API Key 생성 (admin) |
| `GET /auth/me` | 현재 인증 정보 |
| `GET /auth/rate-limit` | Rate Limit 상태 |

### Physics Engine (🆕)
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /physics/state` | 현재 맵 상태 (노드, 링크, 시너지) |
| `GET /physics/kpi` | KPI 조회 (7일/28일) |
| `GET /physics/predict` | KPI 예측 (Rolling Horizon) |
| `POST /physics/person` | 사람(노드) 추가 |
| `POST /physics/event` | 이벤트 추가 (mint/burn/transfer) |
| `POST /physics/drag` | 드래그 입력 처리 |

### WebSocket (실시간)
| 엔드포인트 | 설명 |
|-----------|------|
| `ws://localhost:8000/ws/physics-map` | Physics Map 실시간 |
| `ws://localhost:8000/ws/dashboard` | 대시보드 실시간 |
| `ws://localhost:8000/ws/flywheel` | 플라이휠 실시간 |
| `GET /websocket/stats` | WebSocket 통계 |
| `POST /websocket/broadcast/test` | 테스트 브로드캐스트 |

### Webhooks
| 엔드포인트 | 설명 |
|-----------|------|
| `POST /webhook/stripe` | Stripe 웹훅 |
| `POST /webhook/shopify` | Shopify 웹훅 |
| `POST /webhook/toss` | 토스 웹훅 |
| `POST /webhook/universal` | 범용 웹훅 |

### AutoSync
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /autosync/systems` | 지원 시스템 목록 (30+) |
| `POST /autosync/detect` | 자동 감지 (쿠키/도메인/API키) |
| `POST /autosync/transform` | Zero Meaning 변환 |
| `POST /autosync/connect` | 시스템 연결 |

### CrewAI
| 엔드포인트 | 설명 |
|-----------|------|
| `POST /crewai/analyze` | 전체 분석 |
| `POST /crewai/quick-delete` | 삭제 대상 분석 |
| `POST /crewai/quick-automate` | 자동화 대상 분석 |

### Parasitic Absorption
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /parasitic/supported` | 지원 SaaS 목록 |
| `POST /parasitic/connect` | 연동 시작 |
| `POST /parasitic/credentials` | 인증 설정 |
| `POST /parasitic/sync/{id}` | 실제 동기화 |
| `POST /parasitic/absorb/{id}` | 데이터 흡수 |
| `POST /parasitic/replace/{id}` | 완전 대체 |
| `GET /parasitic/flywheel` | 플라이휠 상태 |

---

## 💡 핵심 철학

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ZERO MEANING: 모든 데이터 → { node_id, value, timestamp } │
│                                                             │
│  MONEY PHYSICS: 사람 = 노드, 돈 = 에너지                   │
│                                                             │
│  FLYWHEEL: 삭제 70% + 자동화 20% + 시너지 10%              │
│                                                             │
│  공식: V = (M - T) × (1 + s)^t                             │
│                                                             │
│  2버튼: CUT (삭제) / LINK (연결) - 그 외 없음              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 완성도 (v2.1.0)

| 모듈 | 상태 | 비고 |
|------|------|------|
| 백엔드 API | 90% ✅ | Physics 라우터 통합 완료 |
| 인증 (JWT/API Key) | 100% ✅ | Rate Limiting 포함 |
| Physics Engine | 85% ✅ | 🆕 main.py 통합 |
| WebSocket | 85% ✅ | 3개 채널 지원 |
| AutoSync | 85% ✅ | 30+ SaaS 지원 |
| Parasitic | 80% ✅ | 실제 SaaS 클라이언트 |
| CrewAI | 75% ✅ | Rule-based fallback |
| Physics Map UI | 70% ✅ | 15+ 버전 |
| 테스트 코드 | 75% ✅ | 중복 제거 완료 |
| n8n 워크플로우 | 85% ✅ | 7개 워크플로우 |
| Docker/배포 | 90% ✅ | 🆕 Dockerfile 추가 |
| 모니터링 | 85% ✅ | Prometheus + Grafana |
| **전체** | **~85%** | 🆙 +5% |

---

## 🎯 다음 단계

### 즉시 가능
1. ✅ 중복 코드 제거 완료
2. ✅ Physics API 통합 완료
3. ✅ Dockerfile 추가 완료

### 다음 작업
1. 🔄 Physics Map 15버전 → 1개로 통합
2. 🔄 실제 SaaS 연동 테스트 (토스 POS 등)
3. 🔄 Railway/Vercel 배포
4. 🔄 Redis 캐싱 활성화

---

## 🐳 Docker 서비스

| 서비스 | 포트 | 설명 |
|--------|------|------|
| `autus-api` | 8000 | FastAPI 메인 서버 |
| `postgres` | 5432 | PostgreSQL DB |
| `neo4j` | 7474, 7687 | Neo4j 그래프 DB |
| `redis` | 6379 | 캐시 + Rate Limiting |
| `n8n` | 5678 | 워크플로우 자동화 |

---

## 📝 라이선스

MIT License

---

*AUTUS Integration Hub v2.1.0 - Money Physics OS*


