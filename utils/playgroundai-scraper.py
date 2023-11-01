# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

# simple playground.ai user gallery prompt scraper utility
# usage instructions: python playgroundai-scraper.py --help

# examples:

# scrape the 'trending' section of playgroundai.com and save the prompts in your Dream Factory prompts folder
# python playgroundai-scraper.py --outdir "..\prompts"

# scrape the 'category:animals' section of playgroundai.com, and include header/footer files in the output
# python playgroundai-scraper.py --mode category --param "animals" --outdir "..\prompts" --header "resources\sample-header.txt" --footer "resources\sample-footer.txt"

# scrape the search page of playgroundai.com for 'delicious cake', include a header file in the output, and filter size & scale info
# python playgroundai-scraper.py --mode search --param "delicious cake" --no_size --no_scale --outdir "..\prompts" --header "resources\sample-header.txt"


from datetime import datetime
import argparse
import requests
import unicodedata
import json
import time
import os
import re
from os.path import exists

# scrapes the specified URL and returns a json object
def scrape(url):
    response = None
    target_start = '<script id="__NEXT_DATA__" type="application/json">'
    target_end = '</script>'

    print('Requesting ' + url + '...')
    page = requests.get(url)
    if target_start in page.text and target_end in page.text:
        print('Extracting JSON data from HTML...')
        data = page.text.split(target_start, 1)[1]
        data = data.split(target_end, 1)[0]
        response = json.loads(data)
    else:
        print('Error: target JSON data not found! Maybe re-try later? Exiting...')
        exit(-1)
    return response


