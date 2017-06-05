# nnet - tcp stealth scanning, client, server
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

from socket import socket, AF_INET, SOCK_RAW, AF_PACKET, SOCK_STREAM, htons, \
    IPPROTO_TCP, getaddrinfo, gethostbyname, inet_pton, SOL_SOCKET,\
    SO_KEEPALIVE, SHUT_WR, SO_REUSEADDR
import sys
import argparse
from signal import signal, SIGALRM, alarm, SIGUSR1

parser = argparse.ArgumentParser(description='give command line arguments')
parser.add_argument('-s', dest='stealth', action='store_true',
        help='stealth scanning')
parser.add_argument('-w', '--wait',metavar='Wait', dest='wait', action='store',
        help='wait for -w minutes before giving up')
parser.add_argument('-l', dest='listen', action='store_true', help='Server Mode')
parser.add_argument('-ip', '--ipaddress',metavar='ip address', dest='ip',
        action='store', required=True, help='ip address or hostname to query')
parser.add_argument('-p', '--port',metavar='Port', dest='port', action='store',
        required=True, help='Port to Query')

args = parser.parse_args()

ip = getaddrinfo(host=args.ip, port=0, family=AF_INET)
ip = ip[0][-1][0]
sock = 0
twait = int(args.wait) if args.wait else 2

def signal_handler(signum, frame):
    pass

signal(SIGALRM, signal_handler)

try:
    if args.stealth:
        ISEQ = 2025
        LPORT = 3000
        IWSIZE = 4096

        def psuedo_tcp_header(psh, blen, srcip, dstip):
            psh[10:12] = int(blen).to_bytes(2, byteorder='big', signed=False)
            psh[:4] = srcip
            psh[4:8] = dstip
            psh[9] = IPPROTO_TCP

        def calculate_checksum(buf):
            csum = 0
            i = 0
            blen = len(buf)

            while i < blen:
                csum += int.from_bytes(buf[i: (i + 2)], byteorder='big',
                                       signed=False)
                i += 2

            csum = (csum >> 16) + (csum & 0xFFFF)
            csum += (csum >> 16)
            return ~csum & 0xFFFF

        alarm(twait * 60)


        sock = socket(AF_INET, SOCK_RAW, IPPROTO_TCP)
        buf = bytearray(64) ## dword boundry
        buf[0:2] = int(LPORT).to_bytes(2, byteorder='big', signed=False)
        buf[2:4] = int(args.port).to_bytes(2, byteorder='big', signed=False)
        buf[4:8] = int(ISEQ).to_bytes(4, byteorder='big', signed=False)
        buf[12] = 0x70 ## header len multiples of dword
        buf[13] = 0x02 ## syn

        sock.connect((ip, 0))

        dipaddr = inet_pton(AF_INET, ip)
        sipaddr = inet_pton(AF_INET, sock.getsockname()[0])

        psh = bytearray(12)
        psuedo_tcp_header(psh, 28, sipaddr, dipaddr)

        ## window size
        buf[14:16] = int(IWSIZE).to_bytes(2, byteorder='big', signed=False)

        buf[16:18] = calculate_checksum(psh + buf[:28]).to_bytes(2, byteorder='big',
                                                                 signed=False)
        sock.send(buf[:28])

        ### receive the packet ###
        zn, iinfo = sock.recvfrom_into(buf, buf.__len__(), 0)
        offset = (buf[0] & 0x0F) << 2

        ## checksum verification ########
        psuedo_tcp_header(psh, ((buf[offset + 12] & 0xF0) >> 4) << 2, dipaddr,
                          sipaddr)
        csum = int.from_bytes(buf[offset + 16 : offset + 18], byteorder='big',
                              signed=False)
        buf[offset + 16] = 0x00
        buf[offset + 17] = 0x00

        if csum != calculate_checksum(psh + buf[offset:zn]):
            print("Checksum invalid", file=sys.stderr)
            sys.exit(1)

        flags = buf[offset + 13]

        if ((flags >> 4) == 1) and  (int.from_bytes(buf[offset + 8:
                offset + 12], byteorder='big', signed=False) == (ISEQ + 1)):
            if (flags & 0x0F) == 2:
                print("Port recahable")
            elif (flags & 0x0F) == 4:
                print("Port unreachable")

    elif args.listen:
        sock = socket(AF_INET, SOCK_STREAM, 0)
        sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind((ip, int(args.port)))
        sock.listen(5)

        from os import fork, read, write, wait, kill

        csock, null = sock.accept()

        child = fork()

        if child == 0:
            def catch_me(signum, frame):
                csock.close()
                sys.exit(1)


            signal(SIGUSR1, catch_me)

            while True:
                cbuf = read(0, 2048)

                if not cbuf:
                    csock.shutdown(SHUT_WR)
                    break

                csock.sendall(cbuf)

        else:
            while True:
                pbuf = csock.recv(2048)

                if not pbuf:
                    kill(child, SIGUSR1)
                    break

                write(1, pbuf)

            wait()
            csock.close()

    else:
        sock = socket(AF_INET, SOCK_STREAM, 0)
        sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        sock.connect((ip, int(args.port)))

        from os import fork, read, write, wait, kill

        child = fork()

        if child == 0:
            def catch_me(signum, frame):
                sys.exit(1)

            signal(SIGUSR1, catch_me)

            while True:
                cbuf = read(0, 2048)

                if not cbuf:
                    sock.shutdown(SHUT_WR)
                    break

                sock.sendall(cbuf)

        else:

            while True:
                pbuf = sock.recv(2048)

                if not pbuf:
                    kill(child, SIGUSR1)
                    break

                write(1, pbuf)

            wait()

except InterruptedError:
    print(ip + ' not reachable', file=sys.stderr)
except Exception as e:
    print(e)
finally:
    if sock: sock.close()