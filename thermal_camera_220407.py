import cmd 
from http import client 

import socket 
import sys 
import struct 
from ctypes import *
from tkinter import Y
from cv2 import LINE_AA 
# from dataclasses import dataclass 
# from matplotlib import markers 
from numpy import size 
import numpy as np
import cv2 


class OZ_header_origin(Structure): 
    marker: str = 'oz00' 
    cmd : int = 6 
    size : int = 0 

class OZ_header(Structure): 
    _fields_ = [("marker", c_char), 
    ("cmd", c_int), 
    ("size", c_int),] 

 
############ Vision data ############# 
HOST='192.168.0.108' 
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
url='rtsp://admin1:1212@192.168.0.108:554/live4.sdp' #id:admin1 pw:1212 #
print('Camera Connected!') 
cap=cv2.VideoCapture(url) 
#cv2.VideoCapture.isOpened() -> retval
print('Video Connected!') 

while True: 
    ret, frame =cap.read() 
    if not ret: # If there is no new frame, Break
        print('no frame')
        break
    # print("ret, frame : ",ret, frame)
    height, width, channels = frame.shape
    print("height, width, channels :",height, width, channels)
    
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
    print("Temp_max = {:.2f}, Y_value = {:.2f}, Image_temp = {:.2f}".format(Temp_max, Dn_value, Image_temp))
    
    frame=cv2.rectangle(frame, (T_max_loc[0]-50,T_max_loc[1]-50),(T_max_loc[0]+50,T_max_loc[1]+50), (0,0,255), 3)
    frame=cv2.putText(frame, 'T={:.2f}degree'.format(Image_temp), T_max_loc, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1, cv2.LINE_4)

            
    cv2.imshow('video', frame) 
    cv2.waitKey(1) 
    
cap.release()   
client_socket.close() 