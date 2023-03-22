# Copyright 2021 - 2023, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
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
        iptc_data = IPTCInfo(filename, force=True, inp_charset='utf-8')
    except:
        pass
    return iptc_data

# prints IPTC data created by Pillow to the console
def debug_iptc_data_pillow(iptc):
    print('\nIPTC data:')
    for k, v in iptc.items():
        if k == 'keywords':
            print(str(k) + ' : ')
            i = 0
            for kw in v:
                i += 1
                print(' [' + str(i) + '] ' + kw)
        else:
            print(str(k) + ' : ' + str(v))

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

# write the supplied pillow-generated IPTC metadata to the specified filename
def write_iptc_info_from_pillow(filename, iptc):
    info = None
    try:
        info = IPTCInfo(filename)
    except:
        pass

    if info != None:
        if iptc['title']:
            info['object name'] = iptc['title']
        if iptc['description']:
            info['caption/abstract'] = iptc['description']
        if iptc['keywords']:
            info['keywords'] = iptc['keywords']
        if iptc['copyright']:
            info['copyright notice'] = iptc['copyright']
        info.save_as(filename)

        if os.path.exists(filename + '~'):
            try:
                os.remove(filename + '~')
            except:
                pass

# write the supplied metadata to the specified filename
# metadata all str except keywords which is []
# if the first char is a '+' metadata will be appended instead of replaced
def write_iptc_info(filename, title, description, keywords, copyright):
    info = None
    try:
        info = IPTCInfo(filename)
    except:
        pass

    if info != None:
        if len(title) > 0 and title[0] == '+':
            if info['object name']:
                info['object name'] += title[1:]
            else:
                info['object name'] = title[1:]
        else:
            info['object name'] = title

        if len(description) > 0 and description[0] == '+':
            if info['caption/abstract']:
                info['caption/abstract'] += description[1:]
            else:
                info['caption/abstract'] = description[1:]
        else:
            info['caption/abstract'] = description

        if len(copyright) > 0 and copyright[0] == '+':
            if info['copyright notice']:
                info['copyright notice'] += copyright[1:]
            else:
                info['copyright notice'] = copyright[1:]
        else:
            info['copyright notice'] = copyright

        if len(keywords) > 0 and len(keywords[0]) > 0 and keywords[0][0] == '+':
            keywords[0] = keywords[0][1:]
            if info['keywords']:
                info['keywords'] += keywords
            else:
                info['keywords'] = keywords
        else:
            info['keywords'] = keywords

        info.save_as(filename)

        if os.path.exists(filename + '~'):
            try:
                os.remove(filename + '~')
            except:
                pass


# entry point
#if __name__ == '__main__':

    # read & display exif
    #exif = read_exif('test.jpg')
    #debug_exif_data(exif)

    # read & display IPTC
    #iptc = read_iptc('1.jpg')
    #debug_iptc_data(iptc)

    # read & display IPTC (Pillow)
    #iptc = read_iptc_pillow('1.jpg')
    #debug_iptc_data_pillow(iptc)

    # write IPTC info to file
    #write_iptc_info('test.jpg', 'title', 'description', ['key1', 'key2', 'key3'], 'copyright testing...')

    # write pillow-formatted IPTC data
    #write_iptc_info_from_pillow('test.jpg', read_iptc_pillow('1.jpg'))

    #exit(0)
