from scripts.networking import SerializingContext, check_connection
import cv2
import numpy as np
import zmq
import msgpack
import msgpack_numpy as m
m.patch()
from simplejpeg import decode_jpeg, encode_jpeg
from pyngrok import ngrok
import queue
import multiprocessing as mp
import traceback
import time
import argparse
import pyfakewebcam
from configs.color_config import ColorConfig
from configs.model_config import detector, landmark_predictor
from code.predictor import Predictor
import torch

PUT_TIMEOUT = 1 # s
GET_TIMEOUT = 1 # s
RECV_TIMEOUT = 1000 # ms
QUEUE_SIZE = 100



class PredictorWorker():
    def __init__(self, in_port=None, out_port=None, background = None, predictor = None):
        self.recv_queue = mp.Queue(QUEUE_SIZE)
        self.send_queue = mp.Queue(QUEUE_SIZE)

        self.worker_alive = mp.Value('i', 0)

        self.recv_process = mp.Process(target=self.recv_worker, args=(in_port, self.recv_queue, self.worker_alive))
        self.predictor_process = mp.Process(target=self.predictor_worker, args=(self.recv_queue, self.send_queue, self.worker_alive, background, predictor))
        self.send_process = mp.Process(target=self.send_worker, args=(out_port, self.send_queue, self.worker_alive))
    
    def run(self):
        self.worker_alive.value = 1

        self.recv_process.start()
        self.predictor_process.start()
        self.send_process.start()

        try:
            self.recv_process.join()
            self.predictor_process.join()
            self.send_process.join()
        except KeyboardInterrupt:
            pass

    @staticmethod
    def recv_worker(port, recv_queue, worker_alive):

        ctx = SerializingContext()
        socket = ctx.socket(zmq.PULL)
        socket.bind(f"tcp://*:{port}")
        socket.RCVTIMEO = RECV_TIMEOUT


        try:
            while worker_alive.value:

                try:
                    _,frame = socket.recv_data()
                except zmq.error.Again:
                    print("recv timeout")
                    continue

                try:
                    recv_queue.put(frame)
                except queue.Full:
                    print('recv_queue full')

        except KeyboardInterrupt:
            print("recv_worker: user interrupt")

        worker_alive.value = 0
        print("recv_worker exit")

    @staticmethod
    def predictor_worker(recv_queue, send_queue, worker_alive, background, predictor):
        
        try:
            while worker_alive.value:

                try:
                    frame = recv_queue.get(timeout=GET_TIMEOUT)
                except queue.Empty:
                    continue

                frame = decode_jpeg(msgpack.unpackb(frame), colorspace = "RGB", fastdct=True)
                
                ### Predictor process ##
                background_img = cv2.resize(background, (frame.shape[1], frame.shape[0]), interpolation = cv2.INTER_AREA)
                frame = predictor.dp_predict(frame, background_img)
                ### ---------------------##

                frame = msgpack.packb(encode_jpeg(frame, colorspace = "RGB", fastdct=True))
                try:
                    send_queue.put(frame)
                except queue.Full:
                    print("send_queue full")
                    pass

        except KeyboardInterrupt:
            print("predictor_worker: user interrupt")
        except Exception as e:
            print("predictor_worker error")
            traceback.print_exc()
    
        worker_alive.value = 0
        print("predictor_worker exit")

    @staticmethod
    def send_worker(port, send_queue, worker_alive):

        ctx = SerializingContext()
        socket = ctx.socket(zmq.PUSH)
        socket.bind(f"tcp://*:{port}")

        try:
            while worker_alive.value:

                try:
                    frame = send_queue.get(timeout=GET_TIMEOUT)
                except queue.Empty:
                    print("send queue empty")
                    continue

                socket.send_data(msg = "image", data = frame)

        except KeyboardInterrupt:
            print("predictor_worker: user interrupt")

        worker_alive.value = 0
        print("send_worker exit")

if __name__ == '__main__':
    torch.multiprocessing.set_start_method('spawn')
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--vis-type", type=int, default=0,
                    help="Visualizer type (0, 1, 2, 3")

    ap.add_argument("-o", "--out-type", type=int, default=0,
                    help="Visualizer type (0, 1")
    args = vars(ap.parse_args())
    vis_type = args.get('vis_type', None)
    out_type = args.get('out_type', None)
    in_port = 5555
    out_port = 5556
    ngrok.set_auth_token("1t4SKLGLQrQWbMnhgqeLMDoZWO5_81uYnSFsT87KsBm4A6zGZ")
    in_addr = ngrok.connect(in_port, "tcp").public_url
    out_addr = ngrok.connect(out_port, "tcp").public_url
    print("---------------------------")
    print("python client.py -in "+in_addr+" -out "+out_addr)
    print("---------------------------")
    background_img = cv2.imread(f"backgrounds/bg1.jpg")
    background_img = cv2.cvtColor(background_img, cv2.COLOR_BGR2RGB)
    dp_predictor = Predictor(visualizer_type=vis_type, output_type=out_type)
    worker = PredictorWorker(in_port=in_port, out_port=out_port,
        background = background_img, predictor = dp_predictor)
    worker.run()