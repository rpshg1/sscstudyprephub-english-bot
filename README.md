# SSC Study Prep Hub — 3x Daily English Telegram Automation

A **100% cloud-autonomous** Telegram bot pipeline powered by **GitHub Actions** + **Google Gemini (`gemini-3.8-flash`)** that posts exam-focused English capsules to `@sscstudyprephub` **3 times every day** — completely hands-free, even when your laptop is shut down.

---

## Daily Schedule (IST)

| Slot | Target Time (IST) | Off-Peak Primary + Backup Cron (UTC) | Content (5 items each = 10/post) |
|---|---|---|---|
| **Morning** | `~7:00 AM IST` | `21 1 * * *` (`6:51 AM`) + backup `51 1 * * *` (`7:21 AM`) | 5 Vocabulary Words + 5 One-Word Substitutions (OWS) |
| **Afternoon** | `~1:00 PM IST` | `21 7 * * *` (`12:51 PM`) + backup `51 7 * * *` (`1:21 PM`) | 5 Idioms & Phrases + 5 Synonyms & Antonyms |
| **Evening** | `~7:00 PM IST` | `21 13 * * *` (`6:51 PM`) + backup `51 13 * * *` (`7:21 PM`) | 5 Homonyms & Homophones + 5 Spelling Boosters |

- **Zero Repeats**: Every posted item is saved to `data/history.json` and automatically committed back to GitHub so words never repeat.
- **Duplicate-Safe Backup Triggers**: Each slot uses an off-peak primary cron and a +30 min backup cron serialized via GitHub `concurrency`. If the primary run succeeds, the backup sees today's marker in `posted_log` and skips automatically.

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

1. Go to your repo's **Actions** tab and pick one of the three workflows:
   - **Morning Dose (7:00 AM IST)**
   - **Afternoon Dose (1:00 PM IST)**
   - **Evening Dose (7:00 PM IST)**
2. Click **Run workflow**:
   - First test with `dry_run`: `true` to preview the exact generated post in the workflow logs without posting to your channel.
   - Then run with `dry_run`: `false` to send a live test post to `@sscstudyprephub`!

After that, leave it untouched — GitHub Actions runs automatically at **7:00 AM**, **1:00 PM**, and **7:00 PM IST** every day!

---

## Optional: Local Testing

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill GEMINI_API_KEY and TELEGRAM_BOT_TOKEN in .env
python -m src.main --slot morning --dry-run
```
