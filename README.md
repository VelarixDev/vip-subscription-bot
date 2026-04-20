# 💎 Telegram VIP Paywall Bot (Full-Stack)

A complete automated solution for managing paid private Telegram channels and groups. This bot handles the entire user journey: from a sleek Mini App subscription storefront to processing Telegram payments, generating one-time invite links, and automatically kicking expired users.

## ✨ Key Features
- Mini App Storefront: A responsive UI hosted on GitHub Pages for selecting subscription plans (1 month, 3 months, 1 Year).
- Native Telegram Payments: Integrated with Telegram's Invoice API (Stripe/Smart Glocal) for seamless in-app checkouts.
- Anti-Piracy System: Generates one-time use invite_links to prevent users from sharing private channel access.
- Automated Lifecycle Management: Uses an asynchronous background task (asyncio.sleep loop) to continuously monitor the SQLite database and automatically kick/ban users whose subscription has expired.
- Secure Admin Dashboard: An inline-keyboard control panel restricted by ADMIN_ID for broadcasting messages, viewing revenue/user statistics, and manually issuing VIP access.

## 🛠 Tech Stack
- Python 3.13
- aiogram 3.x
- aiosqlite (Asynchronous Database Operations)
- Telegram Web App API
- Telegram Payments API

## 📋 Configuration Setup

**Important:** Before running the bot, you must create a `config.py` file in the project root directory with your sensitive credentials. This file is already excluded from version control via `.gitignore` to prevent accidental exposure.

### config.py Variables

| Variable | Description | Example Format |
|----------|-------------|----------------|
| `BOT_TOKEN` | Your Telegram Bot API token obtained from [@BotFather](https://t.me/BotFather) | `"YOUR_BOT_TOKEN_HERE"` |
| `ADMIN_ID` | Your Telegram User ID (numeric) for admin access to the dashboard | `000000000` |
| `PAYMENT_TOKEN` | Telegram Payment Provider token for processing subscriptions (Stripe/Smart Glocal test token) | `"YOUR_PAYMENT_TOKEN_HERE"` |
| `WEB_APP_URL` | Full URL to your hosted Mini App web interface (e.g., GitHub Pages) | `"https://yourdomain.github.io/path/to/web/index.html"` |
| `CHANNEL_ID` | Telegram channel/group ID where VIP access is managed (use negative format for channels) | `-100XXXXXXXXXXX` |

### How to Get These Values

1. **BOT_TOKEN**: Open [@BotFather](https://t.me/BotFather) in Telegram, send `/newbot`, follow the setup wizard, and copy the provided API token.

2. **ADMIN_ID**: Send a message to [@GetMyID Bot](https://t.me/getmyid_bot) or use [@userinfobot](https://t.me/userinfobot) to retrieve your numeric Telegram ID.

3. **PAYMENT_TOKEN**: Configure [Telegram Payments](https://core.telegram.org/bots/payments) through your bot's settings in BotFather, or use a test provider token.

4. **WEB_APP_URL**: Host the `web/` directory on any static hosting service (GitHub Pages, Netlify, Vercel, etc.) and paste the public URL.

5. **CHANNEL_ID**: Add your bot as an admin to the target channel/group, then forward a message from that channel to [@GetMyID Bot](https://t.me/getmyid_bot) to retrieve the channel's numeric ID.

> ⚠️ **Security Warning:** Never commit `config.py` or any file containing real tokens/credentials to version control. If you've already committed it, use `git rm --cached config.py` and rotate all exposed credentials immediately.

---
*Developed by [VelarixDev](https://github.com/VelarixDev)*