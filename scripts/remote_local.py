from networking import SerializingContext, check_connection

import multiprocessing as mp
import queue
import argparse
import cv2
import numpy as np
import zmq
import msgpack
import msgpack_numpy as m
import pyfakewebcam
import time
m.patch()

from imutils.video import WebcamVideoStream
from simplejpeg import decode_jpeg, encode_jpeg
PUT_TIMEOUT = 0.1 # s
GET_TIMEOUT = 0.1 # s
RECV_TIMEOUT = 1000 # ms
QUEUE_SIZE = 100


class PredictorRemote:
    def __init__(self, in_addr=None, out_addr=None):
        self.in_addr = in_addr
        self.out_addr = out_addr

        self.send_queue = mp.Queue(QUEUE_SIZE)
        self.recv_queue = mp.Queue(QUEUE_SIZE)

        self.worker_alive = mp.Value('i', 0)

        self.send_process = mp.Process(
            target=self.send_worker, 
            args=(self.in_addr, self.send_queue, self.worker_alive),
            )
        self.recv_process = mp.Process(
            target=self.recv_worker, 
            args=(self.out_addr, self.recv_queue, self.worker_alive)
            )

        self._i_msg = -1

    def start(self):
        self.worker_alive.value = 1
        self.send_process.start()
        self.recv_process.start()

        self.startprocess()

    def stop(self):
        self.worker_alive.value = 0
        print("join worker processes...")
        self.send_process.join(timeout=5)
        self.recv_process.join(timeout=5)
        self.send_process.terminate()
        self.recv_process.terminate()

    def pack_message(self, msg):
        return(msgpack.packb(msg))

    def unpack_message(self, msg):
        return(msgpack.unpackb(msg))

    def startprocess(self):
        stream = WebcamVideoStream(src=0).start()
        frame = stream.read()
        size_of_fram = (frame.shape[1], frame.shape[0])
        #size_of_fram = (int(frame.shape[1] / 1), int(frame.shape[0] / 1))
        l = size_of_fram[0]
        w = size_of_fram[1]
        print(l,w)
        camera = pyfakewebcam.FakeWebcam('/dev/video7', l, w) 
        time.sleep(1.0)
        while True:
            try:
                frame = stream.read()
                #frame = cv2.resize(frame, (l, w))
                frame = msgpack.packb(encode_jpeg(frame, colorspace = "RGB", fastdct=True))
                try:
                    self.send_queue.put(frame)
                except queue.Full:
                    print('send_queue is full')

                try:
                    frame = self.recv_queue.get(timeout=GET_TIMEOUT)
                    frame = decode_jpeg(msgpack.unpackb(frame), colorspace = "RGB", fastdct=True)
                except queue.Empty:
                    print('recv_queue is empty')
                    continue

                #frame = cv2.resize(frame, (500, 500))
                cv2.imshow('image',frame)
                cv2.waitKey(1)
                camera.schedule_frame(frame)
                time.sleep(0.2)
            except KeyboardInterrupt:
                self.stop()
                print("program terminating --------------------------------------")
                break


    @staticmethod
    def send_worker(address, send_queue, worker_alive):

        ctx = SerializingContext()
        sender = ctx.socket(zmq.PUSH)
        sender.connect(address)

        try:
            while worker_alive.value:

                try:
                    msg = send_queue.get(timeout=GET_TIMEOUT)
                    print("msg sent")
                except queue.Empty:
                    print('send_queue is empty')
                    continue

                sender.send_data(msg = "image", data = msg)

        except KeyboardInterrupt:
            print("send_worker: user interrupt")
        finally:
            worker_alive.value = 0

        sender.disconnect(address)
        sender.close()
        ctx.destroy()

    @staticmethod
    def recv_worker(address, recv_queue, worker_alive):

        ctx = SerializingContext()
        receiver = ctx.socket(zmq.PULL)
        receiver.connect(address)
        receiver.RCVTIMEO = RECV_TIMEOUT

        try:
            while worker_alive.value:

                try:
                    _,msg = receiver.recv_data()
                except zmq.error.Again:
                    continue
                
                try:
                    recv_queue.put(msg, timeout=PUT_TIMEOUT)
                except queue.Full:
                    print('recv_queue full')
                    continue

        except KeyboardInterrupt:
            print("recv_worker: user interrupt")
        finally:
            worker_alive.value = 0

        receiver.disconnect(address)
        receiver.close()
        ctx.destroy()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--vis-type", type=int, default=0,
                    help="Visualizer type (0, 1, 2, 3")

    ap.add_argument("-o", "--out-type", type=int, default=0,
                    help="Visualizer type (0, 1")

    ap.add_argument("-bg", "--background-image", type=int, default=1,
                    help="Background image no.")

    ap.add_argument("-in","--in_port", help="tcp://0.tcp.ngrok.io:5555")

    ap.add_argument("-out","--out_port", help="tcp://0.tcp.ngrok.io:5556")

    args = vars(ap.parse_args())

    p = PredictorRemote(in_addr=args.get('in_port'), out_addr=args.get('out_port')) 
    p.start()
