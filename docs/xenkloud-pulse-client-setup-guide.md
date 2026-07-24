# Connecting Your AWS Account to Xenkloud Pulse

This takes about 5 minutes. You're creating a **read-only** access key — Xenkloud Pulse can see your billing and resource data, but it can never change, delete, or create anything in your AWS account.

---

## Step 1: Log in to AWS

Go to [console.aws.amazon.com](https://console.aws.amazon.com) and log in with your usual AWS account (use your main/root login or an admin user).

## Step 2: Open the IAM service

- In the search bar at the top of the page, type **IAM** and click on it.
- This is the page where AWS manages who can access what.

## Step 3: Create a new user

1. In the left sidebar, click **Users**.
2. Click the **Create user** button (top right).
3. Name it something clear, like `xenkloud-pulse-readonly`.
4. Click **Next**.

## Step 4: Attach read-only permissions

1. Choose **Attach policies directly**.
2. In the search box, find and check these three policies:
   - `ReadOnlyAccess` for Cost Explorer (search "Billing" or "Cost")
   - `AmazonEC2ReadOnlyAccess`
   - `CloudWatchReadOnlyAccess`
3. Click **Next**, then **Create user**.

*(If your AWS admin/IT person prefers, you can just forward this page to them — it's a 2-minute task for anyone familiar with AWS.)*

## Step 5: Generate an access key

1. Click on the user you just created (`xenkloud-pulse-readonly`).
2. Go to the **Security credentials** tab.
3. Scroll to **Access keys** and click **Create access key**.
4. Choose **Third-party service** as the use case.
5. Click through to **Create access key**.
6. You'll see two values:
   - **Access key ID**
   - **Secret access key**

⚠️ **Copy both values now** — AWS only shows the secret key once.

## Step 6: Send us the keys securely

Do **not** email these keys in plain text. Instead:

- Use the secure upload link we send you, **or**
- Share them via a password manager's secure share feature (1Password, Bitwarden), **or**
- If neither is available, split them across two separate messages (e.g., one in email, one in a text message)

## What happens next

We'll connect your account, and within 24 hours you'll get your first cost report — what you're spending, any unusual spikes, and specific ways to save money.

## Revoking access (anytime)

You're always in control. To disconnect us at any point:
1. Go back to **IAM → Users → xenkloud-pulse-readonly**
2. Click **Delete** (or just deactivate the access key under Security credentials)

That's it — access is gone immediately.

---

**Questions?** Reply to this document or reach out directly — happy to walk through this live on a call if that's easier.
