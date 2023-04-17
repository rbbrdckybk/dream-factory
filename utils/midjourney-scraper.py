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
import argparse

url = "https://www.midjourney.com/showcase/recent/"
top = False

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--top",
        action='store_true',
        help="fetch the top showcase instead of recent"
    )
    opt = parser.parse_args()
    top = opt.top


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
        global top
        # the endpoint we are insterested in
        #print(response.url)
        search = 'recent.json'
        if top:
            search = 'top.json'
        if (search in response.url):
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
                        if '--ar' in prompt:
                            prompt = prompt.split('--ar', 1)[0].strip()
                        while prompt.endswith(','):
                            prompt = prompt[:-1]
                        while prompt.startswith('*'):
                            prompt = prompt[1:]
                        if prompt.lower().startswith('/imagine'):
                            prompt = prompt[8:].strip()
                        if '<<<' in prompt and '>>>' in prompt:
                            start = prompt.split('<<<', 1)[0]
                            end = prompt.split('>>>', 1)[1]
                            prompt = start + ' ' + end
                        prompt = prompt.strip()
                        prompts.append(prompt)

                prompts = list(set(prompts))
                prompts.sort()

                date = datetime.today().strftime('%Y-%m-%d')
                filename = 'midjourney-' + date + '.prompts'
                if top:
                    filename = 'midjourney-showcase-top.prompts'
                with open(filename, 'w', encoding="utf-8") as f:
                    f.write('[config]\n\n!MODE = standard\n!REPEAT = yes\n\n!WIDTH = 1024\n!HEIGHT = 1024\n')
                    f.write('!HIGHRES_FIX = yes\n!STRENGTH = 0.68\n!FILENAME = <model>-<date>-<time>\n')
                    f.write('!AUTO_INSERT_MODEL_TRIGGER = end\n\n!CKPT_FILE = # add model(s) here')
                    f.write('\n\n[prompts]\n\n')
                    for prompt in prompts:
                        f.write(prompt + '\n\n')


    run(playwright)
