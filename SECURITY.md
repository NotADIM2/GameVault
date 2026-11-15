# Security policy

## Reporting a vulnerability

**Please don't report security problems in public issues, discussions or pull requests.**

Use [private vulnerability reporting](https://github.com/NotADIM2/GameVault/security/advisories/new) instead. Only the maintainer can see these reports.

Please include:

- what the problem is and where it is (file, route or page)
- steps to reproduce it
- what an attacker could do with it

You'll get a reply within a few days. Once it's fixed, you'll be credited in the advisory unless you'd rather stay anonymous.

## Scope

In scope: the code in this repository, including the Flask app, the database schema and its security rules, and the seed scripts.

Out of scope: denial-of-service, spam, social engineering, and vulnerabilities in third-party services (Supabase, GitHub, Steam) that aren't caused by this project.

## Keeping your own setup safe

- Never commit your `.env` file or paste keys into issues, pull requests or screenshots.
- The `SUPABASE_KEY` in `.env` is a secret key. Keep it on the server only.
- Test other people's pull requests against a separate Supabase project, not one holding real data.
