# Changelog

Dream Factory release notes.

When updating to a new release, use the built-in setup.py script with the --update option to ensure all required repos are refreshed:
```
python setup.py --update
```
## [2024.01.04]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **cf2772fab0af5573da775e7437e6acdca424f26e**

### Added
- Added support for the [ADetailer extension](https://github.com/Bing-su/adetailer). You can see some [initial docs here](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#adetailer_use). In my initial testing, ADetailer works especially well in **!MODE = process** .prompts files that target a directory full of pre-selected images that require some sort of specific fixing (e.g. more detail in faces or hands, etc).

### Changed
- Updated web UI footer copyright notice for the new year. Happy 2024!

## [2023.12.22]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **cf2772fab0af5573da775e7437e6acdca424f26e**

### Added
- Added option to specify a default model to use for upscaling directly from the integrated gallery via config.txt (see **PF_UPSCALE_OVERRIDE_CKPT_FILE** in config-default.txt). This is especially helpful when using SDXL main models, as you may specify a SD 1.5 model for upscales to dramatically reduce memory requirements (and thus allow higher resolution upscales).

### Fixed
- Added a startup wait/delay for the Automatic1111 API to be ready. If you were seeing startup errors related to Auto1111 API responses (likely due to models being stored on slow/NAS drives), this should solve your issue (thanks Koneko349!).
- Numerous minor/cosmetic fixes over the past few weeks that didn't warrant their own entries.

## [2023.10.14]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **5ef669de080814067961f28357256e8fe27544f4**

### Added
- Added support for [Ultimate SD Upscale extension](https://github.com/Coyote-A/ultimate-upscale-for-automatic1111#ultimate-sd-upscale-extension-for-automatic1111-stable-diffusion-web-ui) in **!MODE = process** .prompts files. See the bottom of [/prompts/example-process.prompts](https://github.com/rbbrdckybk/dream-factory/blob/main/prompts/example-process.prompts) for a usage example.

## [2023.09.22]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **5ef669de080814067961f28357256e8fe27544f4**

### Added
- Expanded [Hires Fix](https://github.com/rbbrdckybk/dream-factory#highres_fix) support. Dream Factory now supports the newer Auto1111 method of specifying your intial highres fix image size along with a scaling factor, and continues to support the old legacy method (of simply specifying your desired final output size). The old method is currently the default, check out **HIRES_FIX_MODE** in ```config-default.txt``` for documentation on how to switch.
- Added support for specifying hires fix [upscalers](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_upscaler), [models](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_ckpt_file), [samplers](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_sampler), [steps](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_steps), [prompts](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_prompt), and [negative prompts](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#highres_neg_prompt). This opens up lots of creative potential, including the ability to start image generation with an SDXL model and finish the hires fix step with an SD 1.5 model (all in a single request!). Note that you may use all of these features regardless of whether you switch to the new hires fix method or stick with the old way.
- Added support for [refiners](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#refiner_ckpt_file).
- All of the new hires/refiner .prompts directive metadata are visible within the integrated Dream Factory image gallery.

## [2023.08.01]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **68f336bd994bed5442ad95bad6b6ad5564a5409a**

### Added
- Added support for Automatic1111 styles in Dream Factory .prompts files via a new **!STYLES** directive ([see docs](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#styles)).

### Fixed
- When specifying a specific seed and using a queue of multiple models, the seed value will now only increment each time the entire model queue finishes (instead of after each model).

## [2023.07.31]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **68f336bd994bed5442ad95bad6b6ad5564a5409a**

### Added
- Added a .prompts file directive to [specify a VAE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#vae).
- Added a config.txt option **AUTO_USE_REFINER** that attempts to automatically find and use a refiner model when upscaling images created with SDXL models during !MODE=process .prompts file jobs, if enabled. See config-default.txt for usage explanation. My understanding is that this is not the intended way to use refiner models, but until Auto1111 adds proper support for them, this will allow you to upscale your SDXL images using the corresponding refiner model instead of the base model.
- Added a .prompts file directive **!OVERRIDE_MAX_OUTPUT_SIZE** that allows you to override your config.txt MAX_OUTPUT_SIZE setting within a !MODE=process .prompts file. Necessary for now since SDXL models seem to have much higher VRAM memory requirements (and thus lower max output size) than SD 1.5 models.
- Added a .prompts file directive **!OVERRIDE_CKPT_FILE** that allows you to override the model used for upscaling within a !MODE=process .prompts file (e.g. instead of using the same model that was used to generate the original image). Note that this may also be used to manually specify refiner models instead of the **AUTO_USE_REFINER** method above.

### Fixed
- SD upscale jobs in ```!MODE = process``` .prompts files will now properly use the same !CLIP_SKIP value as the original image.

## [2023.07.07]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **394ffa7b0a7fff3ec484bcd084e673a8b301ccc8**

### Fixed
- SD upscale jobs in ```!MODE = process``` .prompts files on images made with very early version of Dream Factory should no longer fail due to sampler errors.
- A single ```!MODE = process``` SD upscale job failing should no longer cause all remaining jobs in the queue to also fail.

## [2023.06.07]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **baf6946e06249c5af9851c60171692c44ef633e0**

### Added
- Added an icon to upscale an image directly from the integrated gallery (using SD img2img upscaling). To use, you'll need to add MAX_OUTPUT_SIZE to your Dream Factory config.txt file (see config-default.txt for explanation).

### Changed
- Modified some unclear startup messages.
- Hid the image gallery modal vertical scrollbar whenever it isn't needed.

## [2023.06.06]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **b6af0a3809ea869fb180633f9affcae4b199ffcf**

### Added
- Added the ability to use [SD upscale](https://github.com/rbbrdckybk/dream-factory#upscale_model) when running process mode (!MODE = process) .prompts files. You'll need to set the maximum image output size that your GPU is capable of producing in your Dream Factory config.txt file to enable this (see config-default.txt for example).

## [2023.06.04]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **b6af0a3809ea869fb180633f9affcae4b199ffcf**

### Added
- Added [civitai.com](https://civitai.com/) integration. Dream Factory will attempt to gather and cache information about your models, loras, embeddings, and hypernets from civitai.com in the background after every startup (e.g. friendly names, trigger words, base SD model). This info will be shown in the integrated editor reference. You may completely disable this functionality by adding **CIVITAI_INTEGRATION = no** to your Dream Factory config.txt file.
- Added editor reference support for subdirectories in your lora, embedding, and hypernet folders.

### Fixed
- The default [ControlNet control mode](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_controlmode) has been set to 'balanced', which should resolve errors when not setting it yourself while using ControlNet.
- Setting ControlNet's pre-processor to one of the reference modes (e.g.: **!CONTROLNET_PRE = reference_only**) should now allow ControlNet to activate without having to specify a ControlNet model.

## [2023.05.29]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **20ae71faa8ef035c31aa3a410b707d792c8203a3**

### Added
- Added support for the creation of [seamless tiled](https://github.com/rbbrdckybk/dream-factory/tree/main#seamless_tiling) output images.
- Support added for ControlNet [control mode](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_controlmode).
- Support added for ControlNet [pixel perfect mode](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_pixelperfect).

### Changed
- Updated ControlNet extension API calls to be compatible with the latest version (09cb9a32d1051aa827f1bb092cf17fcbf996ed7f).
- Added a warning when attempting to use ControlNet [guess mode](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_guessmode), as it has been removed in the latest version of the ControlNet extension (replaced by [control mode](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_controlmode)).
- Prompt file loading is now deferred until after all startup initialization is complete. This should prevent warnings when attempting to validate custom models before the list of valid models has been retrieved from Auto1111 via the API.

## [2023.04.16]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **a9fed7c364061ae6efb37f797b6b522cb3cf7aa2**

### Added
- Added additional support that should enable most ControlNet v1.1 functionality to work. Note that the ControlNet extension is under pretty heavy development at the moment and things may change. My own changes were tested against ControlNet extension hash ```d499bd4```. If you have old prompt files that make use of preprocessors, note that some of the name references may have changed (and that they don't necessarily match what is displayed in the Auto1111 UI) - this is unfortunately out of my hands as the names are now retrieved via API call.
- Support for ControlNet [guess mode](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_guessmode) is in.
- The [!STEPS directive now supports specifying a range](https://github.com/rbbrdckybk/dream-factory/issues/38).

### Changed
- The !SCALE and !STRENGTH directives also support specifying a range. !MIN_SCALE, !MAX_SCALE, !MIN_STRENGTH, and !MAX_STRENGTH are still supported (within random prompt files) if you already have .prompts files using the old syntax.
- Specifying a single period (".") as your prompt (or within any prompts section) will be considered an empty prompt. Useful if you have ```[prompts]``` sections full of settings directives but don't want to actually add anything else to your prompt. Or if you just actually want an empty prompt (e.g. for ControlNet guessmode, etc).

### Fixed
- Fixed an issue where prompts that started with a ```[``` character would cause the rest of that ```[prompts]``` section to be ignored.

## [2023.03.24]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **a9fed7c364061ae6efb37f797b6b522cb3cf7aa2**

### Added
- Added a mouseover preview for ControlNet pose images in the integrated editor.

### Changed
- Empty subdirectories in your image output folder will now be automatically be cleaned up whenever you switch prompt file or shutdown Dream Factory.
- The !OUTPUT_DIR directive (for !MODE=process prompt files) will now attempt to create the specified directory if it doesn't exist (and will fall back to your default output folder if it can't be created for whatever reason).

### Fixed
- Fixed a bug that could cause errors if you attempted to run a !MODE=process prompt file with no input image set.

## [2023.03.23]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **a9fed7c364061ae6efb37f797b6b522cb3cf7aa2**

### Added
- Added an **!UPSCALE_MODEL** directive ([docs](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#upscale_model)).
- Added a new .prompts file type for batch processing (**!MODE = process**). This is meant for advanced users to set up automated upscaling, metadata tagging, file re-naming & moving tasks within Dream Factory. You can see an [example process .prompts file here](https://github.com/rbbrdckybk/dream-factory/blob/main/prompts/example-process.prompts).

### Fixed
- Fixed an issue that caused the !REPEAT directive to not properly reset to the default (off) when new prompt files were loaded and no new directive was present.

## [2023.03.21]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **a9fed7c364061ae6efb37f797b6b522cb3cf7aa2**

### Added
- Added a **!CLIP_SKIP** directive ([see docs](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#clip_skip) for details).
- Added directives for IPTC metadata tagging (!IPTC_TITLE, !IPTC_DESCRIPTION, !IPTC_KEYWORDS, !IPTC_COPYRIGHT). [Docs/examples](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#iptc_title).
- Added some additional initial data handshaking with Auto1111 to grab available upscalers/scripts for future additions.

### Changed
- Modified setup.py to check dependancies and install any that are missing when running with the --update switch (```iptcinfo3``` is a new dependency; run ```python setup.py --update``` once to get this update, then again to check your dependencies).

## [2023.03.16]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **dfeee786f903e392dbef1519c7c246b9856ebab3**

### Added
- Added an **!AUTO_SIZE** directive that allows you to have your output image dimensions automatically calculated based on the dimensions or aspect ratio of input images or ControlNet input images ([see docs](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#auto_size)).

### Changed
- [!INPUT_IMAGE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#input_image) and [!CONTROLNET_INPUT_IMAGE](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#controlnet_input_image) now both accept directories as input, in addition to individual files.

### Fixed
- Fixed a bug that was preventing img2img calls with ControlNet enabled to disregard ControlNet settings.

## [2023.03.15]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **dfeee786f903e392dbef1519c7c246b9856ebab3**

### Added
- Added an **auto** option for !CONTROLNET_MODEL that will allow you have Dream Factory choose the proper ControlNet model automatically as long as your pose images are named appropriately (see [docs](https://github.com/rbbrdckybk/dream-factory#controlnet_model)).
- Added additional [custom filename variables](https://github.com/rbbrdckybk/dream-factory#filename) for input image, controlnet image, and controlnet model.

### Changed
- Changed web UI pages to use local cached versions of critical Javascript libraries instead of relying on remote CDNs.
- Preview images for ControlNet pose files can now be a different file format than the base pose file (so .jpg preview with a .png pose file or vice versa).
- Cleaned up various minor UI issues.

## [2023.03.13]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **dfeee786f903e392dbef1519c7c246b9856ebab3**

### Added
- Intitial support for ControlNet has been added. This is a fairly rough first cut, but it should be functional for those that want to give it a try. Note that the ControlNet API is fairly new and currently in a state of daily flux, so if you run into issues please ensure that the version of your ControlNet extension matches hash ```c73c9451``` (the latest at the time of this posting). [Instructions here should get you started](https://github.com/rbbrdckybk/dream-factory/edit/main/README.md#controlnet); please open issues if you find bugs!
- Added new reference buttons in the integrated prompt editor for your ControlNet models, preprocessors, and pose/input files (hidden if the ControlNet extension is not installed.
- Added ControlNet metadata to output files when enabled; details visible in the integrated gallery.

### Fixed
- Fixed an issue that prevented a previously-set input image from being cleared when set to nothing (!INPUT_IMAGE = ) via prompt file directive.

### Changed
- Hid the buttons for Hypernetwork / LoRA references in the integrated prompt editor if there are no user-installed hypernets/loras available.

## [2023.03.10]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **0cc0ee1bcb4c24a8c9715f66cede06601bfc00c8**

### Added
- New **JPG_QUALITY** option in config.txt that allows specifying the jpg compression quality of output images. See **config-defaults.txt** for usage example.

## [2023.02.28]
Tested & confirmed working with [Auto1111 version](https://github.com/rbbrdckybk/dream-factory#compatibility-with-automatic1111): **0cc0ee1bcb4c24a8c9715f66cede06601bfc00c8**

### Added
- LoRA reference added to the integrated prompt editor.
- Support for chaining prompt file jobs via a new **!NEXT_PROMPT_FILE** prompt file directive. See [docs](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#next_prompt_file) for reference and usage example.
- Added a help link on the integrated editor page that opens the [full command reference](https://github.com/rbbrdckybk/dream-factory#prompt-file-command-reference).

### Fixed
- Embeddings and Hypernetworks in .safetensors format will now properly show up in the integrated editor reference.
- Fix for potential broken images issue in user-defined gallery.
- Made initial config handshake with Auto1111 happen on a per-GPU basis instead of global to resolve a potential issue when running multiple GPUs.

## [2023.02.09]

### Added
- Support for custom output filenames via a new **!FILENAME** prompt file directive. See [docs](https://github.com/rbbrdckybk/dream-factory/blob/main/README.md#filename) for usage example and reference.
- Hypernetwork reference within the integrated prompt editor (Lora reference will be added as soon as it's available via the Auto1111 API).

### Fixed
- The image gallery will now properly show any hypernetwork/lora references within prompts (previously they were stripped out since <> tags were being treated as HTML).

### Changed
- When specifying custom seeds (via **!SEED = xxx**) within standard prompt files in combination with **!REPEAT = yes**, seed values will now be incremented on each completed loop to avoid creating duplicate images.

## [2023.01.25]

### Added
- Support for 'keyword:' when using the !AUTO_INSERT_MODEL_TRIGGER prompt file directive. For example, the following directive would replace the phrase 'replace_me' in prompts with the active model's configured trigger word:
```
!AUTO_INSERT_MODEL_TRIGGER = keyword:replace_me
```
This is mostly useful if you've trained a bunch of Dreambooth models and want to easily share a prompt file between them (e.g.: you have two models trained with tokens 'john man' and 'bob person'), or if you just want a high-degree of placement control over model token triggers.

### Fixed
- Corrected an issue that could cause the gallery page to fail to load if there were recent images with empty positive prompt metadata.

## [2023.01.23]

### Added
- Several changes to bring compatibility up to the current latest Automatic1111 version (```hash c98cb0f8ecc904666f47684e238dd022039ca16f```). Note that Dream Factory will operate with the original 'hires fix' behavior enabled (Auto1111 Settings -> Compatibility -> For hires fix...) to maintain compatibility with people running older versions of Auto1111. 

## [2023.01.09]

### Fixed
- Corrected an issue that could cause the gallery page's image deletion function to fail if the output directory/prompt file name contained spaces.
- Added some additional touch checks on mobile to help prevent pinch/zoom motions from being confused with swiping left/right/down.

## [2022.12.27]

### Added
- Added the ability to specify EDITOR_MAX_STYLING_CHARS in config.txt. This is a cutoff (in number of characters) where the integrated editor will not attempt to add context-sensitive color styling when displaying prompt files. If you work with large prompt files, you may want to alter this depending on your tolerance for longer load times when working with lengthy files. Remember you can always use an external editor to edit your .prompt files directly (web interfaces aren't great with large amounts of text)!

### Changed
- Added a vertical size constraint to images in the integrated gallery. Images should fit approximately within whatever display device you're using.

## [2022.12.18]

### Added
- Added the ability to specify multiple models with the !CKPT_FILE directive. When specifying multiple models, all of your prompts will be run against the first model, then the second, and so on. You can either use a comma-separated list (e.g. !CKPT_FILE = model01.ckpt, model02.ckpt, etc) or simply use '!CKPT_FILE = all' to specify that all of your models should be iterated through. In random mode, models will be switched every x prompts, where x can be defined with a new config.txt option (see RANDOM_QUEUE_SIZE in config-default.txt).

### Fixed
- Fixed an issue where GPU workers could appear to freeze on the status monitor page while new models were loading. 
- Fixed some malformed HTML on the status monitor page.

## [2022.12.15]

### Added
- Added support for wildcards in prompt files. See prompts/wildcards/colors.txt for an example.
- Added references to your available embeddings to the prompt editor's built-in help (if you have any).

### Fixed
- Fixed handling of 'PF_CKPT_FILE =' assignments in config.txt. Default model files set in config.txt will now be validated, and setting '!CKPT_FILE =' (e.g. setting the model to nothing) in prompt files will now properly default back to the validated config.txt setting.
- If you have '--autolaunch' set in your Auto1111 startup script, it will be ignored when starting Dream Factory (so it won't open a browser to the Auto1111 API).

### Changed
- Sorted the prompt file dropdown lists in both the prompt editor and control panel to appear in alphabetical order.
- Made significant improvements to the prompt editor's built-in help reference. Each help area now has its own button in the reference popup, and there is a bit of additional help context in each area regarding how to use models/wildcards/embeddings.

### Changed
- Sorted the reference samplers & models lists in the prompt editor to appear in alphabetical order.

## [2022.12.13]

### Fixed
- Fixed an that would cause no work to be queued if the active prompt file had an empty [prompts] section under certain conditions.
- Fixed an issue that would cause copying a sampler or model to the clipboard to fail from the prompt editor reference screen on non-https connections.

### Changed
- Sorted the reference samplers & models lists in the prompt editor to appear in alphabetical order.

## [2022.12.09]

If you're upgrading, you'll need to install **psutil**. You can either re-run setup.py, or just run this:
```
pip install psutil
```
### Added
- Added the ability to have Dream Factory automatically add the appropriate trigger word(s) to your prompts when using custom models. See **model-triggers.txt** in your dream-factory folder for more info (you'll need to run Dream Factory at least once after upgrading to generate this file). There is a new config.txt option that controls this behavior (see config-defaults.txt if you're upgrading).
- You can now put a 'catch-all' negative prompt in your config.txt file that will automatically be added to all new prompt files that you generate.

### Fixed
- Fixed an issue where the SD backend (auto1111) would leave child processes running in the background after Dream Factory was shut down.

## [2022.12.08]

### Added
- Added a model & sampler reference to the web GUI prompt editor. It shows a list of all samplers & models that are available to use; each item is clickable and will copy the appropriate prompt file directive to the clipboard. You can open it via the new button in the editor, or with ctrl+h.
- Added some additional error-handling around the txt2img and img2img workflows that should prevent Dream Factory from going into a state where it needs to be restarted due to GPU errors, or Auto1111 returning error responses.

### Fixed
- Fixed an issue where '.png' could be incorrectly appended to the seed value saved to image EXIF.

## [2022.12.06]
This is a major release; pretty much every piece of code has been touched and the entire backend has been re-done. **I highly recommend a fresh install!**

### Added
- Completely replaced the Stable Diffusion backend (which was previously a mix of my own SD repo and [basujindal's fork](https://github.com/basujindal/stable-diffusion), which seems to be mostly abandoned) with [Automatic1111's popular repo](https://github.com/AUTOMATIC1111/stable-diffusion-webui). This means that pretty much all of Automatic1111's [many features](https://github.com/AUTOMATIC1111/stable-diffusion-webui#features) are now available within Dream Factory! Some highlights:
  - Support for many more samplers.
  - Support for SD 2.0 models.
  - Support for [prompt weighting](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#attentionemphasis) within prompt files.
  - Support for the [highres fix](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#highres-fix), allowing for much more coherent images over 512x512.
  - Support for [prompt editing](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#prompt-editing).
  - Support for [Codeformer](https://github.com/sczhou/CodeFormer) as a face enhancement/restoration option alongside GFPGAN.
- Added staggered GPU startup for multi-GPU systems to help prevent system RAM issues during initialization.
- Added a sampler and model reference to new prompt files created via the web interface.
- Added !UPSCALE_GFPGAN_AMOUNT and !UPSCALE_CODEFORMER_AMOUNT as prompt file directives, allowing you to specify the degree of face enhancement you want (from 0.0 to 1.0 for either or both options).

### Fixed
- Corrected many bugs with multi-GPU operation. Just spent the past 36 hours watching Dream Factory churn out images non-stop on a 3-GPU machine powered by a circa-2013 single-core AMD Sempron with 6GB of physical RAM (16GB with a swap file to get through model loads). Mostly confident that everything is working properly now, but report issues if you find them!
- Corrected a bug where setting **!INPUT_IMAGE =** in prompt files didn't properly clear an existing input image.

### Changed
- Models are now kept in memory on each GPU, instead of being discarded after each prompt call. This results in much faster performance.
- Dream Factory's setup script (setup.py) now installs far fewer python dependancies. Again, recommend a fresh install if you want to keep things clean.

### Removed
- !SD_LOW_MEMORY and !SD_LOW_MEM_TURBO have been removed as prompt file directives as they would no longer serve a purpose. Dream Factory will use whatever VRAM flags you've set for your Auto1111 installation, if any (most users won't need to worry about them).
- !UPSCALE_FACE_ENH has been removed as a prompt file directive, replaced by !UPSCALE_GFPGAN_AMOUNT and !UPSCALE_CODEFORMER_AMOUNT (see above).

## [2022.11.15]
### Fixed
- Corrected an issue with setup.py that was causing pytorch to be installed incorrectly.
- Corrected a bug that would throw an error when a single gpu id was manually specified in config.txt.

## [2022.10.20]
### Fixed
- Corrected a fomatting bug that would cause the control panel and status monitor to fail to load in the web UI when total completed jobs became greater than 999.
- Corrected an issue that wouldn't correctly enable webserver console logging in all cases when **WEBSERVER_CONSOLE_LOG = yes** was set in config.txt.

## [2022.10.15]
### Added
- Added negative prompt support, specify with **!NEG_PROMPT** directive in .prompt files.
- Added support for additional samplers. Specify with the **!SAMPLER** directive in .prompt files. Note that not all samplers are available in all modes currently - if you're using the low-memory-optimized mode with txt2img, you should have access to all of them (plms, ddim, lms, euler, euler_a, dpm2, dpm2_a, heun). 
- Added ability to specify a default model checkpoint file and sampler in global config.txt file; see config-default.txt for example.
- Added sampler, negative prompt, and model checkpoint (when not the default model.ckpt) to output EXIF, and display in internal web UI gallery.
- Updated example prompt files with **!CKPT_FILE**, **!SAMPLER**, and **!NEG_PROMPT** usage.

### Fixed
- Corrected a bug when specifying a custom seed with **!SEED**.
- Additional error-checking in setup.py for cases where required executables can't be located. Should handle gracefully now and prompt the user to re-run setup with a new **--shell** option.

## [2022.10.03]
### Added
- Added ability to specify which checkpoint to use in prompt files with **!CKPT_FILE** directive. If you use a relative path, it'll be relative from your /stable_diffusion subdirectory, hence the default is **!CKPT_FILE = models/ldm/stable-diffusion-v1/model.ckpt**. Useful if you've created your own .ckpt file(s) with DreamBooth or some other method and want to switch between them!

## [2022.10.02]
### Fixed
- Several UTF-8 character encoding issues with prompt file and EXIF metadata handling have been corrected.
- Quotation marks in prompts should no longer cause issues.
- Fixed an editor issue where it was possible to clear the entire document using by undo (ctrl-z) too many times.

## [2022.09.28]
### Added
- Initial soft release. Things should mostly work, but expect some issues.
