import argparse

parser = argparse.ArgumentParser(description='give command line arguments')
parser.add_argument('-p', dest='producer', action='store_true',
        help='producer')
parser.add_argument('-c', dest='consumer', action='store_true',
        help='consumer')
parser.add_argument('-f', dest='afile', action='store',
        help='audio file')
parser.add_argument('-l', dest='aplayer', action='store',
        help='audio player')
parser.add_argument('-s', dest='host', action='store',
        help='message queue host')

args = parser.parse_args()

import sys
import puka

if not args.host:
    args.host = 'localhost'

if args.producer:
    if not args.afile:
        print("Audio file not given")
        sys.exit(1)

    producer = puka.Client("amqp://{}/".format(args.host))
    cp = producer.connect()
    producer.wait(cp)

    ep = producer.exchange_declare(exchange='audio', type='fanout')
    producer.wait(ep)

    fp = open(args.afile, 'r')

    while True:
        abuf = fp.read(2048)

        if not abuf:
            break

        mp = producer.basic_publish(exchange='audio', routing_key='', body=abuf)
        producer.wait(mp)

    producer.close()

elif args.consumer:
    if not args.aplayer:
        print("Audio player not provided")
        sys.exit(2)

    import os

    pin, pout = os.pipe()

    if os.fork() == 0:
        os.close(pin)

        consumer = puka.Client("amqp://{}/".format(args.host))
        cp = consumer.connect()
        consumer.wait(cp)

        qp = consumer.queue_declare(exclusive=True)
        qu = consumer.wait(qp)['queue']

        bp = consumer.queue_bind(exchange='audio', queue=qu)
        consumer.wait(bp)

        mp = consumer.basic_consume(queue=qu, no_ack=True)

        while True:
            message = consumer.wait(mp)

            if not message: break

            os.write(pout, message['body'])

        consumer.close()
        os.close(pout)

    else:
        os.close(pout)
        os.close(0)
        os.dup(pin)

        os.system("{} -".format(args.aplayer))
        os.close(pin)