# Soundfonts Directory

This directory contains soundfont (SF2) files used for MIDI rendering with FluidSynth.

## Default Soundfont

The application expects a soundfont file named `FluidR3_GM.sf2` in this directory.

## Custom Soundfont Directory

You can specify a custom soundfont directory by setting the `SOUNDFONT_DIR` environment variable:

```bash
export SOUNDFONT_DIR=/path/to/your/soundfonts
```

The application will look for `FluidR3_GM.sf2` in the specified directory.

## Where to Get Soundfonts

Free soundfonts can be found at:
- [MuseScore SoundFonts](https://musescore.org/en/handbook/soundfonts-and-sfz-files)
- [FluidSynth GitHub](https://github.com/FluidSynth/fluidsynth/tree/master/sf2)
- [Soundfont Archive](https://archive.org/details/soundfonts)
