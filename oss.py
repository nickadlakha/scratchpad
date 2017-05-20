import os
import sys

oss_device = 0

def setup():
    global oss_device
    fh = os.popen('lsmod', mode='r')

    for line in fh:
        if 'snd_pcm_oss' in line:
            oss_device = 1
            break

    fh.close()

    if oss_device == 0:
        print('no oss device loaded, kindly load snd_pcm_oss kernel module', file=sys.stderr)
        sys.exit(1)

    if os.path.exists('/dev/dsp'):
        oss_device = '/dev/dsp'
    elif os.path.exists('/dev/audio'):
        oss_device = '/dev/audio'

    if sys.argv.__len__() < 2:
        print('usage: python3 %s raw_audio_file [audio_frequency]' % sys.argv[0])
        sys.exit(2)

    play_audio()

def play_audio():
    global oss_device
    AFMT_S16_NE = 0x00000010 if sys.byteorder == 'little' else 0x00000020
    SNDCTL_DSP_CHANNELS = 3221508102
    SNDCTL_DSP_SPEED = 3221508098
    SNDCTL_DSP_SYNC = 20481
    SNDCTL_DSP_SETFMT = 3221508101

    import fcntl
    import struct

    try:
        audio_file_fd = os.open(sys.argv[1], os.O_RDONLY) if sys.argv[1] != '-' else 0
        frequency = int(sys.argv[2]) if sys.argv.__len__() == 3 else 44100
        iofd = os.open(oss_device, os.O_WRONLY)

        tmp = struct.pack('i', AFMT_S16_NE)

        fcntl.ioctl(iofd, SNDCTL_DSP_SETFMT, tmp)

        if struct.unpack('i', tmp)[0] != AFMT_S16_NE:
            print('couldnot set the format', file=sys.stderr)
            sys.exit(3)

        " Stereo - 2, mono - 1"
        tmp = struct.pack('i', 2)

        fcntl.ioctl(iofd, SNDCTL_DSP_CHANNELS, tmp)

        tmp = struct.pack('i', frequency)

        fcntl.ioctl(iofd, SNDCTL_DSP_SPEED, tmp)
        print('speed set to ', struct.unpack('i', tmp)[0], ' HZ')

        len_buf = (5 * frequency * 2 * AFMT_S16_NE) // 8

        while True:
            buf = os.read(audio_file_fd, len_buf)

            if buf:
                os.write(iofd, buf)
            else:
                break

    except Exception as e:
        print(e, file=sys.stderr)
    finally:
        if audio_file_fd:
            os.close(audio_file_fd)
        if iofd:
            os.close(iofd)

if __name__ == '__main__':
    setup()