# Copyright 2021 - 2024, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

import os
import logging
from PIL import Image, IptcImagePlugin
from PIL import ExifTags
from iptcinfo3 import IPTCInfo
from os.path import exists

logging.getLogger('iptcinfo').setLevel(logging.ERROR)

# returns exif data for the given filename
def read_exif(filename):
    exif_data = {}
    try:
        img = Image.open(filename)
        raw_iptc = IptcImagePlugin.getiptcinfo(img)
        exif_data = img.getexif()
    except:
        pass
    return exif_data

# prints exif data to the console
def debug_exif_data(exif):
    print('\nEXIF data:')
    for key, val in exif.items():
        if key in ExifTags.TAGS:
            print(str(key) + ': ' + ExifTags.TAGS[key] + ' : ' + str(val))

# reads IPTC data from the given filename using pillow
def read_iptc_pillow(filename):
    iptc_data = {}
    raw_iptc = {}

    try:
        img = Image.open(filename)
        raw_iptc = IptcImagePlugin.getiptcinfo(img)
    except:
        # will fail next check and return empty dict
        pass

    # IPTC fields:
    # https://www.iptc.org/std/photometadata/specification/IPTC-PhotoMetadata

    if raw_iptc:
        # title
        if (2, 5) in raw_iptc:
            iptc_data["title"] = raw_iptc[(2, 5)].decode('utf-8', errors='replace')

        # description
        if (2, 120) in raw_iptc:
            iptc_data["description"] = raw_iptc[(2, 120)].decode('utf-8', errors='replace')

        # keywords
        if (2, 25) in raw_iptc:
            keywords = raw_iptc[(2, 25)]
            d_keywords = []
            for k in keywords:
                k = k.decode('utf-8', errors='replace')
                d_keywords.append(k)
            iptc_data["keywords"] = d_keywords

        # copyright
        if (2, 116) in raw_iptc:
            iptc_data["copyright"] = raw_iptc[(2, 116)].decode('utf-8', errors='replace')

    return iptc_data

# reads IPTC data from the given filename using IPTCInfo
def read_iptc(filename):
    iptc_data = {}
    try:
        iptc_data = IPTCInfo(filename, force=True, inp_charset='utf8')
    except:
        pass
    return iptc_data

# prints IPTC data created by IPTCInfo to the console
def debug_iptc_data(iptc):
    print('\nIPTC data:')
    print(iptc)
    if iptc['object name']:
        print('object name (title): ' + iptc['object name'])
    if iptc['caption/abstract']:
        print('caption/abstract (description): ' + iptc['caption/abstract'])
    if iptc['keywords']:
        print('keywords : ')
        i = 0
        for kw in iptc['keywords']:
            i += 1
            print(' [' + str(i) + '] ' + kw)
    if iptc['copyright notice']:
        print('copyright notice (copyright): ' + iptc['copyright notice'])
    print(iptc)


# saves properly-formatted IPTCInfo dict to filename
# discards the old image data
def attach_iptc_info(filename, old_iptc):
    new_iptc = None
    try:
        new_iptc = IPTCInfo(filename)
    except:
        pass

    if new_iptc != None and old_iptc != None:
        if old_iptc['object name']:
            new_iptc['object name'] = old_iptc['object name']
        if old_iptc['caption/abstract']:
            new_iptc['caption/abstract'] = old_iptc['caption/abstract']
        if old_iptc['copyright notice']:
            new_iptc['copyright notice'] = old_iptc['copyright notice']
        if old_iptc['keywords']:
            new_iptc['keywords'] = old_iptc['keywords']

    new_iptc.save_as(filename)
    if os.path.exists(filename + '~'):
        try:
            os.remove(filename + '~')
        except:
            pass


# write the supplied metadata to the specified filename
# metadata all str except keywords which is []
# pre-existing metadata will be overwritten! (see write_iptc_info_append to preserve)
def write_iptc_info(filename, title, description, keywords, copyright):
    info = None
    try:
        info = IPTCInfo(filename)
    except:
        pass

    if info != None:
        info['object name'] = title
        info['caption/abstract'] = description
        info['copyright notice'] = copyright
        info['keywords'] = keywords

        info.save_as(filename)
        if os.path.exists(filename + '~'):
            try:
                os.remove(filename + '~')
            except:
                pass


# write the supplied metadata to the specified filename
# metadata all str except keywords which is []
# will append to any pre-existing metadata
def write_iptc_info_append(filename, title, description, keywords, copyright):
    info = None
    try:
        info = IPTCInfo(filename)
    except:
        pass

    if info != None:
        if info['object name']:
            info['object name'] += (' ' + title).encode('utf8')
        else:
            info['object name'] = title

        if info['caption/abstract']:
            info['caption/abstract'] += (' ' + description).encode('utf8')
        else:
            info['caption/abstract'] = description

        if info['copyright notice']:
            info['copyright notice'] += (' ' + copyright).encode('utf8')
        else:
            info['copyright notice'] = copyright

        if info['keywords']:
            for k in keywords:
                if k not in info['keywords']:
                    info['keywords'].append(k.encode('utf8'))
        else:
            info['keywords'] = keywords

        info.save_as(filename)
        if os.path.exists(filename + '~'):
            try:
                os.remove(filename + '~')
            except:
                pass
