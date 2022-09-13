# Copyright 2021 - 2022, Bill Kennedy
# SPDX-License-Identifier: MIT

import threading
import time
import datetime
import shlex
import subprocess
import sys
import unicodedata
import re
import random
import os
from os.path import exists
from datetime import datetime as dt
from datetime import date
from pathlib import Path
from collections import deque
from PIL.PngImagePlugin import PngImageFile, PngInfo


# for easy reading of prompt/config files
class TextFile():
    def __init__(self, filename):
        self.lines = deque()
        if exists(filename):
            with open(filename) as f:
                l = f.readlines()

            for x in l:
                # remove newline and whitespace
                x = x.strip('\n').strip();
                # remove comments
                x = x.split('#', 1)[0].strip();
                if x != "":
                    # these lines are actual prompts
                    self.lines.append(x)

    def next_line(self):
        return self.lines.popleft()

    def lines_remaining(self):
        return len(self.lines)


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
    return value[0:180]


# gets just filename from absolute path
def filename_from_abspath(fpath):
    filename = fpath
    if '\\' in fpath:
        filename = fpath.rsplit('\\', 1)[1]
    elif '/' in fpath:
        filename = fpath.rsplit('/', 1)[1]
    return filename

# gets just path from absolute path + filename
def path_from_abspath(fpath):
    path = fpath
    if '\\' in fpath:
        path = fpath.rsplit('\\', 1)[0]
    elif '/' in fpath:
        path = fpath.rsplit('/', 1)[0]
    return path
