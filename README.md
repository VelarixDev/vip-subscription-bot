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

## ⚙️ Security
All sensitive tokens (Bot Token, Payment Provider Token) and database files are securely ignored via .gitignore and loaded through a config.py environment setup.

---
*Developed by [VelarixDev](https://github.com/VelarixDev)*