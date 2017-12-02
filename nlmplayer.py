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
import os
import select
from fcntl import fcntl, F_GETFL, F_SETFL
from signal import signal, pthread_kill, SIGALRM

iloop = 1
oloop = 1
cframes = 0
wthrd = ""

if sys.argv.__len__() <= 1:
    print("Usage: %s [audio_file]" % sys.argv[0])
    sys.exit(1)

def signal_handler(signum, frame):
    pass

signal(SIGALRM, signal_handler)

msg = audiotools.Messenger()

try:
    afile = audiotools.open(sys.argv[1])
    mixer = alsaaudio.Mixer()
    cvol = mixer.getvolume()[0]

    dtemplate = "[keypress]: j to jump 10 seconds forward, q to quit, " \
                "v to increase the vol by 10%%, d to decrease the vol by " \
                "10%%, " \
                "current vol gain [%s]%%"
    pgrs = audiotools.SingleProgressDisplay(msg, dtemplate % cvol)

    sframes = afile.total_frames()
    aformat = alsaaudio.PCM_FORMAT_S16_LE if sys.byteorder == 'little' else \
        alsaaudio.PCM_FORMAT_S16_BE
    lock = threading.Lock()

    if afile.supports_to_pcm():
        apcm = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK,
                             mode=alsaaudio.PCM_NORMAL)
        apcm.setformat(aformat)
        apcm.setrate(afile.sample_rate())
        apcm.setchannels(afile.channels())

        """
        i)   Default periodsize is 32 frames per second.
        ii)  frame size = sample size in bits * no of channels
             example: 16 * 2 = 32 bits/ 8 = 4 bytes
        iii) to avoid jitter we have used 512 frames as periodsize, 
             kernel will maintain internal buffer          
        """

        apcm.setperiodsize(512)
        pcmr = afile.to_pcm()

        def thread_callback():
            try:
                stdin_fd = sys.stdin.fileno()
                oldaddr = termios.tcgetattr(stdin_fd)
                newattr = oldaddr
                newattr[3] = newattr[3] & ~termios.ICANON
                newattr[3] = newattr[3] & ~termios.ECHO

                termios.tcsetattr(stdin_fd, termios.TCSANOW, newattr)
                oldflags = fcntl(stdin_fd, F_GETFL)
                fcntl(stdin_fd, F_SETFL, oldflags|os.O_NONBLOCK)

                mixer = alsaaudio.Mixer()

                global iloop
                global oloop
                global cframes
                global cvol
                cframelist = ''
                ch = ''

                while iloop:
                    (r, w, er) = select.select([0], [], [])

                    if (r):
                        ch = sys.stdin.read(1)

                    if (ch == 'j'):
                        istop = afile.sample_rate() * 10
                        i = 0

                        lock.acquire()
                        cframes += istop
                        lock.release()

                        while i < istop:
                            cframelist =  pcmr.read(512)

                            if cframelist:
                                i += cframelist.frames
                            else:
                                iloop = 0
                                break

                    elif (ch == 'q'):
                        oloop = 0
                        break

                    elif (ch == 'v'):
                        cvol = 100 if ((cvol + 10) > 100) else (cvol + 10)

                        mixer.setvolume(cvol)
                        pgrs.row.output_line = dtemplate % cvol

                    elif (ch == 'd'):
                        cvol = 0 if ((cvol - 10) < 0) else (cvol - 10)

                        mixer.setvolume(cvol)
                        pgrs.row.output_line = dtemplate % cvol

            except InterruptedError:
                pass

            finally:
                fcntl(stdin_fd, F_SETFL, oldflags)
                oldaddr[3] = oldaddr[3] | termios.ECHO
                termios.tcsetattr(stdin_fd, termios.TCSAFLUSH, oldaddr)
     
        wthrd = threading.Thread(target=thread_callback)
        wthrd.start()

        if afile.supports_metadata():
            msg.info(afile.get_metadata().__unicode__())

        fbuf = ""
        bbuf = ""

        while oloop:
            fbuf = pcmr.read(512)
            bbuf = fbuf.to_bytes(False, True)

            lock.acquire()
            cframes += fbuf.frames
            lock.release()

            if not len(bbuf):
                break

            apcm.write(bbuf)
            pgrs.update(cframes / sframes)

        pcmr.close()
        apcm.close()

    else:
        msg.warning(aerr.ERR_UNSUPPORTED_TO_PCM % {"filename" : sys.argv[1],
                                                   "type" : afile.NAME})

except audiotools.UnsupportedFile:
    msg.warning(aerr.ERR_UNSUPPORTED_FILE % sys.argv[1])
except audiotools.InvalidFile as e:
    msg.warning(e)
except IOError as e:
    msg.warning(e)
except KeyboardInterrupt:
    pcmr.close()
    apcm.close()
finally:
    iloop = 0

    if wthrd and wthrd.is_alive():
        pthread_kill(wthrd.ident, SIGALRM)