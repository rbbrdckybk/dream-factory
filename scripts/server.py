# Copyright 2021 - 2022, Bill Kennedy (https://github.com/rbbrdckybk/ai-art-generator)
# SPDX-License-Identifier: MIT

import os, os.path
import random
import string
import time
import scripts.utils as utils
from datetime import datetime, timedelta
import cherrypy
from cherrypy.lib import auth_basic, static



def build_prompt_editor_text(prompt_file):
    buffer = ""

    f = open(prompt_file,'r')
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

        short_prompt = params['prompt']
        if len(params['prompt']) > 302:
            short_prompt = params['prompt'][:300] + '...'

        if params['prompt'] != '':
            if params['width'] != '':
                param_string += 'size: ' + str(params['width']) + 'x' + str(params['height'])
            elif params['input_image'] != "":
                param_string += 'init image: ' + params['input_image'] + '  |  strength: ' + str(params['strength'])

            if params['steps'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'steps: ' + str(params['steps'])

            if params['scale'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'scale: ' + str(params['scale'])

            if params['seed'] != '':
                if param_string != '':
                    param_string += '  |  '
                param_string += 'seed: ' + str(params['seed'])

            if '(upscaled' in upscale_info:
                upscale_info = upscale_info.split('(upscaled', 1)[1]
                upscale_info = upscale_info.replace(')', '').strip()
                upscale_info = "upscaled " + upscale_info
                if param_string != '':
                    param_string += '  |  '
                param_string += upscale_info

        buffer += "\t<li id=\"" + utils.filename_from_abspath(img) + "\" onclick=\"img_modal('i_" + utils.filename_from_abspath(img) + "', 'd_" + utils.filename_from_abspath(img) + "', 'p_" + utils.filename_from_abspath(img) + "')\">\n"
        if control.config['gallery_current'] == 'user_gallery':
            buffer += "\t\t<img src=\"/user_gallery/" + utils.filename_from_abspath(img) + "\" id=\"i_" + utils.filename_from_abspath(img) + "\"/>\n"
        else:
            buffer += "\t\t<img src=\"/" + img + "\" id=\"i_" + utils.filename_from_abspath(img) + "\"/>\n"
        buffer += "\t\t<div class=\"overlay\"><span id=\"c_" + utils.filename_from_abspath(img) + "\">" + short_prompt + "</span></div>\n"
        buffer += "\t\t<div class=\"hidden\" id=\"d_" + utils.filename_from_abspath(img) + "\">" + params['prompt'] + "</div>\n"
        buffer += "\t\t<div class=\"hidden\" id=\"p_" + utils.filename_from_abspath(img) + "\">" + param_string + "</div>\n"
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
    for f in files:
        if f.lower().endswith('.prompts'):
            full_path = os.path.abspath(control.config.get('prompts_location') + '/' + f)
            buffer += "\t\t\t<option value=\"" + full_path + "\">" + f.replace('.prompts', '') + "</option>\n"
    buffer += "\t\t</select>\n"

    buffer += "\t</div>\n"
    buffer += "\t<span class=\"tooltiptext\">All .prompt files in your&#xa;prompt folder appear here.</span>\n"
    buffer += "</div>\n"
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
        else:
            prompt_text = worker["job_prompt_info"].get('prompt')
            if worker["work_state"] != "":
                working_text = worker["work_state"]

            prompt_options_text = ""
            if worker["job_prompt_info"].get('input_image') != "":
                prompt_options_text = "init image: " + utils.filename_from_abspath(worker["job_prompt_info"].get('input_image'))
            else:
                prompt_options_text = 'size: ' + str(worker["job_prompt_info"].get('width')) + 'x' + str(worker["job_prompt_info"].get('height'))

            prompt_options_text += ' | steps: ' + str(worker["job_prompt_info"].get('steps')) \
                + ' | scale: ' + str(worker["job_prompt_info"].get('scale')) \
                + ' | samples: ' + str(worker["job_prompt_info"].get('samples'))
            exec_time = time.time() - worker["job_start_time"]
            clock_text = time.strftime("%M:%S", time.gmtime(exec_time))

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
        jobs = "{:,}".format(int(jobs_done))
        buffer_text += "</div><div>Total jobs done: " + jobs + "</div>"
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
            }
        })

        # if we're not in debug mode, enable production mode
        if not self.control_ref.config['debug_test_mode']:
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


        if self.control_ref.config['webserver_network_accessible']:
            control_ref.print("webserver listening for external requests...")
            cherrypy.config.update({'server.socket_host': '0.0.0.0'})

        cherrypy.config.update({'server.socket_port': self.control_ref.config['webserver_port']})
        webapp = ArtGenerator(self.control_ref)
        webapp.generator = ArtGeneratorWebService(self.control_ref)

        if not self.control_ref.config.get('webserver_console_log'):
            # disable console logging
            cherrypy.log.screen = False
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
