# Customize Your Crunch: Business Manager

Three websites and one API for the Crunch snack cart.

| Website | Address | Who uses it | What it does |
|---|---|---|---|
| **Buyer** | `/` | Customers, on their phones | Menu, 3D packet builder, order ahead, live order tracking, UPI pay link |
| **Seller** | `/seller/` | The team at the cart (seller accounts only) | Point of sale (cash/UPI with change calculator), order queue with a beep for new online orders, refund requests, stock |
| **Admin** | `/admin/` | The owner (owner accounts only) | Everything: the same point of sale and queue, plus dashboard and charts, all orders, refund approvals, AI business assistant, prices and costs, stock, team accounts, activity log, settings |

**Accounts are kept apart.** Each seller signs in on the seller site with their own email and password. A seller can't be given the owner's email or password, and the owner's account doesn't work on the seller site. The owner signs in on the admin site, which can do everything the seller site can. Every password field has an eye button to show what you typed.

Built with the stack from the architecture plan, using only free and open-source tools:
Vue 3 + Tailwind CSS + Vite (websites), FastAPI + SQLAlchemy (API), PostgreSQL on Supabase or Neon (database),
and OpenRouter, Ollama or Hugging Face (free AI models).

```
frontend/   the three websites (one Vite project, three pages)
backend/    FastAPI server, database models, AI assistant, tests
Dockerfile  builds everything into one container for hosting
render.yaml one-click setup for Render's free tier
start.bat   double-click to run everything on this computer
public-link.bat  double-click to get a temporary public link (Cloudflare)
index.html  the earlier one-page version (claude.ai page); not used by this system
```

---

## Run it on your computer

You need **Python 3.10+** and **Node.js 20.19+**.

**The easy way (Windows):** double-click **`start.bat`** in this folder. The first time, it installs everything. Then it opens the sites in your browser, and the admin site asks you to create your owner account:

- Buyer: http://127.0.0.1:8000/
- Seller: http://127.0.0.1:8000/seller/
- Admin: http://127.0.0.1:8000/admin/

Keep its window open while you use the sites, and close it to stop. Don't open the `.html` files directly; they only work through the server.

**The manual way** (also for Mac/Linux, or while changing the code):

**1. Start the API** (first time only: the `venv` and `pip` lines)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Mac/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env            # Mac/Linux: cp .env.example .env

python -m app.cli create-owner --email you@example.com --name "Your Name"
python -m app.cli create-seller --email helper@example.com --name "Helper"

uvicorn app.main:app --reload
```

It asks you to type each password privately. The API runs at http://127.0.0.1:8000, and the full API reference is at http://127.0.0.1:8000/api/docs. For safety it opens only on this computer.

Security is covered in [SECURITY.md](SECURITY.md).

**2. Start the websites** in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:
- Buyer: http://localhost:5173/
- Seller: http://localhost:5173/seller/
- Admin: http://localhost:5173/admin/

**Want sample data to try the dashboards?** Point the API at a separate test database first, so fake orders never mix with real ones:

```bash
set DATABASE_URL=sqlite:///./demo.db        # Mac/Linux: export DATABASE_URL=sqlite:///./demo.db
python -m app.cli create-owner --email demo@example.com --name Demo --password demo-pass-123
python -m app.cli demo-data --days 14 --yes
```

**Run the tests:** `cd backend` then `pytest` (40 tests: money, permissions, stock, refunds, the AI assistant).

---

## Share it online today (temporary)

With `start.bat` running, double-click **`public-link.bat`**. It uses Cloudflare's free tunnel, with no account needed, and prints a link like `https://some-words.trycloudflare.com`. Anyone can open it on their phone:

- Customers: the link
- Sellers: the link + `/seller/`
- Owner: the link + `/admin/`

It only works while this computer is on and both windows are open, and the link changes every time. Use it to try things with your team, then move to the permanent setup below.