# dumps formatted json data to a file for debugging
def dump_json_to_file(data):
    with open('playgroundai-data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# fixes common formatting issues in user prompts
def sanitize_prompt(p):
    while '  ' in p:
        p = p.replace('  ', ' ')
    while ',,' in p:
        p = p.replace(',,', ',')
    while ' ,' in p:
        p = p.replace(' ,', ',')
    while '.,' in p:
        p = p.replace('.,', ',')
    while ', ,' in p:
        p = p.replace(', ,', ',')
    while '8 k' in p:
        p = p.replace('8 k', '8k')
    while '4 k' in p:
        p = p.replace('4 k', '4k')
    # regex to force a space after commas and periods (except in decimal #s)
    #p = re.sub(r'(?<=[.,])(?=[^\s])', r' ', p).strip()
    p = re.sub(r'(?<=[,])(?=[^\s])', r' ', p).strip()
    p = re.sub('\.(?!\s|\d|$)', '. ', p).strip()

    while ', ,' in p:
        p = p.replace(', ,', ',')
    if p.endswith(','):
        p = p[:-1]
    return p


# Taken from https://github.com/django/django/blob/master/django/utils/text.py
# Using here to make filesystem-safe directory names
def slugify(value, allow_unicode=False):
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    value = re.sub(r'[-\s]+', '-', value).strip('-_')
    # added in case of very long filenames due to multiple prompts
    return value[0:160]


# creates a dictionary of unique prompts, given the scraped json data
def create_prompt_list(data, opt):
    count = 0
    prompts = {}

    for job in data["props"]["pageProps"]["data"]:
        if "prompt" in job and job['prompt'] != None and job['prompt'] != '':
            key = ''
            prompt = ''
            if "id" in job and job['id'] != None and job['id'] != '':
                #key = '# https://playgroundai.com/post/' + job['id'] + '\n'
                key = job['id']
            if not opt.no_size:
                if "width" in job:
                    prompt += '!WIDTH = ' + str(job['width']) + '\n'
                if "width" in job:
                    prompt += '!HEIGHT = ' + str(job['height']) + '\n'

            if not opt.no_scale:
                if "cfg_scale" in job:
                    prompt += '!SCALE = ' + str(job['cfg_scale']) + '\n'

            if not opt.no_neg:
                if "negative_prompt" in job and job['negative_prompt'] != None:
                    if job['negative_prompt'] != '':
                        np = job['negative_prompt'].replace('\n', '').strip()
                        np = sanitize_prompt(np)
                        prompt += '!NEG_PROMPT = ' + np + '\n'

            p = job['prompt'].replace('\n', '').strip()
            if p.startswith('['):
                p = 'image of ' + p
            p = sanitize_prompt(p)
            prompt += '\n' + p + '\n\n'
            if prompt not in prompts.values():
                prompts[key] = prompt
        count += 1

    print('Found ' + str(count) + ' prompts in JSON data...')
    print('After removing dupes, there are ' + str(len(prompts)) + ' unique prompts...')
    return prompts


# write the output file - data is the prompt dictionary and opt are the command-line args
def write_output(data, opt):
    date = datetime.today().strftime('%Y-%m-%d')
    desc = opt.mode.lower().strip()
    if desc == 'category':
        desc = 'cat-' + slugify(opt.param.lower().strip())
    if desc == 'search':
        desc = 'search-' + slugify(opt.param.lower().strip())
    output_file = 'playgroundai-' + desc + '-' + str(date) + '.prompts'
    if opt.outdir != '':
        if os.path.exists(opt.outdir):
            output_file = os.path.join(opt.outdir, output_file)
        else:
            print('Warning: specified --outdir does not exist; ignoring it!')

    print('Writing output file "' + output_file + '"...')
    with open(output_file, 'w', encoding='utf-8') as f:
        # write header if necessary
        if opt.header != '':
            if os.path.exists(opt.header):
                lines = ''
                with open(opt.header, 'r', encoding="utf-8") as h:
                    lines = h.readlines()
                for line in lines:
                    f.write(line)
            else:
                print('Warning: --header file "' + opt.header + '" does not exist; ignoring it!')
        f.write('[prompts]\n\n')
        f.write('#####################################################################################################################################\n')
        f.write('### Dream Factory standard .prompts file\n')
        f.write('### Created with playground-scraper.py on ' + str(date) + '\n')
        f.write('### ' + str(len(data)) + ' unqiue prompts scraped from: ' + url.replace(' ', '+') + '\n')
        f.write('#####################################################################################################################################\n\n')
        for key, value in data.items():
            if key != '':
                f.write('# https://playgroundai.com/post/' + key + '\n')
            f.write(value)

        # write footer if necessary
        if opt.footer != '':
            if os.path.exists(opt.footer):
                lines = ''
                with open(opt.footer, 'r', encoding="utf-8") as h:
                    lines = h.readlines()
                for line in lines:
                    f.write(line)
            else:
                print('Warning: --footer file "' + opt.footer + '" does not exist; ignoring it!')


# entry point
if __name__ == '__main__':
    print('\nStarting...')
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        default='trending',
        help="the area of playgroundai.com to scrape - trending (default), category, or search"
    )
    parser.add_argument(
        "--param",
        default='',
        help="required when setting --mode to 'category' or 'search'; desired search/category parameter"
    )
    parser.add_argument(
        "--no_neg",
        action='store_true',
        help="do not include negative prompts in output"
    )
    parser.add_argument(
        "--no_size",
        action='store_true',
        help="do not include image width/height size info in output"
    )
    parser.add_argument(
        "--no_scale",
        action='store_true',
        help="do not include guidance scale in output"
    )
    parser.add_argument(
        "--outdir",
        default='',
        help="output folder location (must exist!), default is current folder"
    )
    parser.add_argument(
        "--header",
        default='',
        help=".txt file containing text to prepend output .prompts file with"
    )
    parser.add_argument(
        "--footer",
        default='',
        help=".txt file containing text to append output .prompts file with"
    )
    parser.add_argument(
        "--file",
        default='',
        help="use this .json file instead of scraping playgroundsai.com (for debugging)"
    )
    opt = parser.parse_args()

    url = "https://playgroundai.com/"

    if opt.mode.lower().strip() == 'pure':
        # we're scraping the pure-prompt section
        url += 'pure-prompt'
    elif opt.mode.lower().strip() == 'category':
        # we're scraping a category
        if opt.param != '':
            url += 'c/' + opt.param.lower().strip()
        else:
            print('You must specify a category to scrape via the --param parameter! Exiting...')
            exit(-1)

    elif opt.mode.lower().strip() == 'search':
        # we're scraping a search term
        if opt.param != '':
            url += 'search?q=' + opt.param.lower().strip()
        else:
            print('You must specify a search term to scrape via the --param parameter! Exiting...')
            exit(-1)
    else:
        # default to scraping the trending section
        opt.mode = 'trending'
        url += 'feed'

    # scrape the data
    data = None
    if opt.file == '':
        data = scrape(url)
        #dump_json_to_file(data)
    else:
        if os.path.exists(opt.file):
            with open(opt.file, 'r', encoding="utf-8") as f:
                print('Loading data from file "' + opt.file + '"...')
                data = json.load(f)
        else:
            print('Specified --file "' + opt.file + '" does not exist! Exiting...')
            exit(-1)

    # create list of unique prompts
    prompts = create_prompt_list(data, opt)

    # write the output file
    write_output(prompts, opt)

    print('Done!')
    exit(0)
