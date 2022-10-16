# Changelog

Dream Factory release notes.

When updating to a new release, use the built-in setup.py script with the --update option to ensure all required repos are refreshed:
```
python setup.py --update
```

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
