"""
JackPy - 메인 봇 파일
텔레그램 봇 초기화 및 실행
"""

import os
import logging
import sys
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("jackpy.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 텔레그램 토큰 확인
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN 환경변수가 설정되지 않았습니다.")
    sys.exit(1)

# 핸들러 import
from bot.handlers import (
    cmd_start,
    cmd_help,
    button_callback,
    cmd_deal,
    cmd_hit,
    cmd_stand,
    cmd_wallet,
    cmd_daily,
    cmd_vip,
    cmd_business,
    cmd_confirm,
    cmd_confirm_business,
    cmd_admin,
    cmd_approve,
    cmd_approve_business,
    cmd_reject,
    cmd_revoke,
    cmd_add_balance,
    cmd_my,
    cmd_rank,
    cmd_stats,
)

# 미들웨어 import
from bot.middleware.auth import user_middleware, group_middleware, logging_middleware

# 모델 import
from models import init_db

# 스케줄러 import
from bot.utils.scheduler import JackPyScheduler


def setup_handlers(app: Application):
    """
    핸들러 등록

    Args:
        app: 텔레그램 Application 객체
    """
    # 미들웨어 등록
    app.add_handler(MessageHandler(filters.ALL, logging_middleware), group=-2)
    app.add_handler(MessageHandler(filters.ALL, user_middleware), group=-1)
    app.add_handler(MessageHandler(filters.ALL, group_middleware), group=-1)

    # 기본 명령어
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    # 블랙잭 게임
    app.add_handler(CommandHandler("deal", cmd_deal))
    app.add_handler(CommandHandler("hit", cmd_hit))
    app.add_handler(CommandHandler("stand", cmd_stand))
    app.add_handler(CommandHandler("wallet", cmd_wallet))
    app.add_handler(CommandHandler("daily", cmd_daily))

    # VIP & 비즈니스
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("business", cmd_business))
    app.add_handler(CommandHandler("confirm", cmd_confirm))
    app.add_handler(CommandHandler("confirm_business", cmd_confirm_business))

    # 관리자
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("approve_business", cmd_approve_business))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(CommandHandler("add", cmd_add_balance))

    # 프로필
    app.add_handler(CommandHandler("my", cmd_my))
    app.add_handler(CommandHandler("rank", cmd_rank))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # 인라인 버튼 콜백
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("✅ 핸들러 등록 완료")


async def post_init(app: Application):
    """
    봇 초기화 후 실행 작업

    Args:
        app: 텔레그램 Application 객체
    """
    logger.info("🚀 JackPy 봇 초기화 중...")

    # 데이터베이스 초기화
    init_db()

    # 스케줄러 시작
    scheduler = JackPyScheduler(app.bot)
    scheduler.start()
    app.bot_data["scheduler"] = scheduler

    logger.info("✅ JackPy 봇 초기화 완료")


async def post_shutdown(app: Application):
    """
    봇 종료 전 실행 작업

    Args:
        app: 텔레그램 Application 객체
    """
    logger.info("⏹ JackPy 봇 종료 중...")

    # 스케줄러 중지
    if "scheduler" in app.bot_data:
        app.bot_data["scheduler"].stop()

    logger.info("✅ JackPy 봇 종료 완료")


def main():
    """메인 함수"""
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🎰 JackPy - Telegram Casino Bot")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Application 생성
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # 핸들러 설정
    setup_handlers(app)

    # 봇 시작
    logger.info("🚀 봇 시작...")
    app.run_polling(
        allowed_updates=["message", "callback_query"], drop_pending_updates=True
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("⏹ 사용자에 의해 봇이 중지되었습니다.")
    except Exception as e:
        logger.error(f"❌ 치명적 오류: {e}", exc_info=True)
        sys.exit(1)
