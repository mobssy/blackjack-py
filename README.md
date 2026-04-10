<div align="center">
  <img src="assets/21.PNG" alt="JackPy" />
  <h1>Black Jack-py</h1>
  <p>A personal Blackjack game bot for Telegram, built as a side project.</p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.14-black?style=flat-square" />
    <img src="https://img.shields.io/badge/PostgreSQL-black?style=flat-square" />
    <img src="https://img.shields.io/badge/Telegram-Bot-black?style=flat-square" />
    <img src="https://img.shields.io/badge/License-MIT-black?style=flat-square" />
  </p>
</div>

---

## Overview

Black Jack-py is a Telegram bot I built to play Blackjack from my phone. It persists game stats to a PostgreSQL database, runs scheduled jobs via APScheduler, and is deployed with a CI pipeline through GitHub Actions.

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

---

## Project Structure

```
blackjack-py/
├── bot/
│   ├── handlers/         # Command handlers
│   ├── utils/            # Deck, payouts, scheduler
│   ├── middleware/        # Auth
│   └── main.py
├── models/               # SQLAlchemy models
├── infra/                # Requirements, Alembic migrations
├── .github/workflows/    # CI pipeline
└── tests/
```

---

## Getting Started

```bash
git clone https://github.com/mobssy/blackjack-py.git
cd blackjack-py

python3 -m venv venv
source venv/bin/activate

pip install -r infra/requirements.txt
cp .env.example .env

createdb blackjack
alembic -c infra/alembic.ini upgrade head

python -m bot.main
```

**Required environment variables**

```env
TELEGRAM_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:pass@localhost:5432/blackjack
```

---

## Commands

| Command | Description |
|---|---|
| `/deal [amount]` | Start a blackjack round |
| `/hit` | Draw a card |
| `/stand` | End your turn |
| `/daily` | Claim daily reward |
| `/wallet` | Check balance |
| `/rank` | Leaderboard |
| `/my` | Profile & stats |
| `/stats` | Detailed game stats |

---

## Blackjack Rules

- Blackjack pays 3:2
- Dealer hits until 17
- Push returns the bet

---

## License

MIT
