# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# Generates a persistent login key for civitai.com for the scraper utility
# To use:
# 1) log out from civitai if you're currently logged in
# 2) click the "login link"
# 3) enter your email address and click the button
# 4) when you receive the email, do not click the link
# 5) instead copy it (right click and select copy), & paste it below on line 29 (between the single quotes)
# 6) run this with: python civitai-auth.py
# 7) wait for the automated browser session to complete (it will auto-close when finished)
# do not run this again unless your token expires, in which case repeat from step 1

import time
from playwright.sync_api import Playwright, sync_playwright

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()

    # Open new page
    page = context.new_page()

    # paste the civitai.com login link from your email between the single quotes below
    # then run this script: python civitai-auth.py
    # civitai-auth.json should be created & you should be able to use the
    # civitai.py scraper as if you're logged in
    page.goto('')

    time.sleep(5)

    # Save storage state into the file.
    context.storage_state(path="civitai-auth.json")

    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
