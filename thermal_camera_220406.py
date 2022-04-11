import cmd 
from http import client 
from pydoc import cli 
import socket 
import sys 
import struct 
from ctypes import * 
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


# class OZ_header_receive: 
# marker='' 
# cmd='' 
# size='' 
# def __init__(self, marker, cmd, size): 
# self.marker =marker.decode() 
# self.cmd = cmd.decode() 
# self.size = size.decode()  
# print('marker = {0}, cmd = {1}, size ={2}'.format(marker, cmd, size)) 
# print('marker = {0}, cmd = {1}, size ={2}'.format(self.marker, self.cmd, self.size)) 

# class OZ_header_send: 
# def __init__(self): 
# marker='oz00' 
# cmd=5 
# size=0 
# message=marker+cmd+size 
# return message 

# size = 12 
# buffer = bytearray(size) 
 
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
url='rtsp://admin1:1212@192.168.0.108:554/live4.sdp' #id:admin1 pw:1212 
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
    
    # file = open("Original.txt", "w") 
    # str = repr(frame)
    # file.write("frame = " + str + "\n")
    # file.close()
     
    print("height, width, channels :",height, width, channels)
    dark=frame[150,150,1]
    print('dark = ',dark)
    dark=np.array([[[dark, dark, dark]]], dtype=np.uint8)
    print('dark_array = ',dark)
    dark_yuv = cv2.cvtColor(dark, cv2.COLOR_BGR2YUV) #Y : luma(brightness)
    print('dark_yuv = ',dark_yuv)
    print('dark_y_value = ',dark_yuv[0][0][0])
    
    Dn_max=32249
    Dn_min=29396
    Dn_value=dark_yuv[0][0][0]
    print("Dn_value = ",Dn_value)
    Dn_image=(Dn_value/255)*(Dn_max-Dn_min)+Dn_min
    Image_temp=(Dn_image/100)-273
    
    Dn = 0 # initial value
    for i in range(0,height):
        for j in range(0,width):
            Dn_value=frame[i,j,1]
            Dn +=Dn_value
    Dn=Dn/(height*width)
            
    cv2.imshow('video', frame) 
    cv2.waitKey(1) 
    
cap.release()   
client_socket.close() 