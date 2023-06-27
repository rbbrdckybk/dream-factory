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
search = 'recent.json'
json_file = ''

top = False
searchFound = False

# entry point
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--top",
        action='store_true',
        help="fetch the top showcase instead of recent"
    )
    parser.add_argument(
        "--file",
        default='',
        help="use this .json file instead of scraping midjourney.com"
    )
    opt = parser.parse_args()
    top = opt.top
    json_file = opt.file
    
    
def create_output(json):
    r = json
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
                
        print('Done! Wrote ' + filename)


def run(playwright: Playwright) -> None:
    # headless = True will result in being flagged as a bot
    browser = playwright.chromium.launch(headless = False)
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36')
    
    s = """
    navigator.webdriver = false
    Object.defineProperty(navigator, 'webdriver', {
    get: () => false
    })
    """

    # Open new page
    page = context.new_page()
    page.add_init_script(s)
    page.on("response", handle_response)
    try:
        page.goto(url, wait_until="networkidle")
        
    except PlaywrightTimeoutError:
        print('Exceeded 30 sec timeout waiting for partial page response, aborting...')
    else:
        page.keyboard.down('End')
    page.context.close()
    browser.close()

with sync_playwright() as playwright:
    def handle_response(response):
        global top
        global search
        global searchFound
        # the endpoint we are insterested in
        #print(response.url)

        if top:
            search = 'top.json'
        if (search in response.url):
            #resp = json.dumps(response.json(), indent=2)
            #with open('midjourney.json', 'w') as f:
            #    f.write(resp)
            
            if response.ok:
                searchFound = True
                r = response.json()
                create_output(r)
            else:
                print('Error: midjourney.com returned a non-OK response (code: ' + str(response.status) + ') (possible bot detection)!')
                #print(response.text())


    # we're scraping from midjourney.com
    if json_file == '':
        run(playwright)
        if not searchFound:
            print('Error: no response with "' + search + '" in the URL!')
      
    # we have a .json file
    else:
        lines = ''
        with open(json_file, 'r', encoding="utf-8") as f:
            json_data = json.load(f)
        create_output(json_data)
