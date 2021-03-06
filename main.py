"""
CONTRIBUTORS:
    Paul Durham, Mitchell Perez, Omnia Awad, Allison Dorsett, Ben Jinkerson, Joseph Proctor
FILE CONTENT DESCRIPTION:
	The file main.py leverages functionality from the various components of SLISH in order to produce a working, efficient 
	software. The user interface design and functionalities are implemented utilizing the tkinter library for its development.
	As previously mentioned, the methods from every component of SLISH are used logically in order for SLISH to act accordingly
	based on the recevied input. 
	
	Specific methods and logic leveraged from the camera component in this file include the system 
	"cool down" period and retrieving the external input for use by the rest of the system.
	
	The classifier comoponent's methods are used frequently throughout the latter contents of this file.
    Based on the classifications made by the classifier component, logic in main.py determines whether enough
	frames have been classified to make an accurate gesture prediction and, if so, whether to execute a command 
	based on the received input. Specifically, this ensures that at least 6 frames were analyzed before a prediction
	is made, ensures that commands are only recognized in a format valid to SLISH (letter -> number) and handles
	invalid or unrecognized input without affecting system performance. 
	Last, methods from the socket class are utilized to control the web sockets that correspond to the command received.
	The actions that are executed are clearly displayed within the contents of the user interface. 
REQUIREMENTS ADDRESSED:
    FR.2, FR.2.1, FR 2.1.1, FR.2.1.2, FR.2.1.3, FR2.2, FR.2.3,
	NFR.2, NFR.4, NFR.5, NFR.6, NFR.7, NFR.8, NFR.9
	EIR.1, EIR.2

CORRESPONDING SDD SECTIONS: 
GUI (Lines 79-249 and 403-405 in code) - Sections: 4.0, 4.1, 4.1.1, 4.1.2, 4.2, 4.3
Camera Frame Retrieval Component methods that are being leveraged in main.py (lines 252-306 and 394-400) - Sections: 3.2.A - 3.2.3.5.2.A
Classifier Component methods that are being leveraged in main.py (lines 313-345) = Sections: 3.2.1.C - 3.2.3.5.2.C
Plug Component methods that are being leveraged in main.py (lines 349-387) - Sections : 3.2.1.D - 3.2.3.5.2.D
Timer functions used for efficiency/unit testing (lines 409-421) - Section: 2.1

LICENSE INFORMATION:
    Copyright (c) 2019, CSC 450 Group 1
    All rights reserved.
    Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
    following conditions are met:
        * Redistributions of source code must retain the above copyright notice, this list of conditions and the
          following disclaimer.
        * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
          the following disclaimer in the documentation and/or other materials provided with the distribution.
        * Neither the name of the CSC 450 Group 1 nor the names of its contributors may be used to endorse or
          promote products derived from this software without specific prior written permission.
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
    STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
    EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
import time
import webbrowser
import cv2
import numpy as np
import traceback
import tkinter as tkinter
# from status_log import *
import keyboard
import pathlib
from sys import platform
from tkinter import filedialog
import sys
from tkinter import *
from multiprocessing import Process
from tkinter import *
from PIL import Image, ImageTk#from PIL import ImageTk
from threading import Thread
import time
import PIL.Image, PIL.ImageTk
from collections import deque, Counter  
try:
    from tkinter import ttk   
except ImportError:
    from tkinter import ttk
import time
from datetime import datetime
from my_sock.sock import Socket
from model_handler.classifier import Classifier
from camera_stream.camera import Camera
from camera_stream.motion_detection import Frame_Comparison


class Slish:
    def __init__(self):
	## Create tkinter window object
        self.log_info("Program started at: {0} ".format(datetime.now()))
        
        ## Creating a TKINTER window
        self.window = tkinter.Tk()
        
        ## Changing the shape of the window
        self.window.geometry("1000x700")
        self.window.title("Slish")
        self.window.config(background='#c9e4ff')

        ## Creating camera object
        self.vid = Camera()
        self.success, self.background_image,_ = self.vid.capture_image()
        self.background_image = cv2.cvtColor(self.background_image, cv2.COLOR_BGR2GRAY)

	## Creating a classifier object
        self.classifier = Classifier()

        ## Creating a motion detection object
        self.checkformotion = Frame_Comparison()
        
        ## Creating variables used to keep track of predictions
        self.last_pred = None;
        self.recent_img = False
        self.pred_queue = deque([])
        self.sequence_of_gestures = [None,None]
        self.sequence_of_gestures_backup = [None,None]
        self.pred_queue_last_gesture = None
        self.recognized_sequence = False
        self.camera_status = self.vid.logStatus(True)
        self.get_background_bool = True
        self.last_time = 0
        
        ## Variables for timing the functions
        self.timing_list = set()
        self.time = {}

        ## Create mappings for plugs
        self.socket = Socket()
	    # Create tkinter Frame and widgets
        self.header_frame= tkinter.Frame(self.window, bg='#c9e4ff')
        self.header_frame.pack(fill='x')
        self.middle_frame= tkinter.Frame(self.window)
        self.middle_frame.pack()
        self.stream_display= tkinter.Frame(self.middle_frame)
        self.stream_display.pack(fill='both')
        self.text_display= tkinter.Frame(self.middle_frame)
        self.text_display.pack(fill='both')
        self.btn =ttk.Button(self.header_frame, text='HELP', command=self.open_help)
        self.btn.pack(padx=10, pady=10, side='bottom')

        ## Create tkinter log/logo
        self.log_frame= tkinter.Frame(self.window, padx=5, pady=5, borderwidth=2, bg='#c9e4ff')
        self.log_frame.pack(side='bottom', fill='both')
        self.logBtn_frame=tkinter.Frame(self.log_frame,padx=5,pady=5,borderwidth=2, bg='#c9e4ff')
        self.logBtn_frame.pack(side='top', fill='y')
        self.btn2 =ttk.Button(self.logBtn_frame, text='Clear Log', command = self.clear_log)
        self.btn2.grid(row=0,column=0,padx=2, pady=2)
        self.btn3 =ttk.Button(self.logBtn_frame, text = 'Save Log', command = self.save) 
        self.btn3.grid(row=0,column=1, pady = 2, padx = 2)
        self.btn4 =ttk.Button(self.logBtn_frame, text='Update Log', command = self.update_log)
        self.btn4.grid(row=0,column=2,padx=2, pady=2)
        self.log=tkinter.Text(self.log_frame)
        self.S = tkinter.Scrollbar(self.log_frame)
        self.S.config(command=self.log.yview)
        self.S.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        self.log.config(yscrollcommand=self.S.set)
        self.logo = ImageTk.PhotoImage(Image.open('pic.png'))
        self.label = tkinter.Label(self.header_frame, image=self.logo)
        self.label.image= self.logo
        self.label.pack(padx=5, pady=5)
        
        self.fps_text_label = tkinter.Label(self.text_display,text="FPS ->", padx=10, pady=10, bg='#c9e4ff')
        self.fps_text_label.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        self.fps_text = tkinter.Label(self.text_display,text="None", padx=10, pady=10)
        self.fps_text.grid(row=0, column=1, padx=1, pady=1)
        
        self.last_gesture_label = tkinter.Label(self.text_display,text="Gesture ->", padx=10, pady=10, bg='#c9e4ff')
        self.last_gesture_label.grid(row=0, column=2, padx=10, pady=10,sticky='nsew')
        self.last_gesture = tkinter.Label(self.text_display,text="None", padx=10, pady=10)
        self.last_gesture.grid(row=0, column=3, padx=1, pady=1)

        self.last_sequence_of_gestures_label = tkinter.Label(self.text_display, text="Sequence of Gestures ->", padx=10, pady=10, bg='#c9e4ff')
        self.last_sequence_of_gestures_label.grid(row=1, column=0, padx=10, pady=10,sticky='nsew')
        self.last_sequence_of_gestures = tkinter.Label(self.text_display, text="None", padx=10, pady=10)
        self.last_sequence_of_gestures.grid(row=1, column=1, padx=1, pady=1)

        self.last_command_label = tkinter.Label(self.text_display,text="Command ->", padx=10, pady=10, bg='#c9e4ff')
        self.last_command_label.grid(row=1, column=2, padx=10, pady=10,sticky='nsew')
        self.last_command = tkinter.Label(self.text_display, text="None", padx=10, pady=10)
        self.last_command.grid(row=1, column=3, padx=1, pady=1)

        ## Creating text output fields
        self.display_image_bool = tkinter.IntVar()
        self.display_image = tkinter.Checkbutton(self.stream_display, text="Display Camera Feed",variable=self.display_image_bool, padx=10, pady=10, bg='#568c96')
        self.display_image.grid(row=0, column=0, padx=10, pady=10)
        self.display_classified_image_bool = tkinter.IntVar()
        self.display_classified_image = tkinter.Checkbutton(self.stream_display, text="Display Classified Feed",variable=self.display_classified_image_bool, padx=10, pady=10, bg='#568c96')
        self.display_classified_image.grid(row=0, column=1, padx=10, pady=10)
        self.stream_display.grid_columnconfigure(0, weight=1)
        self.stream_display.grid_columnconfigure(1, weight=1)
        self.sequence_of_gestures_backup = []        

        ## Updating the log with entries
        self.displayProgramAction(self.camera_status)
        self.displayProgramAction(self.camera_status)
        self.window.protocol("WM_DELETE_WINDOW", self.displayProgramClosing)
        self.recently_executed = False
        self.start_time = time.time()

        ## Begin main loop
        self.ten_sec_window = 0
        self.delay = 5
        self.update()
        self.window.mainloop()

    ## Function to open help document on github    
    def open_help(self): 
        webbrowser.open('https://github.com/mjp1997/ASL-Controlled-Smart-Home-Environment/blob/master/help.txt')
        # button that calls open_help()

    ## Clears the log history
    def clear_log(self):
        f = open('logHistory.txt', 'r+')
        f.truncate(0)
        current_time = datetime.now()
        self.log.delete("1.0", "end")
        file = open('logHistory.txt', 'a')
        file.write("log has been cleared at: {0} ".format(current_time) + '\n')

    ## Saves the logHistory as a copy
    def save(self):
        with open("logHistory.txt", "r") as logfile:
            savefile = filedialog.asksaveasfile(mode='w', defaultextension = ".txt")
            savefile.write(logfile.read())
            savefile.close()

    ## Updates the log
    def update_log(self):
        with open('logHistory.txt','r') as f:
            data = f.read()
            self.log.delete('1.0', 'end')# Remove previous content 
            for x in data:
                self.log.insert(tkinter.INSERT, x)#Insert text from file

    ## Reads the log history from the text file named logHistory.txt
    def displayProgramAction(self, cam_is_open):
        if cam_is_open:
            with open('logHistory.txt','r') as file_data:
                history = list(file_data)
                for x in history:
                    self.log.insert(tkinter.INSERT, x)
                self.log.config(width=640)
                self.log.pack(fill='x')
        else:
            self.log.insert(tkinter.INSERT, "{0}".format(history))

    ## Writes log history to the log widget
    def displayProgramClosing(self):
        current_time = datetime.now()
        file = open('logHistory.txt', 'a')
        file.write("program closed at: {0} ".format(current_time) + '\n')
        file.write('=========================================\n')
        file.close()
        self.log.insert(tkinter.INSERT, "program closed at: {0} ".format(current_time))
        self.log.insert(tkinter.INSERT, "=========================================\n'")
        self.window.destroy()

    #The update function that is called each iteration
    def update(self):
        #Success means that a valid image came back as the image will be an array and will not equal None
        success, frame, no_background = self.vid.capture_image()
        self.modif_frame = self.checkformotion.processCurrentFrame(frame)
        self.frame_difference = self.checkformotion.subtractFrames(self.modif_frame, self.background_image)
        
        #SLISH waits 3 seconds before classifying gestures, thus giving the background remover time to settle.
        if self.get_background_bool == True:
            current_time = int(time.time() - self.start_time)
            if current_time > 3:
                self.get_background_bool = False
                print("Background acquired...")
            else:
                if current_time != self.last_time:
                    self.last_time = current_time
                    print(str(current_time)+" seconds out 20 5 seconds")
                
                self.window.after(self.delay, self.update)

        if not self.get_background_bool:
	        # Quantify the number of pixels that have changed
            changedPixels = self.checkformotion.checkPixelDiff(self.frame_difference)
        
	        # Quanity the total number of pixels
            totalPixels = self.checkformotion.getNumPixels(self.background_image)

            # Wasn't enough movement
            if changedPixels/totalPixels < .10:
                self.window.after(self.delay, self.update)
            #Program will continue past this section if the threshold is met        

            # If there has been a recent classified image and doesnt need to run (COOL DOWN PERIOD)
            if self.recent_image():
                self.window.after(self.delay, self.update)

           #If the cool down period is not active, classify the frame for a gesture....
            else:
                ## Classify the frame from the camera
                pred = self.classifier.classify(no_background)

                #We process the prediction queue
                self.processPred(pred)

            ## Display images if needed based on checkbuttons
                if self.display_image_bool.get() == 1:
                    cv2.imshow("Camera Image",frame)
                if self.display_classified_image_bool.get() == 1:
                    cv2.imshow("Classified Image",no_background)

            ## Update text fields
                self.fps_text.config(text=self.vid.getFPS())
                self.last_sequence_of_gestures.config(text=str(self.sequence_of_gestures_backup[0])+" : "+str(self.sequence_of_gestures_backup[1]))
                self.last_gesture.config(text=self.pred_queue_last_gesture)

                self.window.after(self.delay, self.update)

            
    
    ## This method takes a prediction and pushes it to the queue
    def processPred(self,pred):
        ## If the queue is 6 then its full
        if len(self.pred_queue) == 6:
            print(self.pred_queue)
            ## res is the highest percentage item in the queue and the if statement will run if that percentage is over .6
            res = Counter(self.pred_queue).most_common(1)

            ## If res percentage is .6 and it is not None
            if res[0][1]/6 > .66 and res[0][0] != None:
                self.pred_queue_last_gesture = res[0][0]
                ## This will push the gesture to the gesture list as a gesture has been recognized
                self.processQueue(res[0][0])
                
            ## The most common item in the pred queue is None clear and reset the queue variables
            elif res[0][0] == None:
                self.last_pred = None;
                self.pred_queue = deque([])
                #only clear gesture queue if the user's been given 10 secs to provide a valid gesture
                if len(self.sequence_of_gestures) > 0 and time.time() - self.ten_sec_window > 10: 					
                    self.sequence_of_gestures = []
                    self.recognized_sequence = False
					
                
            ## The gesture isnt recognized so we pop and push a new prediction
            else:
                self.pred_queue.popleft()
                self.pred_queue.append(pred)
                
        ## The queue isnt full so we push the prediction
        else:
            self.pred_queue.append(pred)
            if len(self.sequence_of_gestures_backup) == 0:
                self.sequence_of_gestures_backup = [None,None]
            
    # receives prediction (label) regarding the 6 predictions in the queue
    def processQueue(self, label):
        ## reset the aforementioned 6 gesture queue
        self.pred_queue *= 0 
        self.last_pred = label

        #valid commands = Letter 1st, Number 2nd, following logic assures this
        if self.last_pred.isalpha() and len(self.sequence_of_gestures) == 0: #assures 1st gesture is alphabetic
            self.sequence_of_gestures.append(label)
            self.ten_sec_window = time.time()
            self.recently_executed = True
            self.cmd_execution_time = time.time() 
            print(self.sequence_of_gestures)
        #if it's the 2nd gesture and the gesture is numeric, process the gesture
        elif self.last_pred.isnumeric() and len(self.sequence_of_gestures) ==1:#assures 2nd gesture is numeric
            self.sequence_of_gestures.append(label)
            print(self.sequence_of_gestures)
            self.recognized_sequence = True  #SLISH has recognized a valid alphabetic -> numeric sequence
            self.sequence_of_gestures_backup =list(self.sequence_of_gestures)
            if self.socket.isGestureValid(self.sequence_of_gestures[0]):
                self.selected_appliance =  self.socket.getAppliance(self.sequence_of_gestures[0])
                second = self.sequence_of_gestures[1]
                #if the second gesture presented is 1, turn on the appliance
                if second == '1':
                    self.last_command.config(text="{} turned on".format(self.selected_appliance))
                    with open('logHistory.txt', 'a') as file:
                        file.write(self.last_command.cget("text")+'\n')
                #if the second gesture presented is 2, turn off the appliance
                elif second == '2':
                    self.last_command.config(text="{} turned off".format(self.selected_appliance))
                    with open('logHistory.txt', 'a') as file:
                        file.write(self.last_command.cget("text")+'\n')
                    self.last_sequence_of_gestures.config(text=str(self.sequence_of_gestures[0])+" : "+str(self.sequence_of_gestures[1]))
                #if the second gesture presented is 3, display the appliance that corresponds to the previously presented letter
                else:
                    self.last_command.config(text="command {} controls {}".format(self.sequence_of_gestures[0], self.selected_appliance))
                    with open('logHistory.txt', 'a') as file:
                        file.write(self.last_command.cget("text")+'\n')
            self.sequence_of_gestures *= 0
            self.recently_executed = True
            self.cmd_execution_time = time.time()    
        else:
            pass            

            



    ## Chcecks to see if we have classified a recent image
    def recent_image(self):
        if(self.recently_executed and time.time() - self.cmd_execution_time < 1):
            return True
        else:
            self.recently_executed = False
            self.cmd_execution_time = 0
            return False


    def log_info(self,text):
        with open('logHistory.txt', 'a') as file:
            file.write(text+'\n')
      

    ## Used to time functions
    def add_start(self,string):
        self.time[string+"start"] = time.time()
        self.timing_list.add(string)

    ## Used to time functions
    def add_stop(self,string):
        self.time[string+"stop"] = time.time()
        self.timing_list.add(string)

    ## Used to time functions
    def get_times(self):
        for x in self.timing_list:
            print(str(x)+" = "+str(self.time[str(x)+"stop"]-self.time[str(x)+"start"]))


#beginning of program
Slish()

        
