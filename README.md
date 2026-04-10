<div align="center">
  <img src="assets/21.PNG" alt="JackPy" />
  <h1>Black Jack-py</h1>
  <p>Production-grade Blackjack casino bot for Telegram.</p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.14-black?style=flat-square" />
    <img src="https://img.shields.io/badge/PostgreSQL-15-black?style=flat-square" />
    <img src="https://img.shields.io/badge/Telegram-Bot-black?style=flat-square" />
    <img src="https://img.shields.io/badge/License-MIT-black?style=flat-square" />
  </p>
</div>

---

## Overview

Black Jack-py is a Telegram-based blackjack bot built for real commercial deployment. It features a tiered membership system (Free / VIP / Business), automated scheduling, and a full admin panel — all running on a clean Python + PostgreSQL stack with CI/CD via GitHub Actions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.14 |
| Bot SDK | python-telegram-bot 22.5 |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL |
| Scheduler | APScheduler 3.11 |
| Migrations | Alembic 1.17 |
| CI/CD | GitHub Actions |
| Process | systemd on Ubuntu 22.04 |

---

## Project Structure

```
jackpy/
├── bot/
│   ├── handlers/         # Command handlers
│   ├── utils/            # Deck, payouts, ads, scheduler
│   ├── middleware/        # Auth & permissions
│   └── main.py
├── models/               # SQLAlchemy models
├── infra/                # Requirements, systemd, Alembic
├── .github/workflows/    # CI & deploy pipelines
└── tests/
```

---

## Getting Started

```bash
git clone https://github.com/yourusername/jackpy.git
cd jackpy

python3.11 -m venv venv
source venv/bin/activate

pip install -r infra/requirements.txt
cp .env.example .env

createdb jackpy
alembic -c infra/alembic.ini upgrade head

python -m bot.main
```

**Required environment variables**

```env
TELEGRAM_TOKEN=your_bot_token
ADMIN_IDS=your_telegram_id
DATABASE_URL=postgresql://user:pass@localhost:5432/jackpy
```

---

## Commands

**Game**

| Command | Description |
|---|---|
| `/deal [amount]` | Start a blackjack round |
| `/hit` | Draw a card |
| `/stand` | End your turn |
| `/daily` | Claim daily reward |
| `/wallet` | Check balance |
| `/rank` | Leaderboard |

**Account**

| Command | Description |
|---|---|
| `/start` | Onboarding & plan info |
| `/my` | Profile card |
| `/stats` | Detailed stats |

**Admin**

| Command | Description |
|---|---|
| `/admin pending` | View approval queue |
| `/admin stats` | Platform statistics |
| `/approve [id] [days]` | Grant VIP |
| `/reject [id] [reason]` | Reject request |
| `/revoke [id]` | Remove VIP |

---

## Deployment

Refer to the [deployment guide](infra/) for full Ubuntu 22.04 setup including PostgreSQL, systemd, and GitHub Actions secrets configuration.

---

## License

MIT © Black Jack-py