Create your owner account on this computer first (http://127.0.0.1:8000/admin/). For safety, the first-run account form refuses anyone coming through the public link.

## Put it online for free (permanent)

The simplest setup is **one Render web service** running the Dockerfile. It serves the API and all three websites from one address, with the database on **Supabase** or **Neon**.

1. **Database.** Create a free project on [Neon](https://neon.tech) and copy its connection string (it starts with `postgresql://` and ends with `?sslmode=require`). Supabase works too, but use its **Session pooler** connection string: Supabase's direct address needs IPv6, which Render doesn't support.
2. **Code.** Put this folder in a GitHub repository. The `.gitignore` keeps passwords, databases and build files out.
3. **Render.** At [render.com](https://render.com) choose **New → Blueprint** and pick your repository. Render reads `render.yaml`, builds with **Docker**, and asks for:
   - `DATABASE_URL`: the string from step 1
   - `OWNER_EMAIL` and `OWNER_PASSWORD`: your login, created on the first start. Use three random words; the server refuses easy passwords.
   - `AI_API_KEY` and `AI_MODEL`: optional (see below)
4. **After the first deploy,** delete `OWNER_PASSWORD` from Render's environment settings. Then sign in at `https://your-app.onrender.com/admin/` and add your sellers on the **Team** page.

**Already made a plain Python web service on Render?** Its build fails with `Could not open requirements file`. Switch it to Docker instead of starting again:
1. **Settings → Build → Source → Edit**, choose **Runtime: Docker**, leave the Dockerfile path as `./Dockerfile`, and click **Deploy**.
2. **Environment**, add these variables:

   | Key | Value |
   |---|---|
   | `JWT_SECRET` | click **Generate** |
   | `DATABASE_URL` | your Neon connection string |
   | `OWNER_EMAIL` | your email |
   | `OWNER_PASSWORD` | a strong password, removed after the first successful deploy |

The server checks its settings at start. If one is missing or weak, it stops, and the **Logs** tab says in plain words what to fix.

Things to know:
- Render's free service **sleeps after 15 minutes without visitors**, so the first visit after that takes about a minute. A free [UptimeRobot](https://uptimerobot.com) check on `/api/health` every 10 minutes keeps it awake while the cart is open.
- **Always use Supabase or Neon in production.** Render's own disk is wiped on every deploy, so a SQLite file there would lose your orders.
- Railway and Fly.io also run the same Dockerfile.

**Websites on Vercel or Netlify instead** (the API stays on Render):
1. In Vercel or Netlify, import the same GitHub repository and set the **root directory** to `frontend`. `vercel.json` and `netlify.toml` are already there.
2. Add the environment variable `VITE_API_URL` = your Render address, for example `https://crunch.onrender.com`.
3. On Render, add `CORS_ORIGINS` = your Vercel or Netlify address, for example `https://crunch.vercel.app`.
4. The sites are then at `https://crunch.vercel.app/`, `/seller/` and `/admin/`.

---

## The AI assistant

It is on the admin site, under **AI assistant**. It answers from your real numbers by calling tools: today's sales, a past date, Regular vs Loaded, cash vs UPI, refunds, stock, top picks, period comparison, profit, daily report and order lookup.

It can also **prepare actions**: approve a refund, refund money on an order, or open or close online ordering. Nothing happens until you press **Confirm**, and each confirmed action is recorded in the activity log.

| Mode | Cost | Setup in `.env` (or your host's environment settings) |
|---|---|---|
| Basic (default) | Free, no internet needed | Nothing. It understands common questions like "today's sales", "compare this week" or "any low stock". |
| OpenRouter | Free models available | `AI_PROVIDER=openrouter`, `AI_API_KEY=` your key from openrouter.ai, `AI_MODEL=` a free model that supports tool calling (its id ends in `:free`; free models change, so pick a current one at openrouter.ai/models) |
| Ollama | Free, runs on your computer | Install Ollama, run `ollama pull llama3.1`, then set `AI_PROVIDER=ollama` |
| Hugging Face | Free tier, limited | `AI_PROVIDER=huggingface`, `AI_API_KEY=` your HF token, `AI_MODEL=` a chat model with tool support |

If the model doesn't answer, the assistant falls back to basic mode and says so.

---

## How the business rules work

- **Prices are set by the server.** The websites send what the customer picked, and the API works out the price from the menu, so nobody can change a price in their browser.
- **Menu limits:** Regular gets 1 base, up to 2 toppings, 1 sauce and 1 seasoning. Loaded gets up to 3 toppings, 2 sauces, 2 seasonings and cheese. Change prices on **Menu & prices**.
- **Order numbers** restart at 1 every day (shop time, India).
- **Sales collected** counts paid orders only. Online "pay at the cart" orders show as *unpaid* until the seller taps **Paid cash** or **Paid UPI**.
- **Refunds:** sellers ask, and the owner approves. A refund is counted on the day it's approved. A paid order must be refunded before it can be cancelled.
- **Profit** appears once you enter a **cost per packet** for each size on **Menu & prices**.
- **Stock** is counted in portions (one portion goes into one Regular packet; Loaded uses 1.5 portions of chips). Counting starts for an item the first time someone records a delivery. When an item runs out, customers see it as sold out. Cancelling an order puts its stock back.
- **Permissions:** sellers never see profit or costs, and can't approve refunds, change prices or overwrite stock counts. Every change is in the **Activity** log.
- **Online ordering** can be opened or closed from the seller site (top right) or the admin dashboard. Each phone number and internet connection is limited to 5 online orders per 10 minutes to stop junk orders.

---

## Before you go live (checklist)

- [ ] `JWT_SECRET` is a long random value (Render generates one for you)
- [ ] `DATABASE_URL` points at Supabase or Neon
- [ ] Owner account created, and `OWNER_PASSWORD` removed from the host settings
- [ ] UPI ID entered on **Settings** (or leave it empty for pay-at-cart only)
- [ ] Cost per packet entered on **Menu & prices**, to see profit
- [ ] First stock delivery recorded on **Stock**
- [ ] Sellers added on **Team**
- [ ] Try one test order on a phone, then cancel it
