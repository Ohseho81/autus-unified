# AUTUS 모니터링 설치 가이드

## 구성 요소

| 도구 | 포트 | 용도 |
|------|------|------|
| Prometheus | 9090 | 메트릭 수집 |
| Grafana | 3001 | 대시보드 |
| Node Exporter | 9100 | 서버 메트릭 |
| Uptime Kuma | 3002 | 업타임 모니터링 |

## 빠른 시작

```bash
# 1. 네트워크 생성 (최초 1회)
docker network create autus-network

# 2. 모니터링 시작
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d

# 3. 접속
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin / autus123)
# Uptime Kuma: http://localhost:3002
```

## n8n 메트릭 활성화

```bash
# n8n 환경변수 추가
N8N_METRICS=true
N8N_METRICS_PREFIX=n8n_
```

## Grafana 대시보드

1. 로그인 후 왼쪽 메뉴 → Dashboards
2. AUTUS 폴더 → n8n 모니터링 선택

## 주요 메트릭

| 메트릭 | 설명 |
|--------|------|
| n8n_workflow_executions_total | 총 실행 수 |
| n8n_workflow_executions_failed_total | 실패 수 |
| n8n_workflow_execution_duration_seconds | 실행 시간 |
| node_cpu_seconds_total | CPU 사용량 |
| node_memory_MemAvailable_bytes | 가용 메모리 |

## 알림 설정 (Slack)

1. Grafana → Alerting → Contact points
2. New contact point → Slack
3. Webhook URL 입력
4. 대시보드 패널 → Alert 탭 → Create alert

## Uptime Kuma 설정

1. http://localhost:3002 접속
2. Add New Monitor
3. 타입: HTTP(s)
4. URL: http://n8n:5678/healthz
5. Interval: 60초

## 문제 해결

### Prometheus 연결 안됨
```bash
# n8n이 같은 네트워크에 있는지 확인
docker network inspect autus-network
```

### Grafana 데이터 없음
```bash
# Prometheus 타겟 상태 확인
curl http://localhost:9090/api/v1/targets
```
