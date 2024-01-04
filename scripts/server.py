# Copyright 2021 - 2024, Bill Kennedy (https://github.com/rbbrdckybk/dream-factory)
# SPDX-License-Identifier: MIT

import os, os.path
import random
import string
import time
import scripts.utils as utils
from datetime import datetime, timedelta
import cherrypy
from cherrypy.lib import auth_basic, static
from cherrypy.process.plugins import SimplePlugin

# cherrypy already does signal handling, so if it's shutting down,
# use that as a signal to shut down main thread
class ShutdownPlugin(SimplePlugin):
    control = None
    shutdown = False
    _sleep = None

    def __init__(self, bus, control_ref, sleep = 2):
        self.control = control_ref
        SimplePlugin.__init__(self, bus)
        self._sleep = sleep

    def start(self):
        pass

    def stop(self):
        pass

    def exit(self):
        #print('ShutdownPlugin sending shutdown signal...')
        if not self.shutdown:
            self.shutdown = True
            self.control.shutdown()


def build_prompt_editor_text(prompt_file):
    buffer = ""

    f = open(prompt_file, 'r', encoding = 'utf8')
    for line in f:
        buffer += line
    f.close()

    return buffer


def build_gallery(control):
    images = []
    if control.config['gallery_current'] == 'recent':
        images = utils.get_recent_images(control.config['output_location'], control.config['gallery_max_images'])
    else:
        if control.config['gallery_current'] == 'user_gallery':
            images = utils.get_images_from_dir(control.config['gallery_user_folder'], control.config['gallery_max_images'])
        else:
            images = utils.get_images_from_dir(control.config['gallery_current'], control.config['gallery_max_images'])

    buffer = "<ul id=\"images\" class=\"image-gallery\">\n"

    for img in images:
        exif = utils.read_exif_from_image(img)
        details = ""
        upscale_info = ""
        if exif != None:
            try:
                details = exif[0x9c9c].decode('utf16')
                upscale_info = exif[0x9c9d].decode('utf16')
            except KeyError as e:
                pass

        params = utils.extract_params_from_command(details)
        param_string = ''

        neg_prompt = params['neg_prompt']
        if neg_prompt != "":
            neg_prompt = neg_prompt.replace('<', '&lt;').replace('>', '&gt;')
            neg_prompt = "negative prompt: " + neg_prompt

        short_prompt = params['prompt']
        if len(params['prompt']) > 302:
            short_prompt = params['prompt'][:300] + '...'

        prompt = ''
        if params['prompt'] != '' or params['steps'] != '':
            if params['prompt'] == '':
                prompt = '(no prompt)'
            else:
                prompt = params['prompt'].replace('<', '&lt;').replace('>', '&gt;')

            if params['width'] != '':
                if 'highres_scale_factor' in params and params['highres_scale_factor'] != '':
                    calc_width = round(float(params['highres_scale_factor']) * float(params['width']))
                    calc_height = round(float(params['highres_scale_factor']) * float(params['height']))
                    param_string += 'size: ' + str(calc_width) + 'x' + str(calc_height)
                else:
                    param_string += 'size: ' + str(params['width']) + 'x' + str(params['height'])

            if params['input_image'] != "":
                if param_string != '':
                    param_string += '  |  '
                param_string += 'init image: ' + params['input_image'] + '  |  strength: ' + str(params['strength'])

            if params['ckpt_file'] != '':
                if param_string != '':
                    param_string += '  |  '
                # remove the hash from the string
                model = str(params['ckpt_file'])
                model = model.split('[', 1)[0].strip()
                param_string += 'model: ' + model

            if params['tiling'] == 'yes':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'seamless tiling enabled'

            if params['controlnet_input_image'] != '' and (params['controlnet_model'] != '' or 'reference' in params['controlnet_pre']):
                if param_string != '':
                    param_string += '  |  '
                # remove the hash from the model string
                model = str(params['controlnet_model'])
                model = model.split('[', 1)[0].strip()
                param_string += 'ControlNet enabled: ' + params['controlnet_input_image'] + ' (' + model + ')'
                if params['controlnet_controlmode'] == 'prompt':
                    param_string += ' (favor prompt)'
                elif params['controlnet_controlmode'] == 'controlnet':
                    param_string += ' (favor ControlNet)'
                if params['controlnet_pixelperfect'] == 'yes':
                    param_string += ' (pixel perfect)'

            if params['adetailer_model'] != '':
                if param_string != '':
                    param_string += '  |  '
                # remove the hash from the model string
                model = str(params['adetailer_model'])
                model = model.split('[', 1)[0].strip()
                param_string += 'ADetailer enabled ' + ' (' + model + ')'

            if params['sampler'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'sampler: ' + str(params['sampler'])

            if params['steps'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'steps: ' + str(params['steps'])

            if params['scale'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'scale: ' + str(params['scale'])

            if params['clip_skip'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'CLIP skip: ' + str(params['clip_skip'])

            if params['vae'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'VAE: ' + str(params['vae'])

            if 'refiner_ckpt_file' in params and params['refiner_ckpt_file'] != '':
                if param_string != '':
                    param_string += '  |  '
                model = str(params['refiner_ckpt_file'])
                model = model.split('[', 1)[0].strip()
                param_string += 'refiner: ' + model
                if 'refiner_switch' in params and params['refiner_switch'] != '':
                    param_string += ' (switch at ' + str(params['refiner_switch']) + ')'

            if params['styles'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'style(s): ' + str(params['styles'].replace('Style: ', ''))

            show_denoise = False
            if 'highres_scale_factor' in params and params['highres_scale_factor'] != '' and params['width'] != '':
                show_denoise = True
                if param_string != '':
                    param_string += '  |  '
                param_string += 'highres fix applied: ' + str(params['highres_scale_factor']) + 'x scaling on ' + str(params['width']) + 'x' + str(params['height'])

            if 'highres_ckpt_file' in params and params['highres_ckpt_file'] != '':
                show_denoise = True
                if param_string != '':
                    param_string += '  |  '
                model = str(params['highres_ckpt_file'])
                model = model.split('[', 1)[0].strip()
                param_string += 'HR fix model: ' + model

            if 'highres_upscaler' in params and params['highres_upscaler'] != '':
                show_denoise = True
                if param_string != '':
                    param_string += '  |  '
                param_string += 'HR fix upscaler: ' + str(params['highres_upscaler'])

            if 'highres_sampler' in params and params['highres_sampler'] != '':
                show_denoise = True
                if param_string != '':
                    param_string += '  |  '
                param_string += 'HR fix sampler: ' + str(params['highres_sampler'])

            if 'highres_steps' in params and params['highres_steps'] != '':
                show_denoise = True
                if param_string != '':
                    param_string += '  |  '
                param_string += 'HR fix steps: ' + str(params['highres_steps'])

            if show_denoise and params['strength'] != '':
                param_string += '  |  '
                param_string += 'HR fix denoising: ' + str(params['strength'])

            if params['seed'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'seed: ' + str(params['seed'])

            ad_info = upscale_info
            if '(upscaled' in upscale_info:
                upscale_info = upscale_info.split('(upscaled', 1)[1]
                if '(ADetailer' in upscale_info:
                    upscale_info = upscale_info.split('(ADetailer', 1)[0]
                upscale_info = upscale_info.replace(')', '').strip()
                upscale_info = "upscaled " + upscale_info
                if param_string != '':
                    param_string += '  |  '
                param_string += upscale_info

            if '(ADetailer' in ad_info:
                ad_info = ad_info.split('(ADetailer', 1)[1]
                ad_info = ad_info.replace(')', '').strip()
                ad_info = "ADetailer " + ad_info
                if param_string != '':
                    param_string += '  |  '
                param_string += ad_info

        #img_identifier = utils.filename_from_abspath(img)
        img_identifier = utils.slugify(img)

        buffer += "\t<li id=\"" + img_identifier + "\" onclick=\"img_modal('i_" + img_identifier + "', 'd_" + img_identifier + "', 'p_" + img_identifier + "')\">\n"
        if control.config['gallery_current'] == 'user_gallery':
            #buffer += "\t\t<img src=\"/user_gallery/" + img_identifier + "\" id=\"i_" + img_identifier + "\"/>\n"
            buffer += "\t\t<img src=\"/user_gallery/" + utils.filename_from_abspath(img) + "\" id=\"i_" + img_identifier + "\"/>\n"
        else:
            buffer += "\t\t<img src=\"/" + img + "\" id=\"i_" + img_identifier + "\"/>\n"
        buffer += "\t\t<div class=\"overlay\"><span id=\"c_" + img_identifier + "\">" + short_prompt + "</span></div>\n"
        buffer += "\t\t<div class=\"hidden\" id=\"d_" + img_identifier + "\">" + prompt + "</div>\n"
        buffer += "\t\t<div class=\"hidden\" id=\"n_" + img_identifier + "\">" + neg_prompt + "</div>\n"
        buffer += "\t\t<div class=\"hidden\" id=\"p_" + img_identifier + "\">" + param_string + "</div>\n"
        buffer += "\t</li>\n"

    buffer += "</ul>\n"
    return buffer


def build_prompt_panel(control):
    buffer = ""
    if not control.prompt_file == "":
        file = utils.filename_from_abspath(control.prompt_file)
        path = utils.path_from_abspath(control.prompt_file)

        buffer = "<div id=\"prompt-status-header\" class=\"prompt-status-header\">\n"

        buffer += "\t<div>\n"
        buffer += "\t\t" + file.replace('.prompts', '') + "\n"
        buffer += "\t</div>\n"

        buffer += "\t<div style=\"font-size: 12px; font-weight: normal;\">\n"
        if control.get_mode() == 'random':
            if control.prompt_manager.config.get('random_input_image_dir') != '':
                buffer += "\t\tmode: random prompts, random input images\n"
            else:
                buffer += "\t\tmode: random prompts\n"
        elif control.get_mode() == 'standard':
            buffer += "\t\t" + str(control.jobs_done) + " of " + str(control.orig_work_queue_size) + " prompt combinations completed"
            if control.repeat_jobs:
                buffer += " | loops done: " + str(control.loops) + " | repeat: on\n"
            else:
                buffer += " | repeat: off\n"
        elif control.get_mode() == 'process':
            buffer += "\t\t" + str(control.jobs_done) + " of " + str(control.orig_work_queue_size) + " work items completed"
            buffer += "\t\t | mode: process\n"

        buffer += "\t</div>\n"
        buffer += "</div>\n"

        buffer += "<div id=\"prompt-status\" class=\"prompt-status\">\n"
        buffer += "\t'" + file + "' loaded from " + path + "\n"
        buffer += "</div>\n"

    else:
        buffer = "<div id=\"prompt-status\" class=\"prompt-status\" style=\"color: yellow;\">\n"
        buffer += "\tNo prompt file loaded; choose one below\n"
        buffer += "</div>\n"

    return buffer


def build_gallery_dropdown(control):
    # reset gallery view to most recent images upon page/dropdown initial load
    control.config['gallery_current'] = 'recent'

    buffer = "<label for=\"prompt-file\">View a specific location:</label>\n"
    buffer += "<select name=\"gallery-location\" id=\"gallery-location\" class=\"prompt-dropdown\" onchange=\"new_gallery_location()\">\n"
    buffer += "\t<option value=\"\">select</option>\n"
    buffer += "\t<option value=\"recent\">recent output files</option>\n"

    dirs = []
    files = os.listdir(control.config.get('output_location'))
    for f in files:
        full_path = os.path.join(control.config.get('output_location'), f)
        if os.path.isdir(full_path):
            dirs.append("\t<option value=\"" + full_path + "\">" + f + "</option>\n")

    # sort in reverse alpha order, which should be most recent first
    dirs.sort(reverse=True)
    for dir in dirs:
        buffer += dir

    # add the user-specified gallery dir as an option if it exists
    if control.config.get('gallery_user_folder') != '':
        user_dir = control.config.get('gallery_user_folder')
        if os.path.exists(user_dir):
            user_dir_alias = control.config.get('gallery_user_folder_alias')
            if user_dir_alias == '':
                user_dir_alias = user_dir
            buffer += "\t<option value=\"" + 'user_gallery' + "\">" + user_dir_alias + "</option>\n"

    buffer += "</select>\n"
    return buffer


def build_prompt_dropdown(control):
    buffer = "<div class=\"tooltip\">\n"
    buffer += "\t<div id=\"prompt-select\" class=\"prompt-status\">\n"
    buffer += "\t\t<label for=\"prompt-file\">Choose a prompt file:</label>\n"
    buffer += "\t\t<select name=\"prompt-file\" id=\"prompt-file\" class=\"prompt-dropdown\" onchange=\"new_prompt_file()\">\n"
    buffer += "\t\t\t<option value=\"\">select</option>\n"
    files = os.listdir(control.config.get('prompts_location'))
    files.sort()
    for f in files:
        if f.lower().endswith('.prompts'):
            full_path = os.path.abspath(control.config.get('prompts_location') + '/' + f)
            buffer += "\t\t\t<option value=\"" + full_path + "\">" + f.replace('.prompts', '') + "</option>\n"
    buffer += "\t\t</select>\n"

    buffer += "\t</div>\n"
    buffer += "\t<span class=\"tooltiptext\">All .prompt files in your&#xa;prompt folder appear here.</span>\n"
    buffer += "</div>\n"
    return buffer


def build_sampler_reference(control):
    buffer = ""
    if control.sdi_samplers == None:
        buffer = "Reload this page after Dream Factory has finished initializing to see a list of your available samplers here."
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These samplers may be assigned to the !SAMPLER directive. Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">Samplers:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        for s in control.sdi_samplers:
            cpy = '!SAMPLER = ' + s.replace("\\", "\\\\")
            buffer += "<li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + s + "</li>\n"
        buffer += "</ul>\n"
    return buffer


def build_model_reference(control):
    buffer = ""
    if control.sdi_models == None:
        buffer = "Reload this page after Dream Factory has finished initializing to see a list of your available models here."
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These models may be assigned to the !CKPT_FILE directive. Add additional model files to your Automatic1111 models folder and restart Dream Factory to have them appear here.</p>\n"
        if control.model_trigger_words != None and len(control.model_trigger_words) > 0:
            if control.config.get('auto_insert_model_trigger') != 'off':
                buffer += "<p>Trigger words (right column beside each model name) will be automatically added "
                if control.config.get('auto_insert_model_trigger') == 'first_comma':
                    buffer += "after the first comma in the prompt (or at the end, if there are no commas) when using the associated model."
                else:
                    buffer += "at the " + control.config.get('auto_insert_model_trigger') + " of the prompt when using the associated model."
            else:
                buffer += "<p>Trigger words (right column beside each model name) will be automatically added to prompts when the associated model is in use."
            buffer += " You may override the automatic placement of trigger words with the !AUTO_INSERT_MODEL_TRIGGER directive (off, start, end, first_comma).</p>"
        else:
            buffer += "<p>Note that you may add model trigger words to the 'model-triggers.txt' file in your Dream Factory directory to have them automatically added to your prompts.</p>"
        buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">Models:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"

        # organize into subdirs
        subdirs = []
        for m in control.sdi_models:
            path = os.path.dirname(m['name'])
            if path not in subdirs:
                subdirs.append(path)
        subdirs.sort()
        if '' in subdirs:
            # move base dir to end
            subdirs.remove('')
            subdirs.append('')

        for subdir in subdirs:
            subdir_display = subdir
            if subdir_display == '':
                subdir_display = '(root)'
            buffer += "<details open>"
            buffer += "<summary><li class=\"no-bullets-head\"\">" + subdir_display + "</li></summary>\n"
            for m in control.sdi_models:
                path = os.path.dirname(m['name'])
                if path == subdir:
                    trigger = None
                    if control.model_trigger_words != None:
                        trigger = control.model_trigger_words.get(m['name'])
                    m_name = m['name'].split('[', 1)[0].strip()
                    cpy = '!CKPT_FILE = ' + m_name.replace("\\", "\\\\")
                    filename = os.path.basename(m_name)
                    filename_display = filename

                    # civitai integration stuff
                    civitai_link = '&nbsp;<img src=\"img/spacer.png\" height=\"20\" />'
                    civitai_id = ''
                    civitai_title = ''
                    civitai_base_model = '&nbsp;'
                    civitai_nsfw = '&nbsp;'
                    civitai_triggers = ''
                    if control.config['civitai_use']:
                        if 'civitai_id' in m:
                            civitai_id = m['civitai_id']
                            c_path = 'https://civitai.com/models/' + str(civitai_id)
                            civitai_link = '&nbsp;&nbsp;<a target=\"_blank\" href=\"' + c_path + '\"><img src=\"img/civitai_logo.png\" alt=\"view on civitai.com\"/></a>'
                            civitai_title =  m['civitai_title']
                            if civitai_title != '':
                                filename_display = civitai_title
                            if m['civitai_base_model'] != '':
                                civitai_base_model = m['civitai_base_model']
                            if 'sd' not in civitai_base_model.lower():
                                civitai_base_model = '&nbsp;'
                            if m['civitai_nsfw']:
                                civitai_nsfw = 'nsfw'
                            count = 0
                            for t in m['civitai_triggers']:
                                if count > 0:
                                    civitai_triggers += ', '
                                civitai_triggers += t
                                count += 1

                    # model-triggers.txt trigger overrides civitai.com
                    if trigger != None:
                        civitai_triggers = trigger

                    civitai_triggers_display = civitai_triggers
                    if len(civitai_triggers_display) > 83:
                        civitai_triggers_display = civitai_triggers_display[0:83] + '..'

                    if len(filename_display) > 83:
                        filename_display = filename_display[0:83] + '..'

                    buffer += '<div class=\"pose-row\">'
                    buffer += '<div class=\"pose-column-short\">' + civitai_link + '</div>'
                    buffer += "<div class=\"pose-column-very-long\"><li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + filename_display + "</li></div>"
                    buffer += '<div class=\"pose-column-med\">' + civitai_base_model + '</div>'
                    #buffer += '<div class=\"pose-column-short\">' + civitai_nsfw + '</div>'
                    buffer += "<div class=\"pose-column-med-long\"><li class=\"no-bullets\" onclick=\"copyText('" + civitai_triggers + "')\">" + civitai_triggers_display + "</li></div>"
                    buffer += '</div>'

            buffer += "</details>"
        buffer += "</ul>\n"
    return buffer


def build_hypernetwork_reference(control):
    buffer = ""
    if control.sdi_hypernetworks == None:
        buffer = "Reload this page after Dream Factory has finished initializing to see a list of your available hypernetworks here."
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These hypernetworks may be included in your prompts (use &lt;hypernet:[hypernetwork name]:[weighting]&gt; or simply click an item to copy it to the clipboard in the proper format). Add additional files to your Automatic1111 \'\\models\\hypernetworks\' folder and restart Dream Factory to have them appear here.</p>\n"
        if not control.config['civitai_use']:
            buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        else:
            buffer += "<p>Click on an item to copy it to the clipboard and close this reference. If hypernet trigger(s) are available from civitai.com, click them to copy both the hypernetwork reference and trigger word(s) to the clipboard.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">Hypernetworks:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        if len(control.sdi_hypernetworks) == 0:
            #buffer += "none"
            buffer = "none"
        else:
            # organize into subdirs
            subdirs = []
            for m in control.sdi_hypernetworks:
                path = os.path.dirname(control.model_subdir(m['path']))
                if path not in subdirs:
                    subdirs.append(path)
            subdirs.sort()
            if '' in subdirs:
                # move base dir to end
                subdirs.remove('')
                subdirs.append('')

            for subdir in subdirs:
                subdir_display = subdir
                if subdir_display == '':
                    subdir_display = '(root)'
                buffer += "<details open>"
                buffer += "<summary><li class=\"no-bullets-head\"\">" + subdir_display + "</li></summary>\n"
                for m in control.sdi_hypernetworks:
                    path = os.path.dirname(control.model_subdir(m['path']))
                    if path == subdir:
                        filename = os.path.basename(m['name'])
                        filename_display = filename
                        cpy = '<hypernet:' + filename + ':1.0>'

                        # civitai integration stuff
                        civitai_link = '&nbsp;<img src=\"img/spacer.png\" height=\"20\" />'
                        civitai_id = ''
                        civitai_title = ''
                        civitai_base_model = '&nbsp;'
                        civitai_nsfw = '&nbsp;'
                        civitai_triggers = ''
                        if control.config['civitai_use']:
                            if 'civitai_id' in m:
                                civitai_id = m['civitai_id']
                                c_path = 'https://civitai.com/models/' + str(civitai_id)
                                civitai_link = '&nbsp;&nbsp;<a target=\"_blank\" href=\"' + c_path + '\"><img src=\"img/civitai_logo.png\" alt=\"view on civitai.com\"/></a>'
                                civitai_title =  m['civitai_title']
                                if civitai_title != '':
                                    filename_display = civitai_title
                                if m['civitai_base_model'] != '':
                                    civitai_base_model = m['civitai_base_model']
                                if 'sd' not in civitai_base_model.lower():
                                    civitai_base_model = '&nbsp;'
                                if m['civitai_nsfw']:
                                    civitai_nsfw = 'nsfw'
                                count = 0
                                for t in m['civitai_triggers']:
                                    if count > 0:
                                        civitai_triggers += ', '
                                    civitai_triggers += t
                                    count += 1

                                if 'civitai_weight' in m:
                                    if m['civitai_weight'] != '':
                                        cpy = '<hypernet:' + filename + ':' + str(m['civitai_weight']) + '>'

                        civitai_triggers_display = civitai_triggers
                        if len(civitai_triggers_display) > 83:
                            civitai_triggers_display = civitai_triggers_display[0:83] + '..'

                        if len(filename_display) > 83:
                            filename_display = filename_display[0:83] + '..'

                        buffer += '<div class=\"pose-row\">'
                        buffer += '<div class=\"pose-column-short\">' + civitai_link + '</div>'
                        buffer += "<div class=\"pose-column-very-long\"><li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + filename_display + "</li></div>"
                        buffer += '<div class=\"pose-column-med\">' + civitai_base_model + '</div>'
                        #buffer += '<div class=\"pose-column-short\">' + civitai_nsfw + '</div>'
                        buffer += "<div class=\"pose-column-med-long\"><li class=\"no-bullets\" onclick=\"copyText('" + civitai_triggers + ' ' + cpy + "')\">" + civitai_triggers_display + "</li></div>"
                        buffer += '</div>'

                buffer += "</details>"
            buffer += "</ul>\n"
    return buffer


def build_wildcard_reference(control):
    buffer = ""
    if control.wildcards == None:
        buffer = "Reload this page after Dream Factory has finished initializing to see a list of your available wildcards here."
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These wildcards may be included in your prompts. Add additional wildcard files to '" + control.config.get('wildcard_location') + "' and restart Dream Factory to have them appear here.</p>\n"
        buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">Wildcards:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        keys = []
        for k, v in control.wildcards.items():
            keys.append(k)
        keys.sort()
        for key in keys:
            cpy = '__' + key + '__'
            buffer += "<li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + key + "</li>\n"
        buffer += "</ul>\n"
    return buffer


def build_embedding_reference(control):
    buffer = ""
    if len(control.embeddings) == 0:
        buffer = "none"
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These embeddings may be included in your prompts (simply use the embedding name in the prompt to activate it). Add additional files to your Automatic1111 embeddings folder and restart Dream Factory to have them appear here.</p>\n"
        buffer += "<p>Warning: attempting to use an embedding with an inappropriate model will cause errors (e.g. trying to use a SD v2.x embedding on a SD v1.x model, etc)!</p>\n"
        buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">Embeddings:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        keys = []

        # organize into subdirs
        subdirs = []
        for m in control.embeddings:
            path = os.path.dirname(control.model_subdir(m['path']))
            if path not in subdirs:
                subdirs.append(path)
        subdirs.sort()
        if '' in subdirs:
            # move base dir to end
            subdirs.remove('')
            subdirs.append('')

        for subdir in subdirs:
            subdir_display = subdir
            if subdir_display == '':
                subdir_display = '(root)'
            buffer += "<details open>"
            buffer += "<summary><li class=\"no-bullets-head\"\">" + subdir_display + "</li></summary>\n"

            for m in control.embeddings:
                path = os.path.dirname(control.model_subdir(m['path']))
                if path == subdir:
                    filename = os.path.basename(m['name'])
                    filename_display = filename
                    cpy = filename

                    # civitai integration stuff
                    civitai_link = '&nbsp;<img src=\"img/spacer.png\" height=\"20\" />'
                    civitai_id = ''
                    civitai_title = ''
                    civitai_base_model = '&nbsp;'
                    civitai_nsfw = '&nbsp;'
                    civitai_triggers = ''
                    if control.config['civitai_use']:
                        if 'civitai_id' in m:
                            civitai_id = m['civitai_id']
                            c_path = 'https://civitai.com/models/' + str(civitai_id)
                            civitai_link = '&nbsp;&nbsp;<a target=\"_blank\" href=\"' + c_path + '\"><img src=\"img/civitai_logo.png\" alt=\"view on civitai.com\"/></a>'
                            civitai_title =  m['civitai_title']
                            if civitai_title != '':
                                filename_display = civitai_title
                            if m['civitai_base_model'] != '':
                                civitai_base_model = m['civitai_base_model']
                            if 'sd' not in civitai_base_model.lower():
                                civitai_base_model = '&nbsp;'
                            if m['civitai_nsfw']:
                                civitai_nsfw = 'nsfw'
                            count = 0
                            for t in m['civitai_triggers']:
                                if count > 0:
                                    civitai_triggers += ', '
                                if t.lower() != cpy.lower():
                                    civitai_triggers += t
                                    count += 1

                    civitai_triggers_display = civitai_triggers
                    if len(civitai_triggers_display) > 83:
                        civitai_triggers_display = civitai_triggers_display[0:83] + '..'

                    if len(filename_display) > 83:
                        filename_display = filename_display[0:83] + '..'

                    buffer += '<div class=\"pose-row\">'
                    buffer += '<div class=\"pose-column-short\">' + civitai_link + '</div>'
                    buffer += "<div class=\"pose-column-very-long\"><li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + filename_display + "</li></div>"
                    buffer += '<div class=\"pose-column-med\">' + civitai_base_model + '</div>'
                    #buffer += '<div class=\"pose-column-short\">' + civitai_nsfw + '</div>'
                    buffer += "<div class=\"pose-column-med-long\"><li class=\"no-bullets\" onclick=\"copyText('" + civitai_triggers + ' ' + cpy + "')\">" + civitai_triggers_display + "</li></div>"
                    buffer += '</div>'

            buffer += "</details>"
        buffer += "</ul>\n"
    return buffer


def build_lora_reference(control):
    buffer = ""
    if control.sdi_loras == None:
        buffer = "Reload this page after Dream Factory has finished initializing to see a list of your available LoRAs here."
    else:
        buffer = ""
        buffer += "<div class=\"modal-help-header-pre\"><p>These LoRA files may be included in your prompts (use &lt;lora:[LoRA name]:[weighting]&gt; or simply click an item to copy it to the clipboard in the proper format). Add additional files to your Automatic1111 \'\\models\\Lora\' folder and restart Dream Factory to have them appear here.</p>\n"
        if not control.config['civitai_use']:
            buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        else:
            buffer += "<p>Click on an item to copy it to the clipboard and close this reference. If LoRA trigger(s) are available from civitai.com, click them to copy both the LoRA reference and trigger word(s) to the clipboard.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">LoRA files:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        if len(control.sdi_loras) == 0:
            #buffer += "none"
            buffer = "none"
        else:
            # organize into subdirs
            subdirs = []
            for m in control.sdi_loras:
                path = os.path.dirname(control.model_subdir(m['path']))
                if path not in subdirs:
                    subdirs.append(path)
            subdirs.sort()
            if '' in subdirs:
                # move base dir to end
                subdirs.remove('')
                subdirs.append('')

            for subdir in subdirs:
                subdir_display = subdir
                if subdir_display == '':
                    subdir_display = '(root)'
                buffer += "<details open>"
                buffer += "<summary><li class=\"no-bullets-head\"\">" + subdir_display + "</li></summary>\n"
                for m in control.sdi_loras:
                    path = os.path.dirname(control.model_subdir(m['path']))
                    if path == subdir:
                        filename = os.path.basename(m['name'])
                        filename_display = filename
                        cpy = '<lora:' + filename + ':1.0>'

                        # civitai integration stuff
                        civitai_link = '&nbsp;<img src=\"img/spacer.png\" height=\"20\" />'
                        civitai_id = ''
                        civitai_title = ''
                        civitai_base_model = '&nbsp;'
                        civitai_nsfw = '&nbsp;'
                        civitai_triggers = ''
                        if control.config['civitai_use']:
                            if 'civitai_id' in m:
                                civitai_id = m['civitai_id']
                                c_path = 'https://civitai.com/models/' + str(civitai_id)
                                civitai_link = '&nbsp;&nbsp;<a target=\"_blank\" href=\"' + c_path + '\"><img src=\"img/civitai_logo.png\" alt=\"view on civitai.com\"/></a>'
                                civitai_title =  m['civitai_title']
                                if civitai_title != '':
                                    filename_display = civitai_title
                                if m['civitai_base_model'] != '':
                                    civitai_base_model = m['civitai_base_model']
                                if 'sd' not in civitai_base_model.lower():
                                    civitai_base_model = '&nbsp;'
                                if m['civitai_nsfw']:
                                    civitai_nsfw = 'nsfw'
                                count = 0
                                for t in m['civitai_triggers']:
                                    if count > 0:
                                        civitai_triggers += ', '
                                    civitai_triggers += t
                                    count += 1

                                if 'civitai_weight' in m:
                                    if m['civitai_weight'] != '':
                                        cpy = '<lora:' + filename + ':' + str(m['civitai_weight']) + '>'

                        civitai_triggers_display = civitai_triggers
                        if len(civitai_triggers_display) > 83:
                            civitai_triggers_display = civitai_triggers_display[0:83] + '..'

                        if len(filename_display) > 83:
                            filename_display = filename_display[0:83] + '..'

                        buffer += '<div class=\"pose-row\">'
                        buffer += '<div class=\"pose-column-short\">' + civitai_link + '</div>'
                        buffer += "<div class=\"pose-column-very-long\"><li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + filename_display + "</li></div>"
                        buffer += '<div class=\"pose-column-med\">' + civitai_base_model + '</div>'
                        #buffer += '<div class=\"pose-column-short\">' + civitai_nsfw + '</div>'
                        buffer += "<div class=\"pose-column-med-long\"><li class=\"no-bullets\" onclick=\"copyText('" + civitai_triggers + ' ' + cpy + "')\">" + civitai_triggers_display + "</li></div>"
                        buffer += '</div>'

                buffer += "</details>"
            buffer += "</ul>\n"
    return buffer


def build_controlnet_model_reference(control):
    buffer = ""
    if control.sdi_controlnet_models == None:
        buffer = "none"
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These ControlNet models may be included in your prompts (use !CONTROLNET_MODEL = [model name] or simply click an item to copy it to the clipboard in the proper format). Note that you must also set an appropriate ControlNet input image with !CONTROLNET_INPUT_IMAGE to enable ControlNet.</p>\n"
        buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">ControlNet Models:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        if len(control.sdi_controlnet_models) == 0:
            buffer = "none"
        else:
            for m in control.sdi_controlnet_models:
                m = m.split('[', 1)[0].strip()
                cpy = '!CONTROLNET_MODEL = ' + m
                buffer += "<li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + m + "</li>\n"
            buffer += "</ul>\n"
    return buffer


def build_controlnet_pre_reference(control):
    buffer = ""
    if control.sdi_controlnet_preprocessors == None:
        buffer = "none"
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These ControlNet pre-processors may be included in your prompts (use !CONTROLNET_PRE = [preprocessor name] or simply click an item to copy it to the clipboard in the proper format). Note that you must also set an appropriate ControlNet input image with !CONTROLNET_INPUT_IMAGE, and set a ControlNet model with !CONTROLNET_MODEL to enable ControlNet.</p>\n"
        buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">ControlNet Pre-processors:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"
        if len(control.sdi_controlnet_preprocessors) == 0:
            buffer = "none"
        else:
            for p in control.sdi_controlnet_preprocessors:
                cpy = '!CONTROLNET_PRE = ' + p
                buffer += "<li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + p + "</li>\n"
            buffer += "</ul>\n"
    return buffer


def build_controlnet_poses_reference(control):
    buffer = ""
    if len(control.poses) == 0:
        buffer = "none"
    else:
        buffer += "<div class=\"modal-help-header-pre\"><p>These ControlNet poses may be included in your prompts (use !CONTROLNET_INPUT_IMAGE = [full path to image] or simply click an filename to copy it to the clipboard in the proper format). Note that you must also set a ControlNet model with !CONTROLNET_MODEL to enable ControlNet.</p>\n"
        buffer += "<p>Click on an item to copy it to the clipboard and close this reference.</p></div>\n"
        buffer += "<div class=\"modal-help-header\">ControlNet Poses:</div>\n"
        buffer += "<ul class=\"no-bullets\">\n"

        for p in control.poses:
            subdir = p[0]
            buffer += "<details open>"
            buffer += "<summary><li class=\"no-bullets-head\"\">" + subdir + "</li></summary>\n"
            for f in p[1]:
                file = f[0]
                dimensions = f[1]
                preview = f[2]
                fullpath = os.path.join(subdir, file)
                cpy = '!CONTROLNET_INPUT_IMAGE = ' + fullpath.replace("\\", "\\\\")
                preview_img = '<a class=\"thumbnail\" href=\"#thumb\"><img src=\"img/pre01.png\" /><span>'
                #preview_img += '<img src=\"/' + fullpath + '\" /><br />Pose (' + file + ')</span></a>'
                preview_img += '<img src=\"/' + fullpath + '\" /></span></a>'

                preview_alt = ''
                if preview != '':
                    fullpath_preview = os.path.join(subdir, 'previews')
                    fullpath_preview = os.path.join(fullpath_preview, file)
                    fullpath_preview = fullpath_preview[:-3] + preview
                    preview_alt = '<a class=\"thumbnail\" href=\"#thumb\"><img src=\"img/pre02.png\" /><span>'
                    #preview_alt += '<img src=\"/' + fullpath_preview + '\" /><br />Preview (' + file + ')</span></a>'
                    preview_alt += '<img src=\"/' + fullpath_preview + '\" /></span></a>'

                #buffer += '<li class=\"no-bullets\">'
                buffer += '<div class=\"pose-row\">'
                buffer += '<div class=\"pose-column-short\">&nbsp;&nbsp;&nbsp;&nbsp;</div>'
                #buffer += "<div class=\"pose-column-long\" onclick=\"copyText('" + cpy + "')\">" + file + '</div>'
                buffer += "<div class=\"pose-column-long\"><li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + file + "</li></div>"
                buffer += '<div class=\"pose-column\">' + dimensions + '</div>'
                buffer += '<div class=\"pose-column-short\">' + preview_img + '</div>'
                buffer += '<div class=\"pose-column-short\">' + preview_alt + '</div>'
                buffer += '</div>'
                #buffer += '</li>\n'

                #buffer += "<li class=\"no-bullets\" onclick=\"copyText('" + cpy + "')\">" + file + "</li>\n"
            buffer += "</details>"
        buffer += "</ul>\n"
    return buffer


def build_worker_panel(workers):
    buffer = ""
    count = 0
    for worker in workers:
        if count > 0:
            buffer += '\n'

        working_text = "dreaming"
        clock_text = "0:00"
        prompt_text = ""
        prompt_options_text = ""

        if worker["idle"]:
            working_text = "idle"
            clock_text = ""
            prompt_text = ""
            prompt_options_text = ""
            if not worker['sdi_instance'].init:
                prompt_text = "<div style=\"color: yellow; padding-top: 6px;\">" + "waiting to be initialized...</div>"
            if worker['sdi_instance'].init and not worker['sdi_instance'].ready:
                prompt_text = "<div style=\"padding-top: 6px;\">" + "currently being initialized on port " + str(worker['sdi_instance'].sd_port) + "...</div>"
            if worker['sdi_instance'].ready and worker['sdi_instance'].busy:
                # this should only happen in this case
                prompt_text = "<div style=\"padding-top: 6px;\">" + "performing initial data exchange queries with SD instance...</div>"

        else:
            prompt_text = ''
            prompt_options_text = ''

            if worker["work_state"] != "":
                working_text = worker["work_state"]

            if worker["job_prompt_info"] != None and worker["job_prompt_info"] != '':
                if worker["job_prompt_info"].get('mode') == 'process':
                    prompt_text = 'batch processing...<br>'
                    if worker["work_state"] == 'upscaling':
                        prompt_text += ' -> currently upscaling: \'' + utils.filename_from_abspath(worker["job_prompt_info"].get('input_image')) + '\' ...'

                        if worker["job_prompt_info"].get('upscale_model') != 'sd':
                            prompt_options_text = 'upscaler: ' + worker["job_prompt_info"].get('upscale_model')
                            prompt_options_text += ' | factor: ' + str(worker["job_prompt_info"].get('upscale_amount')) + 'x'
                        else:
                            prompt_options_text = 'upscaler: SD'
                            prompt_options_text += ' | factor: auto'
                        if float(worker["job_prompt_info"].get('upscale_gfpgan_amount')) > 0:
                            prompt_options_text += ' | GFPGAN amount: ' + str(worker["job_prompt_info"].get('upscale_gfpgan_amount'))
                        else:
                            prompt_options_text += ' | GFPGAN disabled'
                        if float(worker["job_prompt_info"].get('upscale_codeformer_amount')) > 0:
                            prompt_options_text += ' | CodeFormer amount: ' + str(worker["job_prompt_info"].get('upscale_codeformer_amount'))
                        else:
                            prompt_options_text += ' | CodeFormer disabled'

                    elif worker["work_state"] == 'adetailer':
                        prompt_text += ' -> ADetailer: \'' + utils.filename_from_abspath(worker["job_prompt_info"].get('input_image')) + '\' ...'
                        prompt_options_text = 'model: ' + worker["job_prompt_info"].get('adetailer_model')
                        if str(worker["job_prompt_info"].get('adetailer_strength')) != '':
                            prompt_options_text += ' | strength: ' + str(worker["job_prompt_info"].get('adetailer_strength'))

                    elif worker["work_state"] == 'processing':
                        prompt_text += ' -> working on: \'' + utils.filename_from_abspath(worker["job_prompt_info"].get('input_image')) + '\' ...'

                else:
                    prompt_text = worker["job_prompt_info"].get('prompt').replace('<', '&lt').replace('>', '&gt')

                    if worker["job_prompt_info"].get('input_image') != "":
                        prompt_options_text = "init image: " + utils.filename_from_abspath(worker["job_prompt_info"].get('input_image'))
                    else:
                        prompt_options_text = 'size: ' + str(worker["job_prompt_info"].get('width')) + 'x' + str(worker["job_prompt_info"].get('height'))

                    prompt_options_text += ' | steps: ' + str(worker["job_prompt_info"].get('steps')) \
                        + ' | scale: ' + str(worker["job_prompt_info"].get('scale')) \
                        + ' | samples: ' + str(worker["job_prompt_info"].get('samples'))

                exec_time = time.time() - worker["job_start_time"]
                clock_text = time.strftime("%M:%S", time.gmtime(exec_time))
            else:
                # this should only happen during options change/model load
                if worker['sdi_instance'].model_loading_now != '':
                    prompt_text = "<div style=\"padding-top: 6px;\">" + 'loading new model: ' + worker['sdi_instance'].model_loading_now + '...</div>'
                    clock_text = '-:-'
                    working_text = "model load"

        buffer += "<div id=\"worker-" + str(worker["id"]) + "\" class=\"worker-info\">\n"
        buffer += "\t<div class=\"worker-info-header\">\n"
        buffer += "\t\t<div>" + str(worker["name"]) + " (" + str(worker["id"]) + ")</div>\n"
        buffer += "\t\t<div class=\"small\">" + str(worker["jobs_done"]) + " jobs completed</div>\n"
        buffer += "\t</div>\n"

        buffer += "\t<div class=\"worker-info-prompt\">\n"
        buffer += "\t\t<div class=\"left\">\n"
        if worker["idle"]:
            buffer += "\t\t\t<div style=\"color: yellow;\">[" + working_text + "]</div>\n"
        else:
            buffer += "\t\t\t<div>[" + working_text + "]</div>\n"
        buffer += "\t\t\t<div class=\"clock\">" + clock_text + "</div>\n"
        buffer += "\t\t</div>\n"
        buffer += "\t\t<div class=\"right\">\n"
        buffer += "\t\t\t<div class=\"right-top\">" + prompt_text + "</div>\n"
        buffer += "\t\t\t<div class=\"right-bottom\">" + prompt_options_text + "</div>\n"
        buffer += "\t\t</div>\n"
        buffer += "\t</div>\n"
        buffer += "</div>\n"

        count += 1
    return buffer


class ArtGenerator(object):
    def __init__(self, control_ref):
        self.control = control_ref

    @cherrypy.expose
    def index(self):
        return open('./server/index.html')

    @cherrypy.expose
    def getzip(self):
        dir = self.control.config['gallery_current']
        if dir == 'user_gallery':
            dir = self.control.config['gallery_user_folder']

        zip_path = utils.create_zip(dir)
        return static.serve_download(os.path.abspath(zip_path))

    @cherrypy.expose
    def getimg(self, img):
        actual_path = ""
        if ('user_gallery/') in img:
            actual_path = img.split('user_gallery/', 1)[1]
            actual_path = os.path.join(self.control.config['gallery_user_folder'], actual_path)
        else:
            actual_path = img.split('output/', 1)[1]
            actual_path = os.path.join(self.control.config['output_location'], actual_path)

        return static.serve_download(os.path.abspath(actual_path))

@cherrypy.expose
class ArtGeneratorWebService(object):
    def __init__(self, control_ref):
        self.control = control_ref


    @cherrypy.tools.accept(media='text/plain')
    def GET(self):
        pass

    def POST(self, type, arg):
        if type.lower().strip() == 'gallery_delete':
            response = self.control.delete_gallery_img(arg)
            return response

        if type.lower().strip() == 'gallery_upscale':
            response = self.control.upscale_gallery_img(arg)
            return response

        if type.lower().strip() == 'prompt_file':
            self.control.new_prompt_file(arg)

        if type.lower().strip() == 'prompt_editor':
            self.control.new_prompt_editor_file(arg)
            buffer_text = build_prompt_editor_text(arg)
            return buffer_text

        if type.lower().strip() == 'prompt_editor_create':
            buffer_text = self.control.create_prompt_editor_file(arg)
            return buffer_text

        if type.lower().strip() == 'prompt_editor_save':
            result = self.control.save_prompt_editor_file(arg)
            if result:
                return ""
            else:
                # error saving
                return "-1"

        if type.lower().strip() == 'prompt_editor_rename':
            result = self.control.rename_prompt_editor_file(arg)
            if result:
                return ""
            else:
                # error renaming
                return "-1"

        if type.lower().strip() == 'gallery_location':
            self.control.config['gallery_current'] = arg

    def WORKER_REFRESH(self):
        buffer_text = build_worker_panel(self.control.workers)
        return buffer_text

    def PROMPT_REFRESH(self):
        buffer_text = build_prompt_panel(self.control)
        return buffer_text

    def PROMPT_DROPDOWN_LOAD(self):
        buffer_text = build_prompt_dropdown(self.control)
        return buffer_text

    def SAMPLER_REFERENCE_LOAD(self):
        buffer_text = build_sampler_reference(self.control)
        return buffer_text

    def MODEL_REFERENCE_LOAD(self):
        buffer_text = build_model_reference(self.control)
        return buffer_text

    def HYPERNETWORK_REFERENCE_LOAD(self):
        buffer_text = build_hypernetwork_reference(self.control)
        return buffer_text

    def LORA_REFERENCE_LOAD(self):
        buffer_text = build_lora_reference(self.control)
        return buffer_text

    def WILDCARD_REFERENCE_LOAD(self):
        buffer_text = build_wildcard_reference(self.control)
        return buffer_text

    def EMBEDDING_REFERENCE_LOAD(self):
        buffer_text = build_embedding_reference(self.control)
        return buffer_text

    def CONTROLNET_MODEL_REFERENCE_LOAD(self):
        buffer_text = build_controlnet_model_reference(self.control)
        return buffer_text

    def CONTROLNET_PRE_REFERENCE_LOAD(self):
        buffer_text = build_controlnet_pre_reference(self.control)
        return buffer_text

    def CONTROLNET_POSES_REFERENCE_LOAD(self):
        buffer_text = build_controlnet_poses_reference(self.control)
        return buffer_text

    def PROMPT_FILE_DELETE(self):
        result = self.control.delete_prompt_file()
        if result:
            return ""
        else:
            # error deleting
            return "-1"
        return buffer_text

    def GALLERY_DROPDOWN_LOAD(self):
        buffer_text = build_gallery_dropdown(self.control)
        return buffer_text

    def BUFFER_REFRESH(self):
        buffer_text = ""
        for i in self.control.output_buffer:
            buffer_text += i
        return buffer_text

    def GALLERY_REFRESH(self):
        buffer_text = build_gallery(self.control)
        return buffer_text

    def GALLERY_REFRESH_RATE(self):
        return str(self.control.config['gallery_refresh'])

    def EDITOR_MAX_CHARS(self):
        return str(self.control.config['editor_max_styling_chars'])

    def STATUS_REFRESH(self):
        jobs_done = "{:,}".format(self.control.total_jobs_done)
        # we'll pass back whether or not the server is paused as the first char
        buffer_text = "n<div>Server is running</div>"
        if self.control.is_paused:
            if self.control.num_workers_working() > 0:
                buffer_text = "y<div style=\"color: yellow;\">Pause requested; waiting for " + str(self.control.num_workers_working()) + " worker(s) to finish...</div>"
            else:
                buffer_text = "y<div style=\"color: yellow;\">Server is paused</div>"
        buffer_text += "<div>Server uptime: "
        diff = time.time() - self.control.server_startup_time
        buffer_text += "{}".format(str(timedelta(seconds = round(diff, 0))))
        buffer_text += "</div><div>Total jobs done: " + jobs_done + "</div>"
        if self.control.config['debug_test_mode']:
            buffer_text += "<div style=\"color: yellow;\">*** TEST/DEBUG MODE ENABLED - NO ACTUAL IMAGES ARE BEING CREATED! ***</div>"
        return buffer_text

    def BUFFER_LENGTH(self, new_length):
        if new_length.isdigit():
            self.control.resize_buffer(int(new_length))

    def BUFFER_CLEAR(self):
        self.control.output_buffer.clear()

    def SERVER_PAUSE(self):
        self.control.pause()

    def SERVER_UNPAUSE(self):
        self.control.unpause()

    def SERVER_SHUTDOWN(self):
        self.control.shutdown()


class ArtServer:
    def __init__(self):
        self.control_ref = None
        self.config = {}

    def start(self, control_ref):
        self.control_ref = control_ref

        self.config = {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd())
            }
        }

        if self.control_ref.config['webserver_use_authentication']:
            control_ref.print("webserver authentication enabled...")
            self.config = {
                '/': {
                    'tools.auth_basic.on': True,
                    'tools.auth_basic.realm': 'localhost',
                    'tools.auth_basic.checkpassword': self.validate_password,
                    'tools.auth_basic.accept_charset': 'UTF-8',
                    'tools.sessions.on': True,
                    'tools.staticdir.root': os.path.abspath(os.getcwd())
                }
            }

        # common config items
        favicon_path = os.path.join('server', 'img')
        favicon_path = os.path.join(favicon_path, 'favicon.ico')
        self.config.update({
            '/generator': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'text/plain')],
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './server'
            },
            '/output': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': os.path.abspath(self.control_ref.config['output_location'])
            },
        	'/favicon.ico': {
        		'tools.staticfile.on': True,
                'tools.staticfile.filename': os.path.abspath(favicon_path)
        	}
        })

        # if we're not in debug mode and not logging web requests, enable production mode
        if not self.control_ref.config['debug_test_mode'] and not self.control_ref.config.get('webserver_console_log'):
            self.config.update({
                'global': {
                    'environment' : 'production'
                }
            })

        # set up reference to user-specified gallery folder if necessary
        if self.control_ref.config['gallery_user_folder'] != '':
            user_dir = self.control_ref.config.get('gallery_user_folder')
            if os.path.exists(user_dir):
                self.config.update({
                    '/user_gallery': {
                        'tools.staticdir.on': True,
                        'tools.staticdir.dir': os.path.abspath(self.control_ref.config.get('gallery_user_folder'))
                    }
                })

        # set up reference to ControlNet poses folder
        if os.path.exists('poses'):
            self.config.update({
                '/poses': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.dir': os.path.abspath('poses')
                }
            })


        if self.control_ref.config['webserver_network_accessible']:
            control_ref.print("webserver listening for external requests...")
            cherrypy.config.update({'server.socket_host': '0.0.0.0'})

        cherrypy.config.update({'server.socket_port': self.control_ref.config['webserver_port']})
        webapp = ArtGenerator(self.control_ref)
        webapp.generator = ArtGeneratorWebService(self.control_ref)

        if not self.control_ref.config.get('webserver_console_log'):
            # disable console logging
            cherrypy.log.screen = False

        ShutdownPlugin(cherrypy.engine, self.control_ref).subscribe()

        cherrypy.quickstart(webapp, '/', self.config)

    def stop(self):
        cherrypy.engine.exit()

    def validate_password(self, realm, username, password):
        if username == self.control_ref.config['webserver_auth_username'] \
            and password == self.control_ref.config['webserver_auth_password']:
           return True
        return False


if __name__ == '__main__':
    server = ArtServer()
    server.start()
