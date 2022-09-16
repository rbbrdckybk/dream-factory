# Copyright 2021 - 2022, Bill Kennedy (https://github.com/rbbrdckybk/ai-art-generator)
# SPDX-License-Identifier: MIT

import os, os.path
import random
import string
import time
import scripts.utils as utils
from datetime import datetime, timedelta
import cherrypy
from cherrypy.lib import auth_basic


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
        elif control.get_mode() == 'combination':
            #buffer += "\t\t6 of 100 prompt combinations completed | loops done: 1 | repeat: on\n"
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



def build_prompt_dropdown(control):
    buffer = "<label for=\"prompt-file\">Choose a new prompt file:</label>\n"
    buffer += "<select name=\"prompt-file\" id=\"prompt-file\" class=\"prompt-dropdown\" onchange=\"new_prompt_file()\">\n"
    buffer += "\t<option value=\"\">select</option>\n"
    files = os.listdir(control.config.get('prompts_location'))
    for f in files:
        if f.lower().endswith('.prompts'):
            full_path = os.path.abspath(control.config.get('prompts_location') + '/' + f)
            buffer += "\t<option value=\"" + full_path + "\">" + f.replace('.prompts', '') + "</option>\n"
    buffer += "</select>\n"
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
    @cherrypy.expose
    def index(self):
        return open('./server/index.html')


@cherrypy.expose
class ArtGeneratorWebService(object):
    def __init__(self, control_ref):
        self.control = control_ref

    @cherrypy.tools.accept(media='text/plain')
    def GET(self):
        pass

    def POST(self, type, arg):
        if type.lower().strip() == 'prompt_file':
            self.control.new_prompt_file(arg)

    def WORKER_REFRESH(self):
        buffer_text = build_worker_panel(self.control.workers)
        return buffer_text

    def PROMPT_REFRESH(self):
        buffer_text = build_prompt_panel(self.control)
        return buffer_text

    def PROMPT_DROPDOWN_LOAD(self):
        buffer_text = build_prompt_dropdown(self.control)
        return buffer_text

    def BUFFER_REFRESH(self):
        buffer_text = ""
        for i in self.control.output_buffer:
            buffer_text += i
        return buffer_text

    def STATUS_REFRESH(self):
        jobs_done = "{:,}".format(self.control.total_jobs_done)
        # we'll pass back whether or not the server is paused as the first char
        buffer_text = "n<div>Server is running</div>"
        if self.control.is_paused:
            buffer_text = "y<div style=\"color: yellow;\">Server is paused</div>"
        buffer_text += "<div>Server uptime: "
        diff = time.time() - self.control.server_startup_time
        buffer_text += "{}".format(str(timedelta(seconds = round(diff, 0))))
        buffer_text += "</div><div>Total jobs done: " + jobs_done + "</div>"
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
        self.config = {
            '/': {
                'tools.sessions.on': True,
                'tools.staticdir.root': os.path.abspath(os.getcwd())
            },
            '/generator': {
                'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [('Content-Type', 'text/plain')],
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': './server'
            }
        }

    def start(self, control_ref):
        self.control_ref = control_ref
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
                },
                '/generator': {
                    'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                    'tools.response_headers.on': True,
                    'tools.response_headers.headers': [('Content-Type', 'text/plain')],
                },
                '/static': {
                    'tools.staticdir.on': True,
                    'tools.staticdir.dir': './server'
                }
            }

        cherrypy.config.update({'server.socket_port': self.control_ref.config['webserver_port']})
        webapp = ArtGenerator()
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
