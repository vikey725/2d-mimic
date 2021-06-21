import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
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
import pyfakewebcam
from configs.color_config import ColorConfig
from configs.model_config import detector, landmark_predictor
from code.predictor import Predictor
import torch

PUT_TIMEOUT = 1 # s
GET_TIMEOUT = 1 # s
RECV_TIMEOUT = 1000 # ms
QUEUE_SIZE = 1

class PredictorWorker():
    def __init__(self, in_port=None, out_port=None):
        self.recv_queue = mp.Queue(QUEUE_SIZE)
        self.send_queue = mp.Queue(QUEUE_SIZE)

        self.worker_alive = mp.Value('i', 0)

        self.recv_process = mp.Process(target=self.recv_worker, args=(in_port, self.recv_queue, self.worker_alive))
        self.predictor_process = mp.Process(target=self.predictor_worker, args=(self.recv_queue, self.send_queue, self.worker_alive, in_addr, out_addr))
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
                    msg = socket.recv_data()
                    #print("data received")
                except zmq.error.Again:
                    #print("recv timeout")
                    continue

                try:
                    recv_queue.put(msg, block=False)
                except queue.Full:
                    pass
                    #print('recv_queue full')

        except KeyboardInterrupt:
            print("recv_worker: user interrupt")

        worker_alive.value = 0
        print("recv_worker exit")

    @staticmethod
    def predictor_worker(recv_queue, send_queue, worker_alive, in_addr, out_addr):
        BATCH_SIZE = 1
        vis_type = 0
        out_type = 0
        background = "0"
        h = 400
        w = 400

        try:
            background_img = cv2.imread("backgrounds/bg"+str(background)+".jpg")
            background_img = cv2.cvtColor(background_img, cv2.COLOR_BGR2RGB)
            background_img = cv2.resize(background_img, (h,w), interpolation = cv2.INTER_AREA)

            predictor = Predictor(visualizer_type=vis_type, output_type=out_type)
            time.sleep(1)
            print("---------------------------")
            print("python -m scripts.remote_local -in "+in_addr+" -out "+out_addr)
            print("---------------------------")
            while worker_alive.value:

                try:
                    if recv_queue.qsize() >= BATCH_SIZE:
                        infos = []
                        inputs_tensors = []
                        inputs_frames = []
                        info = None
                        for idx in range(BATCH_SIZE):
                            info, frame = recv_queue.get()
                            frame = decode_jpeg(msgpack.unpackb(frame), colorspace = "RGB", fastdct=True)
                            #frame = cv2.imdecode(np.frombuffer(frame, dtype='uint8'), -1)
                            frame = cv2.resize(frame, (h,w))
                            infos.append(info)
                            inputs_tensors.append({
                              "image": torch.as_tensor(frame.astype("float32").transpose(2, 0, 1)),
                              "height": h,
                              "width": w
                            })
                            inputs_frames.append(frame)
                    else:
                        continue
                except queue.Empty:
                    continue

                s = time.time()
                ### Predictor process ##

                if int(info["vis_type"]) != vis_type or int(info["out_type"]) != out_type:
                    vis_type = int(info["vis_type"])
                    out_type = int(info["out_type"])
                    predictor = Predictor(visualizer_type=vis_type, output_type=out_type)
                if info["background"] != background: 
                    background = info["background"]
                    background_img = cv2.imread("backgrounds/bg"+str(info["background"])+".jpg")
                    background_img = cv2.cvtColor(background_img, cv2.COLOR_BGR2RGB)
                    background_img = cv2.resize(background_img, (h,w), interpolation = cv2.INTER_AREA)
                


                frames = predictor.predict_batch(inputs_tensors, inputs_frames, background_img)
                ### ---------------------##
                for idx in range(len(frames)):
                    try:
                      frame = msgpack.packb(encode_jpeg(frames[idx], colorspace = "RGB", fastdct=True))
                      #_,frame = cv2.imencode(".jpg", frames[idx], [int(cv2.IMWRITE_JPEG_QUALITY), 100])
                      info = infos[idx]
                      info["pred_time"] = time.time() - s
                    except:
                      continue
                    try:
                        send_queue.put((info, frame), block=False)
                    except queue.Full:
                        #print("send_queue full")
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
                    msg = send_queue.get(timeout=GET_TIMEOUT)
                except queue.Empty:
                    #print("send queue empty")
                    continue

                socket.send_data(*msg)

        except KeyboardInterrupt:
            print("predictor_worker: user interrupt")

        worker_alive.value = 0
        print("send_worker exit")

if __name__ == '__main__':
    torch.multiprocessing.set_start_method('spawn')
    in_port = 5555
    out_port = 5556
    ngrok.set_auth_token(os.environ['NGROK_AUTH_TOKEN'])
    in_addr = ngrok.connect(in_port, "tcp").public_url
    out_addr = ngrok.connect(out_port, "tcp").public_url
    print("Server is starting .............. wait till you find the python common for local terminal below")
    worker = PredictorWorker(in_port=in_port, out_port=out_port)
    worker.run()
