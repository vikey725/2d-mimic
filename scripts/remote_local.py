from scripts.networking import SerializingContext, check_connection
from scripts.utils import crop

import os
os.environ["KIVY_NO_ARGS"] = "1"
import kivy.core.text
from kivy.app import App
from kivy.base import EventLoop
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.lang import Builder

import signal
import multiprocessing as mp
import queue
import argparse
import cv2
import numpy as np
import zmq
import msgpack
import msgpack_numpy as m
m.patch()
import time
import pyfakewebcam
from simplejpeg import decode_jpeg, encode_jpeg

PUT_TIMEOUT = 0.1 # s
GET_TIMEOUT = 0.1 # s
RECV_TIMEOUT = 1000 # ms
QUEUE_SIZE = 1
default_cam_capture = None

DEFAULT_CAM_ID = 0
qrcam_vis_type = 0
qrcam_out_type = 0
qrcam_background = 0

ALSO_ME_CAM_STATE = False

class OriginalCamera(Image):

    def __init__(self, **kwargs):
        super(OriginalCamera, self).__init__(**kwargs)
        self.capture = None

    def start(self, capture, fps=30):
        self.capture = capture
        Clock.schedule_interval(self.update, 1.0 / fps)

    def stop(self):
        Clock.unschedule_interval(self.update)
        self.capture = None

    def update(self, dt):
        return_value, frame = self.capture.read()
        if return_value:
            texture = self.texture
            w, h = frame.shape[1], frame.shape[0]
            if not texture or texture.width != w or texture.height != h:
                self.texture = texture = Texture.create(size=(w, h))
                texture.flip_vertical()
            texture.blit_buffer(frame.tobytes(), colorfmt='bgr')
            self.canvas.ask_update()


class KivyCamera(Image):

    def __init__(self, **kwargs):
        super(KivyCamera, self).__init__(**kwargs)
        self.capture = None

        global in_addr
        global out_addr

        self.in_addr = in_addr
        self.out_addr = out_addr

        self.vis_type = 0
        self.out_type = 0
        self.background = 0

        self.send_queue = mp.Queue(QUEUE_SIZE)
        self.recv_queue = mp.Queue(QUEUE_SIZE)

        self.worker_alive = mp.Value('i', 0)

        self.new_camera = pyfakewebcam.FakeWebcam('/dev/video7',640,480)

        self.send_process = mp.Process(
            target=self.send_worker,
            args=(self.in_addr, self.send_queue, self.worker_alive),
        )
        self.recv_process = mp.Process(
            target=self.recv_worker,
            args=(self.out_addr, self.recv_queue, self.worker_alive)
        )

        self._i_msg = -1
        #self.sr = cv2.dnn_superres.DnnSuperResImpl_create()
        #self.sr.readModel("checkpoints/ESPCN_x4.pb")
        #self.sr.setModel("espcn",4)



    def start(self, capture, fps=30):
        self.capture = capture
        Clock.schedule_interval(self.update, 1.0 / fps)

        self.worker_alive.value = 1
        self.send_process.start()
        self.recv_process.start()

    def stop(self):
        Clock.unschedule_interval(self.update)
        self.capture = None

    def update(self, dt):

        if self.worker_alive.value == 1:

            _, frame = self.capture.read()

            #size_of_fram = (frame.shape[1], frame.shape[0])
            # size_of_fram = (400, 400)
            # l = size_of_fram[0]
            # w = size_of_fram[1]
            h = 400
            w = 400


            try:
                if ALSO_ME_CAM_STATE is False:
                    # Copy Orignal Fucntion

                    frame = cv2.resize(frame, (640, 480))

                    try:
                        self.new_camera.schedule_frame(frame)
                    except:
                        pass

                    texture = self.texture
                    w, h = frame.shape[1], frame.shape[0]
                    if not texture or texture.width != w or texture.height != h:
                        self.texture = texture = Texture.create(size=(w, h))
                        texture.flip_vertical()
                    texture.blit_buffer(frame.tobytes(), colorfmt='bgr')
                    self.canvas.ask_update()

                    current_fps = 30
                    current_latency = 0

                    App.get_running_app().root.ids.fps.text = f"fps: {current_fps}"
                    App.get_running_app().root.ids.latency.text = f"latency: {current_latency}"



                else:
                    # Perform AlsoMe Fucntion
                    ################

                    frame = cv2.resize(frame, (h, w))
                    assert isinstance(frame, np.ndarray), 'Expected image'
                    frame = msgpack.packb(encode_jpeg(frame, colorspace="RGB"))
                    global qrcam_vis_type
                    global qrcam_out_type
                    global qrcam_background
                    self.vis_type = qrcam_vis_type
                    self.out_type = qrcam_out_type
                    self.background = qrcam_background

                    info = {"vis_type": self.vis_type,
                            "out_type": self.out_type,
                            "background": self.background,
                            "time": time.time()}
                    try:
                        self.send_queue.put((info, frame))

                    except queue.Full:
                        pass
                        #print('send_queue is full')

                    try:
                        info, frame = self.recv_queue.get(timeout=GET_TIMEOUT)
                        frame = decode_jpeg(msgpack.unpackb(frame), colorspace="RGB", fastdct=True)
                        frame = cv2.resize(frame, (640, 480))
                        info["total_time"] = time.time() - info["time"]
                        #print("received frame info", info)
                        try:
                            self.new_camera.schedule_frame(frame)
                        except:
                            pass

                        ## Updating the UI camera view
                        texture = self.texture
                        w, h = frame.shape[1], frame.shape[0]
                        if not texture or texture.width != w or texture.height != h:
                            self.texture = texture = Texture.create(size=(w, h))
                            texture.flip_vertical()
                        texture.blit_buffer(frame.tobytes(), colorfmt='bgr')
                        self.canvas.ask_update()

                        current_fps = 30
                        current_latency =  round(info["total_time"], 2)

                        App.get_running_app().root.ids.fps.text = f"fps: {current_fps}"
                        App.get_running_app().root.ids.latency.text = f"latency: {current_latency}"

                    except queue.Empty:
                        #print('recv_queue is empty')
                        pass


                    ##################

            except KeyboardInterrupt:
                self.mp_stop()
                self.worker_alive.value = 0
                self.stop()
                print("program terminating --------------------------------------")
            except Exception as e:
                raise e



    def mp_stop(self):
        self.worker_alive.value = 0
        #print("join worker processes...")
        self.send_process.join(timeout=5)
        self.recv_process.join(timeout=5)
        self.send_process.terminate()
        self.recv_process.terminate()

    def pack_message(self, msg):
        return (msgpack.packb(msg))

    def unpack_message(self, msg):
        return (msgpack.unpackb(msg))


    @staticmethod
    def send_worker(address, send_queue, worker_alive):

        ctx = SerializingContext()
        sender = ctx.socket(zmq.PUSH)
        sender.connect(address)

        try:
            while worker_alive.value:

                try:
                    msg = send_queue.get(timeout=GET_TIMEOUT)
                    #print("msg sent")
                except queue.Empty:
                    #print('send_queue is empty')
                    continue

                sender.send_data(*msg)

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
                    msg = receiver.recv_data()
                except zmq.error.Again:
                    continue

                try:
                    recv_queue.put(msg, timeout=PUT_TIMEOUT)
                except queue.Full:
                    #print('recv_queue full')
                    continue

        except KeyboardInterrupt:
            print("recv_worker: user interrupt")
        finally:
            worker_alive.value = 0

        receiver.disconnect(address)
        receiver.close()
        ctx.destroy()


