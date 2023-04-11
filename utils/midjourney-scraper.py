# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# simple Midjourney showcase prompt scraper utility
# usage: python midjourney-scraper.py

# This requires Playwright, which can be installed with these commands:
# pip3 install playwright
# playwright install

from playwright.sync_api import Playwright, sync_playwright
from datetime import datetime
import time
import json

url = "https://www.midjourney.com/showcase/recent/"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless = True)

    # Open new page
    page = browser.new_page()
    page.on("response", handle_response)
    page.goto(url, wait_until="networkidle")
    page.keyboard.down('End')
    page.context.close()
    browser.close()

with sync_playwright() as playwright:
    def handle_response(response):
        # the endpoint we are insterested in
        #print(response.url)
        if ("recent.json" in response.url):
            #resp = json.dumps(response.json(), indent=2)
            #with open('midjourney.json', 'w') as f:
            #    f.write(resp)

            r = response.json()
            count = 0
            prompts = []

            if r["pageProps"]["jobs"]:
                for job in r["pageProps"]["jobs"]:
                    if "prompt" in job and job["prompt"] is not None:
                        count += 1
                        prompt = job["prompt"].replace('\n', '').strip()
                        if prompt.startswith('['):
                            prompt = 'image of ' + prompt
                        while prompt.endswith(','):
                            prompt = prompt[:-1]
                        prompt = prompt.strip()
                        prompts.append(prompt)

                prompts = list(set(prompts))
                date = datetime.today().strftime('%Y-%m-%d')
                filename = 'midjourney-' + date + '.prompts'
                with open(filename, 'w', encoding="utf-8") as f:
                    f.write('[config]\n\n!MODE = standard\n!REPEAT = yes\n\n!WIDTH = 1024\n!HEIGHT = 1024\n')
                    f.write('!HIGHRES_FIX = yes\n!STRENGTH = 0.68\n!FILENAME = <model>-<date>-<time>\n')
                    f.write('!AUTO_INSERT_MODEL_TRIGGER = end\n\n!CKPT_FILE = # add model(s) here')
                    f.write('\n\n[prompts]\n\n')
                    for prompt in prompts:
                        f.write(prompt + '\n\n')

    run(playwright)
