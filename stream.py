#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan  20 02:07:13 2019
@author: prabhakar
"""
# import necessary argumnets 
import gi
import cv2
import argparse

# Themal camera arguments
import cmd 
from http import client 

import socket 
import sys 
import struct 
from ctypes import *
from cv2 import LINE_AA 
from numpy import size 
import numpy as np

# import required library like Gstreamer and GstreamerRtspServer
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

# Themal camera class
class OZ_header_origin(Structure): 
    marker: str = 'oz00' 
    cmd : int = 6 
    size : int = 0 

class OZ_header(Structure): 
    _fields_ = [("marker", c_char), 
    ("cmd", c_int), 
    ("size", c_int),] 

############ Vision data ############# 
HOST='192.168.10.108' 
PORT=1030 #9090 TCP:1030 RSTP: 1056 

client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
client_socket.connect((HOST,PORT)) 

data=client_socket.recv(1024) 
info=struct.unpack('ccccii',data) 
print('Unpacked data[header] : ', info) 
print('info[5] : ',info[5]) 

data=client_socket.recv(info[5]) 
print('Unpacked data[data] : ', data) 
print('type : ', type(data)) 

############ Vision data transfer ############# 
PORT=554 #9090 TCP:1030 RSTP: 1056 
client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
client_socket.connect((HOST,PORT)) 
url='rtsp://admin:qwe1010@192.168.10.108:554/live4.sdp' #id:admin pw:1212 #
print('Camera Connected!') 
# cap=cv2.VideoCapture(url) 
#cv2.VideoCapture.isOpened() -> retval
print('Video Connected!') 


# Sensor Factory class which inherits the GstRtspServer base class and add
# properties to it.
class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, **properties):
        super(SensorFactory, self).__init__(**properties)
        PORT=554 #9090 TCP:1030 RSTP: 1056 
        client_socket=socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        client_socket.connect((HOST,PORT)) 
        url='rtsp://admin:qwe1010@192.168.10.108:554/live4.sdp' #id:admin pw:1212 #
        print('Camera Connected!') 
        # self.cap = cv2.VideoCapture(opt.device_id)
        self.cap = cv2.VideoCapture(url)
        print('Video Connected!') 
        self.number_frames = 0
        self.fps = opt.fps
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        self.launch_string = 'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME ' \
                             'caps=video/x-raw,format=BGR,width={},height={},framerate={}/1 ' \
                             '! videoconvert ! video/x-raw,format=I420 ' \
                             '! x264enc speed-preset=ultrafast tune=zerolatency bitrate=2048 ' \
                             '! rtph264pay config-interval=1 name=pay0 pt=96' \
                             .format(opt.image_width, opt.image_height, self.fps)
    # method to capture the video feed from the camera and push it to the
    # streaming buffer.
    def on_need_data(self, src, length):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # It is better to change the resolution of the camera 
                # instead of changing the image shape as it affects the image quality.
                # processing Thermal camera
                height, width, channels = frame.shape
                Dn_max=32231
                Dn_min=29086
                for i in range(0,height,2):
                    for j in range(0,width,2):
                        if i==0 and j==0:
                            Temp_avg=Temp_min=Temp_max=Dn_value=frame[i,j,1]
                        else:
                            Dn_value=frame[i,j,1]
                            if Dn_value < Temp_min:
                                Temp_min=Dn_value
                                T_min_loc=(j,i)
                            if Dn_value > Temp_max:
                                Temp_max=Dn_value
                                T_max_loc=(j,i)
                            Temp_avg +=Dn_value
                Temp_avg=Temp_avg/(height*width)
                dark=Temp_max
                dark=np.array([[[dark, dark, dark]]], dtype=np.uint8)
                dark_yuv = cv2.cvtColor(dark, cv2.COLOR_BGR2YUV) #Y : luma(brightness)
                Dn_value=dark_yuv[0][0][0]
                Dn_image=(Dn_value/255)*(Dn_max-Dn_min)+Dn_min
                Image_temp=(Dn_image/100)-273
                # frame=cv2.rectangle(frame, (T_max_loc[0]-50,T_max_loc[1]-50),(T_max_loc[0]+50,T_max_loc[1]+50), (0,0,255), 3)
                frame=cv2.putText(frame, 'T={:.2f}degree'.format(Image_temp), T_max_loc, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1, cv2.LINE_4)
                
                # frame resize
                frame = cv2.resize(frame, (opt.image_width, opt.image_height), \
                    interpolation = cv2.INTER_LINEAR)
                data = frame.tostring()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)
                buf.duration = self.duration
                timestamp = self.number_frames * self.duration
                buf.pts = buf.dts = int(timestamp)
                buf.offset = timestamp
                self.number_frames += 1
                retval = src.emit('push-buffer', buf)
                print('pushed buffer, frame {}, duration {} ns, durations {} s'.format(self.number_frames,
                                                                                       self.duration,
                                                                                       self.duration / Gst.SECOND))
                if retval != Gst.FlowReturn.OK:
                    print(retval)
    # attach the launch string to the override method
    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)
    
    # attaching the source element to the rtsp media
    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)

# Rtsp server implementation where we attach the factory sensor with the stream uri
class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, **properties):
        super(GstServer, self).__init__(**properties)
        self.factory = SensorFactory()
        self.factory.set_shared(True)
        self.set_service(str(opt.port))
        self.get_mount_points().add_factory(opt.stream_uri, self.factory)
        self.attach(None)

# getting the required information from the user 
parser = argparse.ArgumentParser()
parser.add_argument("--device_id", required=True, help="device id for the \
                video device or video file location")
parser.add_argument("--fps", required=True, help="fps of the camera", type = int)
parser.add_argument("--image_width", required=True, help="video frame width", type = int)
parser.add_argument("--image_height", required=True, help="video frame height", type = int)
parser.add_argument("--port", default=8554, help="port to stream video", type = int)
parser.add_argument("--stream_uri", default = "/video_stream", help="rtsp video stream uri")
opt = parser.parse_args()

try:
    opt.device_id = int(opt.device_id)
except ValueError:
    pass

# initializing the threads and running the stream on loop.
GObject.threads_init()
Gst.init(None)
server = GstServer()
loop = GObject.MainLoop()
loop.run()
