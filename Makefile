# JackPy - Makefile
# 개발 및 배포 작업 자동화

.PHONY: help install test lint format run clean db-init db-migrate db-upgrade db-downgrade

# 기본 타겟: 도움말
help:
	@echo "JackPy - 사용 가능한 명령어:"
	@echo ""
	@echo "  make install        - 의존성 설치"
	@echo "  make test           - 테스트 실행"
	@echo "  make lint           - 코드 린팅"
	@echo "  make format         - 코드 포맷팅"
	@echo "  make run            - 봇 실행"
	@echo "  make clean          - 임시 파일 정리"
	@echo ""
	@echo "  make db-init        - 데이터베이스 초기화"
	@echo "  make db-migrate     - 마이그레이션 생성"
	@echo "  make db-upgrade     - 마이그레이션 적용"
	@echo "  make db-downgrade   - 마이그레이션 롤백"
	@echo ""

# 의존성 설치
install:
	pip install --upgrade pip
	pip install -r infra/requirements.txt
	@echo "✅ 의존성 설치 완료"

# 테스트 실행
test:
	pytest tests/ -v --cov=bot --cov=models --cov-report=term-missing
	@echo "✅ 테스트 완료"

# 코드 린팅
lint:
	flake8 bot/ models/ --max-line-length=127
	@echo "✅ 린팅 완료"

# 코드 포맷팅
format:
	black bot/ models/ tests/
	@echo "✅ 포맷팅 완료"

# 봇 실행
run:
	python -m bot.main

# 임시 파일 정리
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	rm -rf .pytest_cache .coverage htmlcov/ .tox/
	@echo "✅ 정리 완료"

# 데이터베이스 초기화 (테이블 생성)
db-init:
	python -c "from models import init_db; init_db()"
	@echo "✅ 데이터베이스 초기화 완료"

# 마이그레이션 생성
db-migrate:
	alembic -c infra/alembic.ini revision --autogenerate -m "$(msg)"
	@echo "✅ 마이그레이션 생성 완료"

# 마이그레이션 적용
db-upgrade:
	alembic -c infra/alembic.ini upgrade head
	@echo "✅ 마이그레이션 적용 완료"

# 마이그레이션 롤백
db-downgrade:
	alembic -c infra/alembic.ini downgrade -1
	@echo "✅ 마이그레이션 롤백 완료"

# 개발 환경 설정 (처음 한 번만)
setup: install
	cp .env.example .env
	@echo "⚠️  .env 파일을 편집하여 환경변수를 설정하세요"
	@echo "✅ 개발 환경 설정 완료"