def set_vistype_value(spinner, text):
    #print('The spinner  from Binder ', spinner, 'has text', text)
    global qrcam_vis_type
    qrcam_vis_type = text

def set_outtype_value(spinner, text):
    #print('The spinner  from Binder ', spinner, 'has text', text)
    global qrcam_out_type
    qrcam_out_type = text

def set_backimage_value(spinner, text):
    #print('The spinner  from Binder ', spinner, 'has text', text)
    global qrcam_background
    qrcam_background = text


def also_me_switch_callback(instance, value):
    global ALSO_ME_CAM_STATE
    ALSO_ME_CAM_STATE = value

class QrtestHome(BoxLayout):

    def init_qrtest(self):
        self.ids.spinner_outtype.bind(text=set_outtype_value)
        self.ids.spinner_backimage.bind(text=set_backimage_value)

    def dostart(self, *largs):
        global default_cam_capture
        global DEFAULT_CAM_ID

        default_cam_capture = cv2.VideoCapture(DEFAULT_CAM_ID)

        self.ids.qrcam.start(default_cam_capture)
        self.ids.orig_camera.start(default_cam_capture)

        global ALSO_ME_CAM_STATE
        ALSO_ME_CAM_STATE = True
        self.ids.switch.disabled = False
        self.ids.switch.active = ALSO_ME_CAM_STATE

        self.ids.switch.bind(active=also_me_switch_callback)


    def doexit(self):
        global default_cam_capture
        self.ids.qrcam.mp_stop()

        pid = os.getpid()
        os.kill(pid, signal.SIGTERM)

        if default_cam_capture != None:
            default_cam_capture.release()
            default_cam_capture = None

        EventLoop.close()


class AlsoMeApp(App):

    def build(self):
        Window.clearcolor = (.4,.4,.4,1)
        Window.size = (800, 600)
        homeWin = QrtestHome()
        homeWin.init_qrtest()
        return homeWin

    def on_stop(self):
        global default_cam_capture

        if default_cam_capture:
            default_cam_capture.release()

            default_cam_capture = None
            also_me_cam_capture = None

if __name__ == '__main__':

    Builder.load_file('QrtestHome.kv')

    ap = argparse.ArgumentParser()
    ap.add_argument("-in","--in_port", help="tcp://0.tcp.ngrok.io:5555")
    ap.add_argument("-out","--out_port", help="tcp://0.tcp.ngrok.io:5556")
    args = vars(ap.parse_args())
    in_addr = args.get('in_port')
    out_addr = args.get('out_port')

    pid = os.getpid()
    AlsoMeApp().run()