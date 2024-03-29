## Pre-requisites ##
* pkg-config
* Download audiotools from `https://audiotools.sourceforge.net/install.html`

## Compiling / Installing ##
* `Untar` audiotools
* `cd` audiotools
* `export CFLAGS="-DPY_SSIZE_T_CLEAN"`
* `python3 setup.py build`
* `python3 setup.py install`
* `pip3 install pyalsaaudio`

## Running ##
### nnet examples ###
* python3 nnet.py -s -ip example.com -p 80 ## stealth scanning
* python3 nnet.py -s -w 4 -ip example.com -p 80 ## stealth scanning with wait [in minutes]
* python3 nnet.py -ip example.com -p 3456 ## client
* python3 nnet.py -l -ip yourip.com -p 3456 ## server
### nlmplayer examples (supported files - mp2, mp3, m4a, ogg / vorbis, flac, opus, wav, sun au, wavpack, aiff, apple lossless) ###
* python3 nlmplayer audio_file.mp3
