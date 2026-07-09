"""
JackPy - 다국어 지원 (한국어 / English)
"""

from typing import Any

STRINGS: dict[str, dict[str, str]] = {
    "ko": {
        # 언어 선택
        "select_language": "언어를 선택하세요.",
        "btn_korean": "🇰🇷 한국어",
        "btn_english": "🇺🇸 English",
        "language_set": "언어가 한국어로 설정되었습니다.",
        # /start
        "welcome_new": "JackPy에 오신 것을 환영합니다!\n\n가입 축하 보너스: $1,000\n\n",
        "welcome_back": "다시 오신 것을 환영합니다, {name}님!\n\n",
        "btn_game_start": "게임 시작",
        "btn_help": "도움말",
        "btn_daily": "출석 체크",
        "btn_profile": "프로필",
        # /deal
        "deal_usage": "[오류] 사용법: /deal [금액]\n예: /deal 100 | 올인: /deal all",
        "deal_positive": "[오류] 베팅 금액은 0보다 커야 합니다.",
        "deal_invalid": "[오류] 올바른 금액을 입력해주세요.",
        "deal_no_user": "[오류] 등록되지 않은 사용자입니다. /start를 먼저 실행해주세요.",
        "deal_no_balance": "[오류] 잔액이 부족합니다. 현재 잔액: ${balance:.2f}",
        "deal_in_progress": "[오류] 이미 게임이 진행 중입니다. /hit 또는 /stand를 입력하세요.",
        "dealer_label": "딜러",
        "player_label": "플레이어",
        "deal_caption": "블랙잭 시작!{theme}\n베팅: ${bet:,.2f}",
        # 게임 이미지 라벨
        "img_dealer": "🤖 딜러",
        "img_player": "🎯 플레이어",
        "img_total": "합",
        "hint_commands": "명령어: /hit (카드 추가) | /stand (멈춤)",
        "hint_commands_first": "명령어: /hit | /stand | /double (더블) | /surrender (항복)",
        "drawing_card": "카드를 뽑는 중...",
        "card_drawn": "카드를 한 장 더 받았습니다!",
        # 더블 다운 / 서렌더
        "double_only_first": "[오류] 더블 다운은 첫 두 장에서만 가능합니다.",
        "double_no_balance": "[오류] 더블 다운에 필요한 추가 잔액이 부족합니다. 현재 잔액: ${balance:,.2f}",
        "double_caption": "더블 다운! 베팅: ${bet:,.2f}",
        "surrender_only_first": "[오류] 서렌더는 첫 두 장에서만 가능합니다.",
        "result_surrender": "서렌더 (절반 회수)",
        # 스플릿
        "split_not_allowed": "[오류] 스플릿은 첫 두 장이 같은 랭크일 때만 가능합니다.",
        "split_no_balance": "[오류] 스플릿에 필요한 추가 잔액이 부족합니다. 현재 잔액: ${balance:,.2f}",
        "split_caption": "스플릿! 각 핸드에 베팅 ${bet:,.2f}",
        "split_aces_note": "에이스 스플릿: 각 핸드에 카드 1장씩만 받고 자동 스탠드합니다.",
        "hand_label": "핸드",
        "hand_playing": "핸드 {n}/{total} 플레이 중",
        "hand_bust_next": "핸드 {n} 버스트! 핸드 {next}/{total} 플레이 중",
        # 연승 스트릭
        "streak_line": "🔥 {n}연승 중!",
        "streak_bonus_line": "🔥 {n}연승 보너스: +${bonus:,.2f}",
        # 결과 라벨
        "result_label": "게임 결과",
        "bet_label": "베팅 금액",
        "payout_label": "정산 금액",
        "balance_label": "현재 잔액",
        "game_over_suffix": "게임 종료",
        "btn_play_again": "다시 시작",
        # 게임 결과
        "result_blackjack": "블랙잭!",
        "result_win": "승리!",
        "result_push": "무승부",
        "result_lose": "패배",
        "result_bust": "버스트",
        "result_dealer_bust": "딜러 버스트!",
        "game_over": "버스트 게임 종료",
        # /hit, /stand
        "no_game": "[오류] 진행 중인 게임이 없습니다. /deal [금액]으로 시작하세요.",
        "btn_hit": "Hit",
        "btn_stand": "Stand",
        # /daily
        "daily_already": "일일 보상은 하루에 한 번만 받을 수 있습니다.\n내일 다시 시도해주세요!",
        "daily_reward": "일일 보상 수령!\n\n받은 금액: ${reward:,.2f}{bonus}\n현재 잔액: ${balance:,.2f}",
        "daily_vip_bonus": " (VIP 보너스!)",
        # /wallet
        "wallet_info": "잔액: ${balance:,.2f}",
        "wallet_full": (
            "지갑 정보\n\n"
            "잔액: ${balance:,.2f}\n"
            "VIP: {vip}\n\n"
            "통계\n"
            "총 게임: {games:,}회\n"
            "승리: {wins:,}회\n"
            "패배: {losses:,}회\n"
            "연승: {streak:,}연승\n"
            "총 수익: ${profit:,.2f}"
        ),
        "vip_active": "[활성]",
        "vip_inactive": "[비활성]",
        # 게임 시작 안내
        "start_game_msg": "게임 시작\n\n/deal [금액] 명령어로 블랙잭을 시작하세요.\n예: /deal 100",
        # /help
        "help_text": (
            "JackPy 도움말\n\n"
            "게임 명령어\n"
            "/deal [금액] - 블랙잭 시작 (/deal all = 올인)\n"
            "/hit - 카드 추가\n"
            "/stand - 멈춤\n"
            "/double - 더블 다운 (첫 두 장, 베팅 2배 + 카드 1장)\n"
            "/surrender - 항복 (첫 두 장, 베팅액 절반 회수)\n"
            "/split - 스플릿 (같은 랭크 2장을 두 핸드로 분리)\n"
            "/wallet - 잔액 확인\n"
            "/daily - 일일 보상\n"
            "/rank - 랭킹 조회\n\n"
            "사용자 명령어\n"
            "/my - 내 프로필\n"
            "/start - 시작하기\n\n"
            "블랙잭 규칙\n"
            "목표: 21에 가까운 숫자\n"
            "블랙잭: 3:2 배당\n"
            "일반 승리: 1:1 배당\n"
            "무승부: 베팅액 반환\n"
            "서렌더: 베팅액 절반 회수\n"
            "스플릿: 같은 랭크 2장 분리 (추가 베팅, 에이스는 1장씩만)\n"
            "연승 보너스: 3연승부터 +10%, 5연승부터 +20%\n"
            "딜러: 17 이상까지 히트"
        ),
        # 단체방
        "group_redirect": "{name}님, 게임은 개인 채팅에서 진행됩니다!",
        "btn_start_dm": "BlackJack 시작하기",
        # 뒤로가기
        "btn_back": "뒤로가기",
    },
    "en": {
        # 언어 선택
        "select_language": "Please select your language.",
        "btn_korean": "🇰🇷 한국어",
        "btn_english": "🇺🇸 English",
        "language_set": "Language set to English.",
        # /start
        "welcome_new": "Welcome to JackPy!\n\nBonus chips: $1,000\n\n",
        "welcome_back": "Welcome back, {name}!\n\n",
        "btn_game_start": "Play",
        "btn_help": "Help",
        "btn_daily": "Daily Reward",
        "btn_profile": "Profile",
        # /deal
        "deal_usage": "[Error] Usage: /deal [amount]\nExample: /deal 100 | All-in: /deal all",
        "deal_positive": "[Error] Bet amount must be greater than 0.",
        "deal_invalid": "[Error] Please enter a valid amount.",
        "deal_no_user": "[Error] User not registered. Please run /start first.",
        "deal_no_balance": "[Error] Insufficient balance. Current balance: ${balance:.2f}",
        "deal_in_progress": "[Error] Game already in progress. Type /hit or /stand.",
        "dealer_label": "Dealer",
        "player_label": "Player",
        "deal_caption": "Blackjack!{theme}\nBet: ${bet:,.2f}",
        # 게임 이미지 라벨
        "img_dealer": "🤖 Dealer",
        "img_player": "🎯 Player",
        "img_total": "Total",
        "hint_commands": "Hit: /hit | Stand: /stand",
        "hint_commands_first": "/hit | /stand | /double | /surrender",
        "drawing_card": "Drawing card...",
        "card_drawn": "Card drawn!",
        # 더블 다운 / 서렌더
        "double_only_first": "[Error] Double down is only allowed on your first two cards.",
        "double_no_balance": "[Error] Insufficient balance to double down. Current balance: ${balance:,.2f}",
        "double_caption": "Double down! Bet: ${bet:,.2f}",
        "surrender_only_first": "[Error] Surrender is only allowed on your first two cards.",
        "result_surrender": "Surrender (half returned)",
        # 스플릿
        "split_not_allowed": "[Error] Split is only allowed when your first two cards are the same rank.",
        "split_no_balance": "[Error] Insufficient balance to split. Current balance: ${balance:,.2f}",
        "split_caption": "Split! ${bet:,.2f} bet per hand",
        "split_aces_note": "Split aces receive one card each and stand automatically.",
        "hand_label": "Hand",
        "hand_playing": "Playing hand {n}/{total}",
        "hand_bust_next": "Hand {n} bust! Playing hand {next}/{total}",
        # 연승 스트릭
        "streak_line": "🔥 {n} win streak!",
        "streak_bonus_line": "🔥 {n}-win streak bonus: +${bonus:,.2f}",
        # 결과 라벨
        "result_label": "Result",
        "bet_label": "Bet",
        "payout_label": "Payout",
        "balance_label": "Balance",
        "game_over_suffix": "Game Over",
        "btn_play_again": "Play Again",
        # 게임 결과
        "result_blackjack": "Blackjack!",
        "result_win": "Win!",
        "result_push": "Push",
        "result_lose": "Lose",
        "result_bust": "Bust",
        "result_dealer_bust": "Dealer Bust!",
        "game_over": "Bust - Game Over",
        # /hit, /stand
        "no_game": "[Error] No game in progress. Start with /deal [amount].",
        "btn_hit": "Hit",
        "btn_stand": "Stand",
        # /daily
        "daily_already": "Daily reward can only be claimed once per day.\nTry again tomorrow!",
        "daily_reward": "Daily reward claimed!\n\nAmount: ${reward:,.2f}{bonus}\nBalance: ${balance:,.2f}",
        "daily_vip_bonus": " (VIP bonus!)",
        # /wallet
        "wallet_info": "Balance: ${balance:,.2f}",
        "wallet_full": (
            "Wallet\n\n"
            "Balance: ${balance:,.2f}\n"
            "VIP: {vip}\n\n"
            "Stats\n"
            "Games: {games:,}\n"
            "Wins: {wins:,}\n"
            "Losses: {losses:,}\n"
            "Win streak: {streak:,}\n"
            "Total profit: ${profit:,.2f}"
        ),
        "vip_active": "[Active]",
        "vip_inactive": "[Inactive]",
        # 게임 시작 안내
        "start_game_msg": "Start Game\n\nUse /deal [amount] to start blackjack.\nExample: /deal 100",
        # /help
        "help_text": (
            "JackPy Help\n\n"
            "Game Commands\n"
            "/deal [amount] - Start blackjack (/deal all = all-in)\n"
            "/hit - Draw a card\n"
            "/stand - Stay\n"
            "/double - Double down (first two cards, 2x bet + one card)\n"
            "/surrender - Surrender (first two cards, half bet returned)\n"
            "/split - Split a same-rank pair into two hands\n"
            "/wallet - Check balance\n"
            "/daily - Daily reward\n"
            "/rank - Leaderboard\n\n"
            "User Commands\n"
            "/my - My profile\n"
            "/start - Start\n\n"
            "Blackjack Rules\n"
            "Goal: Get closer to 21 than the dealer\n"
            "Blackjack: 3:2 payout\n"
            "Win: 1:1 payout\n"
            "Push: Bet returned\n"
            "Surrender: Half bet returned\n"
            "Split: Same-rank pair, extra bet (aces get one card each)\n"
            "Streak bonus: +10% from 3 wins, +20% from 5 wins in a row\n"
            "Dealer hits until 17+"
        ),
        # 단체방
        "group_redirect": "{name}, please play in private chat!",
        "btn_start_dm": "Start BlackJack",
        # 뒤로가기
        "btn_back": "Back",
    },
}


def t(key: str, lang: str = "ko", **kwargs: Any) -> str:
    """번역 문자열 반환. 키가 없으면 한국어 fallback."""
    lang_dict = STRINGS.get(lang, STRINGS["ko"])
    text = lang_dict.get(key, STRINGS["ko"].get(key, key))
    return text.format(**kwargs) if kwargs else text


def get_user_lang(user) -> str:
    """User 객체에서 언어 코드 반환. 없으면 'ko'."""
    return getattr(user, "language", None) or "ko"
