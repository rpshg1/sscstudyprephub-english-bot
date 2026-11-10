# SSC Study Prep Hub — 3x Daily English Telegram Automation

A **100% cloud-autonomous** Telegram bot pipeline powered by **GitHub Actions** + **Google Gemini (`gemini-3.8-flash`)** that posts exam-focused English capsules to `@sscstudyprephub` **3 times every day** — completely hands-free, even when your laptop is shut down.

---

## Daily Schedule (IST)

| Slot | Time (IST) | UTC Cron | Content (5 items each = 10/post) |
|---|---|---|---|
| **Morning** | `7:00 AM IST` | `30 1 * * *` | 5 Vocabulary Words + 5 One-Word Substitutions (OWS) |
| **Afternoon** | `1:00 PM IST` | `30 7 * * *` | 5 Idioms & Phrases + 5 Synonyms & Antonyms |
| **Evening** | `7:00 PM IST` | `30 13 * * *` | 5 Homonyms & Homophones + 5 Spelling Boosters |

- **Zero Repeats**: Every posted item is saved to `data/history.json` and automatically committed back to GitHub so words never repeat.
- **Duplicate-Safe**: Each IST date + slot is tracked in `posted_log`, preventing accidental double-posting on the same day (unless `--force` is used).

---

## Step 1: Telegram Bot Setup (Skip if you already have a bot admin in `@sscstudyprephub`)

1. Open Telegram and message **`@BotFather`**.
2. Send `/newbot`, choose a display name (e.g. `SSC English Bot`) and username (e.g. `sscstudyprephub_english_bot`), and copy the **Bot Token**.
3. Open your channel **`@sscstudyprephub`** → **Channel Info** → **Administrators** → **Add Admin**.
4. Add your bot and enable the **Post Messages** permission.

*(Note: If you already created a bot for `sscstudyprephub_automation`, you can reuse that same `TELEGRAM_BOT_TOKEN`!)*

---

## Step 2: Get a Gemini API Key

1. Open [Google AI Studio API Keys](https://aistudio.google.com/api-keys).
2. Click **Create API key** and copy your key.

---

## Step 3: Push to GitHub & Configure Secrets (One-Time Setup)

1. Create a new repository on [GitHub](https://github.com/new) (e.g., `sscstudyprephub-english-bot`, Private or Public).
2. From this project folder, initialize git and push to GitHub:
   ```bash
   git init
   git add .
   git commit -m "feat: initial 3x daily SSC English Telegram automation"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/sscstudyprephub-english-bot.git
   git push -u origin main
   ```
3. Add your secrets in GitHub:
   - Open your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:
     - `TELEGRAM_BOT_TOKEN` = *(your BotFather token)*
     - `GEMINI_API_KEY` = *(your Google AI Studio key)*
     - `TELEGRAM_CHAT_ID` = `@sscstudyprephub` *(optional, defaults to `@sscstudyprephub`)*

---

## Step 4: Test Immediately (1-Click from Phone or Browser)

1. Go to your repo's **Actions** tab → **SSC English 3x Daily Telegram Posts**.
2. Click **Run workflow**:
   - Choose `slot`: `morning`, `afternoon`, or `evening`
   - First test with `dry_run`: `true` to preview the exact generated post in the workflow logs without posting to your channel.
   - Then run with `dry_run`: `false` to send a real live test post to `@sscstudyprephub`!

After that, leave it untouched — GitHub Actions runs automatically at **7:00 AM**, **1:00 PM**, and **7:00 PM IST** every day!

---

## Optional: Local Testing

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill GEMINI_API_KEY and TELEGRAM_BOT_TOKEN in .env
python -m src.main --slot morning --dry-run
```
