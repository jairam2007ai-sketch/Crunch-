# Deploying Crunch (step by step)

The whole system runs as **one Render web service** built from this repository's `Dockerfile`: the API plus
the buyer, seller and admin websites. Data lives in a free **Supabase** Postgres database (Neon works too).

```
GitHub repo ──push──▶ Render (Docker: API + 3 websites) ──▶ Supabase Postgres (orders, accounts, stock)
```

When it's done:

| Site | Address |
|---|---|
| Customers | `https://crunch-fvol.onrender.com/` |
| Sellers | `https://crunch-fvol.onrender.com/seller/` |
| Owner | `https://crunch-fvol.onrender.com/admin/` |

(Use your own service's address if it's different. It's shown at the top of the service page in Render.)

---

## 1. Get the database address from Supabase

1. Open your project at [supabase.com/dashboard](https://supabase.com/dashboard).
2. Click **Connect** at the top of the project page.
3. Under **Connection String**, choose **Session pooler**. Don't use **Direct connection**: it needs IPv6, which Render doesn't have.
4. Copy the string. It looks like this:
   `postgresql://postgres.abcdefghijkl:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`
5. Replace `[YOUR-PASSWORD]`, including the square brackets, with your database password.
   Forgot it? Go to **Project Settings → Database → Reset database password**.

Don't use the **Project URL** (`https://….supabase.co`) or the **API keys**. Those are for a different purpose.

**Using Neon instead?** In [neon.tech](https://neon.tech), open **Connect**, choose **Connection string**, and
copy the line starting with `postgresql://`. Its password is already filled in.

**Optional: test the address on your computer first.** In the `crunch` folder, run:

```
backend\.venv\Scripts\python -m app.cli check-db "postgresql://...your string..."
```

`OK: connected to ...` means it will work on Render too. Otherwise it tells you what's wrong.

## 2. Set the Render service to Docker

In [dashboard.render.com](https://dashboard.render.com), open the **Crunch** service, then go to **Settings**.

1. **Build → Source → Edit**: set **Runtime** to **Docker**, set **Dockerfile Path** to `./Dockerfile`, and leave **Root Directory** empty. Save.
2. **Health Checks**: set **Health Check Path** to `/api/health`.
3. **Auto-Deploy**: set it to **On Commit**, so every `git push` updates the live site.

## 3. Add the environment variables

Go to **Environment** and add these four variables. Delete any other `DATABASE_URL` entry first.

| Key | Value |
|---|---|
| `DATABASE_URL` | the full string from step 1, starting with `postgresql://`. No quotes, no `psql`. |
| `JWT_SECRET` | click **Generate** |
| `OWNER_EMAIL` | the email you'll sign in with |
| `OWNER_PASSWORD` | your sign-in password: 8+ characters, not a common password, and not containing your name or email. Three random words work well, like `mango-river-chips`. |

Click **Save, rebuild, and deploy**, or **Save** and then do step 4.

Don't add `ENV`, `PORT` or `CORS_ORIGINS`; the Dockerfile and Render already set them. Optional extras, like the AI
assistant's `AI_PROVIDER`, `AI_API_KEY` and `AI_MODEL`, are covered in the README.

## 4. Deploy

1. Go to **Manual Deploy → Deploy latest commit**.
2. Watch the **Logs** tab. The first build takes about 3–5 minutes.
3. It worked when the status says **Live** and the log has no `RuntimeError`.
4. Open `https://crunch-fvol.onrender.com/api/health`. It should show `{"ok":true}`.

If it fails, scroll to the **bottom** of the log. The line starting with `RuntimeError:` names the problem;
see [Troubleshooting](#troubleshooting).

## 5. After the first successful deploy

1. Sign in at `/admin/` with `OWNER_EMAIL` and `OWNER_PASSWORD`.
2. In Render, **delete `OWNER_PASSWORD`** from Environment. The account already exists, and the server warns while the password is still there.
3. In the admin site:
   - **Settings**: your UPI ID, so customers can pay online; a pickup note, like where the cart stands; and your daily goal.
   - **Menu & prices**: your cost per packet, to see profit.
   - **Team**: add each seller with their own email and password. Sellers can't use your email or password.
   - **Stock**: record your first delivery, so the site warns you when things run low.
4. Share the links: customers get the main address; sellers get `/seller/`.
5. Place one test order from your phone, then cancel it.

## 6. Updating the live site

Change the code on your computer, test it with `start.bat`, then:

```
git add -A
git commit -m "Describe the change"
git push
```

Render rebuilds and goes live in a few minutes. Your data in Supabase is untouched.

## 7. Free-plan facts

- **Render free** sleeps after 15 minutes without visitors, so the next visit waits about 50 seconds. To keep it
  awake during selling hours, add a free monitor at [uptimerobot.com](https://uptimerobot.com) for
  `https://crunch-fvol.onrender.com/api/health` every 5 minutes. One always-on free service fits Render's monthly free hours.
- **Supabase free** pauses a project after about a week with no database use. Daily orders keep it awake. If it
  pauses, click **Restore** in the Supabase dashboard.
- **Backups**: Supabase keeps daily backups on paid plans only. On the free plan, use **Database → Backups** to download
  one now and then.

## Troubleshooting

Find the message at the bottom of Render's **Logs**.

| You see | Fix |
|---|---|
| `Could not open requirements file` | The service is still a Python service. Do step 2 (Runtime: Docker). |
| `DATABASE_URL is a website address` | You pasted the Project URL (`https://…`). Use the Session pooler string (step 1). |
| `DATABASE_URL looks like an API key` | You pasted an API key. Use the Session pooler string (step 1). |
| `still has the [YOUR-PASSWORD] placeholder` | Replace `[YOUR-PASSWORD]` (with the brackets) by your database password. |
| `DATABASE_URL isn't set` | Add `DATABASE_URL` (step 3). |
| `...supabase.co ... IPv6` or `Network is unreachable` | You used the Direct connection. Copy the **Session pooler** string instead. |
| `password is wrong` | Reset the database password in Supabase and update `DATABASE_URL`. |
| `Tenant or user not found` | Copy the Session pooler string exactly: the user name looks like `postgres.abcdefghijkl`. |
| `didn't answer` / `timeout` | The Supabase project may be paused. Restore it, then redeploy. |
| `JWT_SECRET must be a random value` | Add `JWT_SECRET` and click **Generate** (step 3). |
| `No owner account yet` | Add `OWNER_EMAIL` and `OWNER_PASSWORD` (step 3). |
| `OWNER_PASSWORD isn't strong enough` | Choose a longer password without your name or email. |
| Site loads very slowly the first time | The free service was asleep. It's fast again after the first visit. |

Still stuck? Send a screenshot of the last 20 lines of the log.
