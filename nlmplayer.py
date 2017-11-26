# nlmplayer - simple audio player
#
# Author: Nicklesh Adlakha <nicklesh.adlakha@gmail.com>
# copyright (c) 2017 by Nicklesh Adlakha
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import audiotools
import alsaaudio
import audiotools.text as aerr
import threading
import termios

iloop = 1
wthrd = ""

if sys.argv.__len__() <= 1:
    print("Usage: %s [audio_file]" % sys.argv[0])
    sys.exit(1)

try:
    afile = audiotools.open(sys.argv[1])
    msg = audiotools.Messenger()

    aformat = alsaaudio.PCM_FORMAT_S16_LE if sys.byteorder == 'little' else alsaaudio.PCM_FORMAT_S16_BE

    if afile.supports_to_pcm():

        apcm = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK, mode=alsaaudio.PCM_NORMAL)
        apcm.setformat(aformat)
        apcm.setrate(afile.sample_rate())
        apcm.setchannels(afile.channels())

        """
        i)  Default periodsize is 32 frames per second.
        ii) frame size = sample size in bits * no of channels
                example: 16 * 2 = 32 bits/ 8 = 4 bytes
        iii) to avoid jitter we have used 256 frames as periodsize, kernel will maintain internal buffer          
        """

        apcm.setperiodsize(256)
        pcmr = afile.to_pcm()

        def thread_callback():

            oldaddr = termios.tcgetattr(sys.stdin.fileno())
            newattr = oldaddr
            newattr[3] = newattr[3] & ~termios.ICANON
            newattr[3] = newattr[3] & ~termios.ECHO

            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, newattr)

            global iloop

            while iloop:
                ch = sys.stdin.read(1)
                if (ch == 'j'):
                    istop = afile.sample_rate() * 10
                    i = 0

                    while i < istop:
                        if pcmr.read(256):
                            i += 256
                        else:
                            iloop = 0
                            break
            oldaddr[3] = oldaddr[3] | termios.ECHO
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, oldaddr)
     
        wthrd = threading.Thread(target=thread_callback)
        wthrd.start()

        if afile.supports_metadata():
            msg.info(unicode(afile.get_metadata()))

        while 1:
            buf = pcmr.read(256).to_bytes(False, True)
            if not len(buf):
                break

            apcm.write(buf)

        pcmr.close()
        apcm.close()
        iloop = 0
        if wthrd:
            wthrd.join()
    else:
        msg.warning(aerr.ERR_UNSUPPORTED_TO_PCM % {"filename" : sys.argv[1], "type" : afile.NAME})

except audiotools.UnsupportedFile:
    msg.warning(aerr.ERR_UNSUPPORTED_FILE % sys.argv[1])
except audiotools.InvalidFile as e:
    msg.warning(e)
except IOError as e:
    msg.warning(e)
except KeyboardInterrupt:
    iloop = 0
    pcmr.close()
    apcm.close()
