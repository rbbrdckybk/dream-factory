# Dream Factory



Multi-threaded GUI manager for mass creation of AI-generated art with support for multiple GPUs.

This is aimed at the user that wants to create a **lot** of AI artwork with minimal hands-on time. If you're looking for a repo that will allow you to spend hours tweaking a single image until it's perfect, [there are better options](https://github.com/AUTOMATIC1111/stable-diffusion-webui) (update 2022-12-06: Dream Factory now uses Automatic1111's repo on the backend so you'll get the best of both worlds!). If you have hundreds of prompt ideas and want to easily and quickly (well, as quickly as your GPUs can manage!) see them rendered in hundreds of different variations and/or styles, then this is for you.

To illustrate, I've had an RTX 3060, RTX 3080Ti, and Tesla M40 running Dream Factory 24/7 for a couple weeks now, and they churn out many thousands of images every day! Some samples (all straight out of Dream Factory other than some minor sharpening applied in Photoshop):  
<table>
 <tr>
  <td><img src="/images/01.jpg" width="152" height="152" alt="sample image 1" title="sample image 1"></td>
  <td><img src="/images/02.jpg" width="152" height="152" alt="sample image 2" title="sample image 2"></td>
  <td><img src="/images/03.jpg" width="152" height="152" alt="sample image 3" title="sample image 3"></td>
  <td><img src="/images/04.jpg" width="152" height="152" alt="sample image 4" title="sample image 4"></td>
 </tr>
 <tr>
  <td><img src="/images/05.jpg" width="152" height="152" alt="sample image 5" title="sample image 5"></td>
  <td><img src="/images/06.jpg" width="152" height="152" alt="sample image 6" title="sample image 6"></td>
  <td><img src="/images/07.jpg" width="152" height="152" alt="sample image 7" title="sample image 7"></td>
  <td><img src="/images/08.jpg" width="152" height="152" alt="sample image 8" title="sample image 8"></td>
 </tr>
 <tr>
  <td><img src="/images/09.jpg" width="152" height="152" alt="sample image 9" title="sample image 9"></td>
  <td><img src="/images/10.jpg" width="152" height="152" alt="sample image 10" title="sample image 10"></td>
  <td><img src="/images/11.jpg" width="152" height="152" alt="sample image 11" title="sample image 11"></td>
  <td><img src="/images/12.jpg" width="152" height="152" alt="sample image 12" title="sample image 12"></td>
 </tr>
</table>

Some UI screenshots:
<table>
 <tr>
  <td><img src="/images/screen_monitor.png" width="152" height="152" alt="UI: status monitor" title="UI: status monitor"></td>
  <td><img src="/images/screen_editor.png" width="152" height="152" alt="UI: prompt editor" title="UI: prompt editor"></td>
  <td><img src="/images/screen_gallery.png" width="152" height="152" alt="UI: gallery" title="UI: gallery"></td>
  <td><img src="/images/screen_gallery_image.png" width="152" height="152" alt="UI: image viewer" title="UI: image viewer"></td>
 </tr>
</table>

# Features

 * Based on [Stable Diffusion](https://stability.ai/blog/stable-diffusion-public-release).
 * Dream Factory acts as a powerful automation and management tool for the popular [Automatic1111 SD repo](https://github.com/AUTOMATIC1111/stable-diffusion-webui#features). Integration with Automatic1111's repo means full support for a rapidly-expanding feature set.
 * Multi-threaded engine capable of simultaneous, fast management of multiple GPUs. As far as I'm aware, Dream Factory is currently one of the only Stable Diffusion options for true multi-GPU support.
 * Powerful custom prompt file format that allows you to easily define compound prompt templates. Want to quickly create thousands of prompts from a template like "_photo of a **[adjective(s)] [animal]** as a **[profession]**, art by **[artist(s)]**, **[keyword(s)]**_" where each bracketed section needs to be filled in with dozens (or hundreds) of different items? No problem. Maybe you want your GPUs to create every possible combination, or maybe you want combinations to be picked randomly? Your choice. Maybe you want some items to be handled with different settings? Totally doable. Prompt files can be as complex or simple as you want — you can simply paste in a list of stand-alone prompts and go, too!
 * Dream Factory can automatically add custom model trigger word(s) to your prompts. For example, if you're using [this Modern Disney Style model](https://huggingface.co/nitrosocke/mo-di-diffusion), you need to add 'modern disney style' to each of your prompts. If you use a lot of custom models, it can be difficult to always remember to do this. Let Dream Factory handle it for you!
 * All prompt and creation settings are automatically embedded into output images as EXIF metadata (including the random seed used). Never wonder how you created an image again!
 * Easy web interface. Includes a built-in prompt file editor with context-sensitive highlighting, a gallery that displays your prompts and creation settings alongside your images, and at-a-glance information about the status of completed/ongoing work. Hate web interfaces? Turn it off via a configuration file — Dream Factory can be run completely via the command line if that's your thing!
 * Remote management. Access and fully manage your Dream Factory installation from anywhere (and easily download your created images in bulk as .zip files!). Can be configured to be accessible via LAN, WAN (internet), or just locally on the computer that Dream Factory is running on. Includes very basic HTTP-based authentication for WAN access.
 * Integrated optional [ESRGAN upscaling](https://github.com/xinntao/ESRGAN) with [GFPGAN face correction](https://xinntao.github.io/projects/gfpgan). 
 * Easy setup. If you can download a file and copy & paste a few lines ([see below](https://github.com/rbbrdckybk/dream-factory/edit/main/README.md#setup)), you can get this working. Uses Anaconda so Dream Factory will happily run alongside other Stable Diffusion repos without disturbing them.

# Requirements

You'll need at least one Nvidia GPU, preferably with a decent amount of VRAM. 3GB of VRAM should be enough to produce 512x512 images, but more GPU memory will allow you to create larger images (and/or create them faster).

You'll also need a working [Automatic1111 Stable Diffusion webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui#installation-and-running).

# Setup

These instructions were tested on several Windows 10 desktops with a variety of modern Nvidia GPUs ranging from 8-12GB VRAM, and also on an Ubuntu Server 20.04.3 system with an old Nvidia Tesla M40 GPU (24GB VRAM).

**[1]** Install [Anaconda](https://www.anaconda.com/products/individual), open the root terminal, and create a new environment (and activate it):
```
conda create --name dream-factory python=3.9
conda activate dream-factory
```

**[2]** Install a couple required Python packages:
```
conda install -c anaconda git urllib3
```

**[3]** Clone this repository and switch to its directory:
```
git clone https://github.com/rbbrdckybk/dream-factory
cd dream-factory
```

**[4]** Run the included setup script to finish the rest of your installation automatically:
```
python setup.py
```

**[5]** Edit your config.txt file to specify the full path to your Automatic1111 SD installation:
 * Look for the **SD_LOCATION =** entry near the top of the file.
 * On Windows, it should look something like **SD_LOCATION = C:\Applications\stable-diffusion-webui** when finished, depending on where you placed Automatic1111's webui.
 * On Linux, you'll want something like **SD_LOCATION = /home/[username]/stable-diffusion-webui**, where [username] is the linux user it was installed under, assuming you kept the default install location.

You're done! Ensure that your [Automatic1111 installation works properly](https://github.com/AUTOMATIC1111/stable-diffusion-webui#installation-and-running) before attempting to test Dream Factory. Additionally, ensure that everything in the "settings" tab of Auto1111 is configured to your liking, as Dream Factory will automatically inherit any options you set there.

Once you've verified that you can generate individual images with your Auto1111 installation, you can perform a test to make sure Dream Factory is working by running this (again, from the main **dream-factory** folder):
```
python dream-factory.py --prompt_file prompts/example-standard.prompts
```
This should start up the web interface with a simple example prompt file pre-loaded that your GPU(s) should start working on automatically. On the first run, several large files (~2GB total) will be downloaded automatically so it may take a few minutes before things start happening.

Eventually you should see images appearing in your **\output** folder (or you can click on the "Gallery" link within the web UI and watch for them there). If you're getting images, everything is working properly and you can move on to the next section.

# Usage

Instructions assume that you've completed [setup](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#setup) and verified that your installation works properly.

## Startup and Basic Usage

Start Dream Factory with:
```
python dream-factory.py
```
The web UI should open automatically, if not go to http://localhost:8080 (assuming you didn't change the port in config.txt) via your browser. Your GPU(s) will automatically start initializing (each GPU will take about as long as it takes to launch auto1111 in standalone mode).

Browse to 'Control Panel' in the top nav and select one of the two example prompt files via the dropdown. Your GPU(s) should start working on whichever one you choose as soon as they're finished initializing. You can browse back to 'Status Monitor' and should see that your GPU(s) are being assigned work from the selected prompt file. If you browse to 'Gallery' in the top nav you'll see images appearing as they're completed.

## Creating and Editing Prompt Files

Prompt files are the heart of Dream Factory and define the work that you want your GPU(s) to do. They can be as simple or as complex as you want.

### Example Prompt Files

Before we get into creating new prompt files, let's take a look at the two example prompt files that are included with Dream Factory. Start by clicking 'Prompt Editor' in the top nav, then choose 'example-standard' in the 'Choose a prompt file:' dropdown.

You should see the prompt file load into the editor. Prompt files have an optional [config] section at the top with directives that define your Stable Diffusion settings, and at least one [prompts] section that contains prompts (or sections of prompts to be combined with other [prompts] sections).

The example files contain comments that should make it fairly clear what each [config] directive does, and how the [prompts] sections will combine. See the [Command Reference](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#prompt-file-command-reference) below for help on any directives that aren't clear.

### Creating a New Prompt File

You can create prompt files by using the integrated editor (click 'Prompt Editor' in the top nav, then click 'New Standard' or 'New Random' to start a new file). Prompt files will automatically be created with a skeleton containing common directives and the default settings contained in your config.txt.

After creation, prompt files can be renamed by simply clicking on the name at the top of the editor, entering a new name, and then clicking 'Rename'.

If you'd prefer, you can also create prompt files externally using a text editor of your choice (name them with a .prompt extension and place them in your prompts folder). If you happen to use [Notepad++](https://notepad-plus-plus.org/), there is a plugin in the **dream-factory/prompts/notepad_plugin** folder that will add context-sensitive highlighting to .prompt files.

### Prompt File Command Reference

These directives are valid only in the [config] section of both standard and random prompt files:

 * [!MODE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#mode)
 * [!DELIM](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#delim)

These directives are valid in both the [config] section of both standard and random prompt files **and** also in any [prompts] section of **standard** prompt files (!MODE = standard):

 * [!WIDTH](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#width)
 * [!HEIGHT](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#height)
 * [!HIGHRES_FIX](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_fix)
 * [!STEPS](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#steps)
 * [!SAMPLER](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#sampler)
 * [!SCALE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#scale)
 * [!SAMPLES](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#samples)
 * [!BATCH_SIZE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#batch_size)
 * [!INPUT_IMAGE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#input_image)
 * [!STRENGTH](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#strength)
 * [!CKPT_FILE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#ckpt_file)
 * [!NEG_PROMPT](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#neg_prompt)
 * [!AUTO_INSERT_MODEL_TRIGGER](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#auto_insert_model_trigger)
 * [!SEED](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#seed)
 * [!USE_UPSCALE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#use_upscale)
 * [!UPSCALE_AMOUNT](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#upscale_amount)
 * [!UPSCALE_CODEFORMER_AMOUNT](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#upscale_codeformer_amount)
 * [!UPSCALE_GFPGAN_AMOUNT](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#upscale_gfpgan_amount)
 * [!UPSCALE_KEEP_ORG](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#upscale_keep_org)

These directives are valid only in the [config] section of **standard** prompt files (!MODE = standard):

 * [!REPEAT](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#repeat)

Finally, these directives are valid only in the [config] section of **random** prompt files (!MODE = random):

 * [!MIN_SCALE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#min_scale)
 * [!MAX_SCALE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#max_scale)
 * [!MIN_STRENGTH](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#min_strength)
 * [!MAX_STRENGTH](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#max_strength)
 * [!RANDOM_INPUT_IMAGE_DIR](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#random_input_image_dir)

Command Help and Usage Examples:

#### !MODE
Sets the prompt file mode to either **standard** (default) or **random**. Standard prompt files work by iterating through all possible [prompts] sections combinations, and random prompt files simply pick prompts at random from [prompts] sections. See prompts/example-standard.prompts and prompts/example-random.prompts for a detailed walkthrough of how each mode works.
```
!MODE = standard
```
#### !DELIM
Sets the delimiter that will be used when joining [prompts] sections (default is a space). For example, if you have two [prompts] sections, and the top entry in the first is "a portrait of" and the top entry in the second is "a cat", then when the two sections are combined, you'd end up with "a portrait of a cat" if !DELIM = " ". 
```
!DELIM = " "
```
#### !WIDTH
Sets the output image width, in pixels (default is 512). Note that this must be a multiple of 64!
```
!WIDTH = 512
```
#### !HEIGHT
Sets the output image height, in pixels (default is 512). Note that this must be a multiple of 64!
```
!HEIGHT = 512
```
#### !HIGHRES_FIX
Enables or disables the Auto1111 [highres fix](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#highres-fix). Valid options are **yes** or **no** (default). This should be enabled when generating images at resolutions signficantly higher than 512x512.
```
!HIGHRES_FIX = no
```
#### !STEPS
The number of denoising steps (default = 20). More steps will generally improve image quality to a point, at the cost of processing time.
```
!STEPS = 20
```
#### !SAMPLER
The sampler to use (default is DPM++ 2M Karras). This must match an available option in your Auto1111 SD webui exactly. You can press ctrl+h or click the help icon at the top right corner of the editor to see a reference list of available samplers (click on a sampler to copy it to the clipboard so that you can easily paste it into the editor).
```
!SAMPLER = DPM++ 2M Karras
```
#### !SCALE
The guidance scale, or how closely you want Stable Diffusion to follow your text prompt. The default is 7.5, and generally speaking useful values are between 5 - 30.
```
!SCALE = 7.5
```
#### !SAMPLES
How many images to produce of each prompt before moving on to the next one (default = 1). Unlike the below BATCH_SIZE option, there is no additional cost in terms of GPU memory when increasing this. There will be a liner increase in processing time when increasing this (e.g.: !SAMPLES = 10 will take ten times as long as !SAMPLES = 1).
```
!SAMPLES = 1
```
#### !BATCH_SIZE
How many images you want each GPU to produce in parallel (default = 1). Each increase of BATCH_SIZE will require more GPU VRAM, and setting this value too high will cause GPUs to run out of memory and crash. However, as long as you know you have enough VRAM, you can achieve moderate speed gains by increasing this beyond 1. This is an advanced setting and isn't included in new prompt file templates, however you may manually add it to your prompt files.
```
!BATCH_SIZE = 1
```
#### !INPUT_IMAGE
Sets an image to use as a starting point for the denoising process, rather than the default random noise. This can be a relative (to the Dream Factory base directory) or absolute path, and setting this to nothing will clear any previously-set input image.
```
!INPUT_IMAGE = C:\images\dog.png                         # specifies the full path to an input image
!INPUT_IMAGE = cat.jpg                                   # specifies an input image 'cat.jpg' in the DF home directory
!INPUT_IMAGE =                                           # specifies no input image should be used
```
#### !STRENGTH
Sets the strength of the input image influence. Valid values are 0-1 (default = 0.75). Values close to 0 will result in an output image very similar to the input image, and values close to 1 will result in images with less resemblence. Generally, values between 0.2 - 0.8 are most useful. Note that this is also used when !HIGHRES_FIX = yes to indicate how closely the final image should mirror the low-res initialization image.
```
!STRENGTH = 0.75
```
#### !CKPT_FILE
Sets the model to use. Any custom models should be installed to the appropriate models directory of your auto1111 installation. You can press ctrl+h or click the help icon at the top right corner of the editor to see a reference list of available models (click on a model to copy it to the clipboard so that you can easily paste it into the editor). Setting this to nothing will default back to whatever model you have set in your config.txt file (if you haven't set a default, setting this to nothing won't do anything!).

You many also set a list of comma-separated models here. In standard mode, Dream Factory will render all prompts with the first model, then the second, and so on. In random mode, Dream Factory will switch models every 50 prompts (this interval can be changed in your config.txt file).

You may also use the reserved word "all" here, and Dream Factory will rotate through all of your available models automatically.
```
!CKPT_FILE = analog-style.ckpt                           # sets a new model to use
!CKPT_FILE = sd-v1-5-vae.ckpt, analog-style.ckpt         # sets 2 models to rotate between
!CKPT_FILE = all                                         # will rotate between all of your models
!CKPT_FILE =                                             # sets the default model specified in your config.txt
```
#### !NEG_PROMPT
Specifies a negative prompt to be used for all of the prompts that follow it (remember you can place most directives directly into [prompts] sections of standard prompt files!). If you have a 'catch-all' negative prompt that you tend to use, you can specify it in your config.txt file and it'll be populated as the default on new prompt files you create. Setting this to nothing will clear the negative prompt.
```
!NEG_PROMPT = watermark, blurry, out of focus
```
#### !AUTO_INSERT_MODEL_TRIGGER
For use with custom models that require a 'trigger word' that has been set up in your model-triggers.txt file (see [Custom Models] below). This allows you to control the placement of the automatically-inserted trigger word. Valid options are **start** (default), **end**, **first_comma**, and **off**: 'start' will put the trigger word at the front of the prompt, 'end' will place it at the end, 'first_comma' will place it after the first comma (or at the end if there is no comma in the prompt), and 'off' will disable auto-insertion entirely.
```
!AUTO_INSERT_MODEL_TRIGGER = start
```
#### !SEED
Specifies the seed value to be used in image creation. This value is normally chosen at random - using the same settings with the same seed value should produce exactly the same output image. Setting this to nothing will indicate that random seed values should be used (the default). This is an advanced setting and isn't included in new prompt file templates, however you may manually add it to your prompt files.
```
!SEED = 42
```
#### !USE_UPSCALE
Whether or not every output image should automatically be upscaled. Upscaling can take a significant amount of time, so generally you'd only want to do this on a subset of selected images. Valid options are **yes** or **no** (default).
```
!USE_UPSCALE = no
```
#### !UPSCALE_AMOUNT
The factor to upscale by. Setting !UPSCALE_AMOUNT = 2 will double the width and height of an image (resulting in quadruple the resolution). Has no effect unless !USE_UPSCALE = yes.
```
!UPSCALE_AMOUNT = 2
```
#### !UPSCALE_CODEFORMER_AMOUNT
The visibility of [Codeformer face enhancement](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#face-restoration) on the output image. Valid values are between 0-1. Setting this to 0 disables Codeformer enhancement entirely. Has no effect unless !USE_UPSCALE = yes.
```
!UPSCALE_CODEFORMER_AMOUNT = 0.50
```
#### !UPSCALE_GFPGAN_AMOUNT
The visibility of [GFPGAN face enhancement](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#face-restoration) on the output image. Valid values are between 0-1. Setting this to 0 disables GFPGAN enhancement entirely. Has no effect unless !USE_UPSCALE = yes.
```
!UPSCALE_GFPGAN_AMOUNT = 0.50
```
#### !UPSCALE_KEEP_ORG
When upscaling, keep the original (non-upscaled) image as well? Valid options are **yes** or **no** (default). If set to yes, originals will be stored in an /originals sub-directory off the main output folder. Has no effect unless !USE_UPSCALE = yes.
```
!UPSCALE_KEEP_ORG = no
```
#### !REPEAT
Tells Dream Factory whether or not to continuing producing images after it has finished all possible combinations in the prompt file. Options are **yes** (default) or **no**. If set to no, Dream Factory will idle after it has completed all prompts.
```
!REPEAT = yes
```
#### !MIN_SCALE
When using random mode prompt files, sets the minimum !SCALE value to use. If !MIN_SCALE and !MAX_SCALE are set to different values, Dream Factory will choose a random value between them for each prompt.
```
!MIN_SCALE = 6.0
```
#### !MAX_SCALE
When using random mode prompt files, sets the maximum !SCALE value to use. If !MIN_SCALE and !MAX_SCALE are set to different values, Dream Factory will choose a random value between them for each prompt.
```
!MIN_SCALE = 18.5
```
#### !MIN_STRENGTH
When using random mode prompt files, sets the minimum !STRENGTH value to use. If !MIN_STRENGTH and !MAX_STRENGTH are set to different values, Dream Factory will choose a random value between them for each prompt.
```
!MIN_STRENGTH = 0.45
```
#### !MAX_STRENGTH
When using random mode prompt files, sets the maximum !STRENGTH value to use. If !MIN_STRENGTH and !MAX_STRENGTH are set to different values, Dream Factory will choose a random value between them for each prompt.
```
!MAX_STRENGTH = 0.80
```
#### !RANDOM_INPUT_IMAGE_DIR
When using random mode prompt files, sets a directory that random input images should be pulled from. If this is set, Dream Factory will choose a random input image to use for each prompt.
```
!RANDOM_INPUT_IMAGE_DIR = C:\images                      # specifies the full path to a directory containing input images
!RANDOM_INPUT_IMAGE_DIR = images                         # specifies a relative path to a directory containing input images
!RANDOM_INPUT_IMAGE_DIR =                                # specifies no input images should be used
```

# Advanced Usage

TODO

## Wildcards

TODO

## Custom Models

TODO

## Embeddings

TODO

# Updating Dream Factory

You can update Dream Factory to the latest version by typing:
```
python setup.py --update
```
