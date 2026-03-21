# Ralphify Cowork

Put your AI on autopilot. This skill lets you set up autonomous AI coding loops right from Claude Cowork — no coding experience needed.

Tell your AI what you want done ("keep writing tests", "clean up my code", "fix all the bugs"), and it sets up a loop that keeps working automatically, round after round, until the job is done.

## What it does

- Installs ralphify for you (one-time setup)
- Creates an automation from a plain-English description
- Runs it safely (one round first, so you can see what happens)
- Helps you tweak it if the results aren't quite right
- Manages all your automations in one place

You never have to touch config files, write code, or learn terminal commands. Just describe what you want.

## Install in Cowork

### Step 1: Allow internet access

Cowork needs permission to fetch the skill from GitHub.

1. Open your Cowork **project settings**
2. Find **Domain allowlist**
3. Set it to **All domains**

### Step 2: Ask Cowork to install it

Paste this into your Cowork chat:

> Please install this skill:
> https://github.com/computerlovetech/ralphify/tree/main/skills/ralphify-cowork

Cowork will fetch the skill and set it up for you. Once installed, you'll see **ralphify-cowork** in your skills list.

## How to use it

After installing, just type in your Cowork chat:

> /ralphify-cowork

It will ask you what you want to automate. Here are some ideas:

- "Keep writing tests until my code is fully covered"
- "Clean up and improve my codebase while I'm away"
- "Fix all the linting errors across my project"
- "Write documentation for every module"
- "Keep improving my website until it looks professional"

The skill handles everything from there — it figures out your project setup, creates the automation, and walks you through running it.

## What happens behind the scenes

Each "round" of your automation:

1. Checks the current state of your project (tests, linting, recent changes)
2. Picks the next piece of work to do
3. Does the work
4. Makes sure nothing is broken
5. Saves the progress
6. Repeats

You can let it run for one round, five rounds, or let it keep going until you stop it.

## FAQ

**Do I need to know how to code?**
No. The skill handles all the technical setup. You just describe what you want in plain English.

**Is it safe?**
Yes. It always starts with a single test round so you can see what the AI does before letting it run on its own. All changes are saved in git, so nothing is ever lost.

**What if it does something I don't want?**
Just tell it. Say "it's changing files I don't want it to touch" or "the changes are too big" and it will adjust.

**What projects does it work with?**
Python, TypeScript/JavaScript, Rust, Go, and most other languages. It automatically detects your project setup.

**What is ralphify?**
[Ralphify](https://ralphify.co) is an open-source tool that runs AI coding agents in autonomous loops. This skill makes it accessible to everyone through Cowork.
