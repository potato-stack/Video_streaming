from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import tkinter as tk
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
from RtpPacket import RtpPacket
import time
from tkinter.messagebox import showinfo
import math

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

button_config = {
			'font': ("Roboto", 10, "bold"),			
			'bg': "#00a0a0",
			'fg': "white",
			'padx':3,
			'pady':3,
			'bd': 0,				
			'cursor': "hand2",
			'borderwidth': 0,			
			'highlightbackground': "white",
			'relief': "flat",
			'width': 17,
			'height': 1,
}
class Client:
	LOAD = 10
	INIT = 11
	READY = 12
	PLAYING = 13
	
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	STARTAGAIN = 4
	SPEEDUP = 5
	SLOWDOWN = 6
	DESCRIBE = 7	
	REWIND = 8

	state = LOAD
	
	recv_packet_count = 0
	download_rate = 0
	download_rate_sqr = 0
	last_recv_time = time.time()
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)		
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		#self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.createWidgets()
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		
				# self.setup = Button(self.master)
		# self.setup["text"] = "SETUP - load your movie"
		# self.setup["command"] = self.setupMovie
		# self.setup.config(**button_config)
		# self.setup.config(width = 30)
		# self.setup.grid(row=0, column=0, columnspan=4, padx=2, pady=2)

		# Create a Dropdown list		
		self.variable = tk.StringVar(self.master)
		self.variable.set("Choose a movie")
		self.currentFilm = self.variable.get()
		self.dropdown = ttk.Combobox(self.master, textvariable=self.variable, state = "readonly")
		self.dropdown["value"] = ["Choose a movie","Choose a movie","Choose a movie"]
		self.dropdown.pack()
		self.dropdown.grid(row=0, column=1, padx=2, pady=2, columnspan= 2)
		style = ttk.Style()
		style.theme_use('default')  # use the default theme
		style.configure('TCombobox', foreground='gray', borderwidth=2, relief='round', font=('Roboto', 15))
		self.dropdown.bind("<<ComboboxSelected>>", self.update_drop_down_value)		
	
		self.setupMovie()
		# Create Play button		
		self.start = Button(self.master)
		self.start["text"] = "PLAY"
		self.start["command"] = self.playMovie
		self.start.config(**button_config)
		self.start.grid(row=2, column=0, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master)
		self.pause["text"] = "PAUSE"
		self.pause["command"] = self.pauseMovie
		self.pause.config(**button_config)
		self.pause.grid(row=2, column=1, padx=2, pady=2)
		
		# Create Start again button			
		self.startagain = Button(self.master)
		self.startagain["text"] = "Start again"
		self.startagain["command"] = self.startAgain
		self.startagain.config(**button_config)
		self.startagain.grid(row=4, column=2, padx=2, pady=2)

		# Create Speed up button			
		self.speedup = Button(self.master)
		self.speedup["text"] = "Speed up"
		self.speedup["command"] = self.speedUp
		self.speedup.config(**button_config)
		self.speedup.grid(row=2, column=3, padx=2, pady=2)

		# Create Slow down button			
		self.slowdown = Button(self.master)
		self.slowdown["text"] = "Slow down"
		self.slowdown["command"] = self.slowDown
		self.slowdown.config(**button_config)
		self.slowdown.grid(row=2, column=2, padx=2, pady=2)

		# Create Teardown button
		self.teardown = Button(self.master)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.config(**button_config)
		self.teardown.config(background='red')
		self.teardown.grid(row=5, column=1, columnspan = 2, padx=2, pady=2)
		
		# Create Describe button
		self.desc = Button(self.master)
		self.desc["text"] = "Describe"
		self.desc["command"] = self.describe
		self.desc.config(**button_config)
		self.desc.grid(row=4, column=1, padx=2, pady=2)

		# Create progress bar
		style = ttk.Style()
		style.theme_use('clam')
		style.configure('My.Horizontal.TProgressbar', troughcolor='#DCDCDC', bordercolor='black',
                background='#ADD8E6', lightcolor='#ADD8E6', darkcolor='#ADD8E6')
		self.progressbar = ttk.Progressbar(self.master, orient=HORIZONTAL, length=480, mode='determinate', style='My.Horizontal.TProgressbar')
		self.progressbar.grid(row=3, column=0, padx=1, pady=1, columnspan=4)
		self.master.update_idletasks()
		self.progressbar.bind("<Button-1>", self.on_progressbar_click)
		self.progressbar['value'] = 0
		self.currRewind = 0	

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=1, column=0, columnspan=6, sticky=W+E+N+S, padx=5, pady=10) 
	
	def on_progressbar_click(self, event):
		curr_value = self.progressbar['value']
		x = event.x
		w = self.progressbar.winfo_width()
		current_click = int(x/w*100)
		print(current_click*self.totalFrame/100)
		self.currRewind = current_click*self.totalFrame/100

		threading.Thread(target=self.listenRtp).start()
		self.state = self.READY

		self.playEvent = threading.Event()

		self.playEvent.clear()


		self.sendRtspRequest(self.REWIND)
		


	def update_drop_down_value(self, event): 
		temp_file = self.variable.get()
		if(self.fileName != temp_file):
			self.fileName = temp_file


			threading.Thread(target=self.listenRtp).start()
			self.state = self.READY
			self.playEvent = threading.Event() 
			self.playEvent.clear()
			self.sendRtspRequest(self.STARTAGAIN)	

	def setupMovie(self):
		"""Setup button handler."""
		# TODO
		if self.state == self.LOAD:
			self.sendRtspRequest(self.LOAD)
	
	def startAgain(self):
		"""Setup button handler."""
		# TODO
		threading.Thread(target=self.listenRtp).start()
		self.state = self.READY

		self.playEvent = threading.Event()

		self.playEvent.clear()

		self.sendRtspRequest(self.STARTAGAIN)

	def speedUp(self):
		threading.Thread(target=self.listenRtp).start()
		self.state = self.READY

		self.playEvent = threading.Event()

		self.playEvent.clear()

		self.sendRtspRequest(self.SPEEDUP)

	def slowDown(self):
		threading.Thread(target=self.listenRtp).start()
		self.state = self.READY

		self.playEvent = threading.Event()

		self.playEvent.clear()

		self.sendRtspRequest(self.SLOWDOWN)

	def exitClient(self):
		"""Teardown button handler."""
		#TODO
		self.sendRtspRequest(self.TEARDOWN)		

		self.master.destroy() # Close the gui window

		try:
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
		except:
			pass

	def pauseMovie(self):
		"""Pause button handler."""
		#TODO
		if self.state == self.PLAYING:

			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		#TODO
		if self.state == self.READY:

			# Create a new thread to listen for RTP packets

			threading.Thread(target=self.listenRtp).start()

			self.playEvent = threading.Event()

			self.playEvent.clear()

			self.sendRtspRequest(self.PLAY)
	
	def describe(self):
		"""Describe button handler."""
		if self.state != self.INIT:
			self.sendRtspRequest(self.DESCRIBE)

	def listenRtp(self):		
		"""Listen for RTP packets."""
		#TODO
		self.last_recv_time = time.time()
		print(self.rtpSocket)
		while True:

			try:

				data = self.rtpSocket.recv(20480)				
				
				if data:
					download_time = (time.time() - self.last_recv_time)
					rtpPacket = RtpPacket()

					rtpPacket.decode(data)

					currFrameNbr = rtpPacket.seqNum()

					#print ("Current Seq Num: " + str(currFrameNbr))
					
					self.recv_packet_count += 1
										
					if currFrameNbr > self.frameNbr or self.requestSent == self.STARTAGAIN or self.requestSent == self.REWIND: # Discard the late packet
						print ("current frame number: ", currFrameNbr)
						self.frameNbr = currFrameNbr

						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))

						self.master.update_idletasks()
						self.progressbar['value'] = int(currFrameNbr/self.totalFrame*100)
						# print(int(currFrameNbr/self.totalFrame*100))
					
					payload_size = os.path.getsize(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)
					
					# Calculate dowload rate using f(x) linear function: 
					# Dowload rate equal how many byte/1packet/1time_unit is dowloaded
					Byte_dowloaded_per_time_unit = self.download_rate*(self.recv_packet_count-1) # find all we have dowloaded till noew
					new_byte_dowloaded_per_time_unit = Byte_dowloaded_per_time_unit + (payload_size/download_time) #adding the new amount of bytes
					self.download_rate = new_byte_dowloaded_per_time_unit/self.recv_packet_count #devide to find the rate again

				self.last_recv_time = time.time()
			except:

				# Stop listening upon requesting PAUSE or TEARDOWN

				if self.playEvent.isSet(): #is set here is that the pause or teardown is set  					
					break				

				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break

					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		#TODO
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT

		file = open(cachename, "wb")

		file.write(data)

		file.close()

		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		#TODO
		photo = ImageTk.PhotoImage(Image.open(imageFile)) # type: ignore

		self.label.configure(image = photo, height=288) 

		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		#TODO
		# We need a reliable connection for seding and receiving request since no one want to send a request multiple time.
		# For this SOCK_STREAM a.k.a TCP protocol is more suitable
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			# Establish the connect first since this is TCP
			self.rtspSocket.connect((self.serverAddr, self.serverPort))

		except:

			messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)

	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		# Forward or rewind request
		if requestCode == self.REWIND and self.state != self.INIT: 
			self.rtspSeq += 1

			request = 'REWIND ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId) + '\nFrame: ' + str(self.currRewind)

			self.requestSent = self.REWIND
		
		# Loading request
		elif requestCode == self.LOAD and self.state == self.LOAD:

			threading.Thread(target=self.recvRtspReply).start()			
			#update RTSP sequence

			self.rtspSeq += 1

			request = 'LOAD ' + 'all video' + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nTransport: RTP/UDP; client_port= ' + str(self.rtpPort)

			self.requestSent = self.LOAD

		# Setup request
		elif requestCode == self.SETUP and self.state == self.INIT:			

			# Update RTSP sequence number.

			self.rtspSeq += 1
			
			
			# Write the RTSP request to be sent.
			print(self.fileName,'\n')

			request = 'SETUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nTransport: RTP/UDP; client_port= ' + str(self.rtpPort)

			

			# Keep track of the sent request.

			self.requestSent = self.SETUP 

		# STARTAGAIN request

		elif requestCode == self.STARTAGAIN and self.state == self.READY:

			self.rtspSeq += 1

			request = 'STARTAGAIN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)

			self.requestSent = self.STARTAGAIN

		# SPEEDUP request

		elif requestCode == self.SPEEDUP and self.state == self.READY:

			self.rtspSeq += 1

			request = 'SPEEDUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)

			self.requestSent = self.SPEEDUP

		# SLOWDOWN request

		elif requestCode == self.SLOWDOWN and self.state != self.INIT:

			self.rtspSeq += 1

			request = 'SLOWDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)

			self.requestSent = self.SLOWDOWN

		# Play request

		elif requestCode == self.PLAY and self.state == self.READY:

			self.rtspSeq += 1

			request = 'PLAY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)

			self.requestSent = self.PLAY

		# Pause request

		elif requestCode == self.PAUSE and self.state == self.PLAYING:

			self.rtspSeq += 1

			request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)

			self.requestSent = self.PAUSE

			
		# Teardown request

		elif requestCode == self.TEARDOWN:

			self.rtspSeq += 1

			request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId) 

			self.requestSent = self.TEARDOWN
		
		# Describe request

		elif requestCode == self.DESCRIBE:

			self.rtspSeq += 1

			request = "DESCRIBE " + str(self.fileName) + " RTSP/1.0\nCSeq: " + str(self.rtspSeq) + "\nSesssion: " + str(self.sessionId)
			
			self.requestSent = self.DESCRIBE

		else:

			return

		# Send the RTSP request using rtspSocket.
		# Note that we use send here because rtsp is TCP, it reliable, so only need to send, since the conenction is already establish 
		self.rtspSocket.send(bytes(request, 'utf-8'))

		print ('\nData sent:\n' + request)
	
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		#TODO
		while True:
			reply = self.rtspSocket.recv(1024)
			
			# If we receive reply. parse it (decode)
			if reply:
				print('reply:', reply)
				self.parseRtspReply(reply.decode('utf-8'))
			

			# Close the RTSP socket upon requesting Teardown
			
			if self.requestSent == self.TEARDOWN:
				print("shutdown")
				self.rtspSocket.shutdown(socket.SHUT_RDWR)

				self.rtspSocket.close()

				break
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		#TODO
		lines = data.split('\n')

		seqNum = int(lines[1].split(' ')[1])

		# Process only if the server reply's sequence number is the same as the request's

		if seqNum == self.rtspSeq:

			session = int(lines[2].split(' ')[1])

			# New RTSP session ID

			if self.sessionId == 0:

				self.sessionId = session

			

			# Process only if the session ID is the same

			if self.sessionId == session:

				if int(lines[0].split(' ')[1]) == 200: 
					if self.requestSent == self.LOAD:
						# update the movie list	
						movieList = lines[-1].split("'")
						listLength = len(movieList)
						currentList = []
						for i in range (1, listLength, 2):
							currentList.append(movieList[i])
						print(currentList)						
						self.dropdown['value'] = currentList

						self.state = self.INIT
						self.fileName = self.dropdown['value'][0]
						self.sendRtspRequest(self.SETUP)
						
						

					elif self.requestSent == self.SETUP:

						# Update RTSP state.

						self.state = self.READY

						# Open RTP port.

						self.openRtpPort()

						# Update total number of frames						
						self.totalFrame = int(lines[-1].split(" ")[-1])

						# print(f"Total Frame: {self.totalFrame}")

					elif self.requestSent == self.REWIND:
						
						self.state = self.PLAYING
						self.playEvent.set()

					elif self.requestSent == self.STARTAGAIN:
						
						self.state = self.PLAYING
						self.playEvent.set()

					elif self.requestSent == self.PLAY:

						self.state = self.PLAYING

					elif self.requestSent == self.PAUSE and self.state != self.INIT:

						self.state = self.READY

						# The play thread exits. A new thread is created on resume.

						#self.playEvent.set()

					elif self.requestSent == self.SPEEDUP:

						self.state = self.PLAYING
						self.playEvent.set()

					elif self.requestSent == self.SLOWDOWN:

						self.state = self.PLAYING
						self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:

						self.state = self.INIT

						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1 
					
					elif self.requestSent == self.DESCRIBE:
						description = ""
						length = len(lines) - 1
						for i in range(3, length):
							description += lines[i] + "\n\n"
						packet_sent = int(lines[-1].split(" ")[-1])
						description += f"Packet loss: {(packet_sent - self.recv_packet_count)/packet_sent*100:.2f}%" + f"\n\n-->Sent: {packet_sent}" + f"\n\n-->Received: {self.recv_packet_count}" + f"\n\nData rate: {self.download_rate/(1024):.0f} KB/s"
						showinfo("Description", description)
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...

		# In here we use SOCK_DGRAM or can understand as UDP protocol, a connection that suitable for low-lantency and lost tolerance
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		
		# Set the timeout value of the socket to 0.5sec
		# The reason for this is stop the code from waiting too long for coming data, we only need to wait with the interval is 0.5s
		self.rtpSocket.settimeout(0.5)
		
		try:

			# Now the soket has opned, we have to bind the socket to the address using the RTP port given by the client user

			self.rtpSocket.bind(("", self.rtpPort))

		except:

			messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)


	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		#TODO

		self.pauseMovie()

		if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):

			self.exitClient()

		else: # When the user presses cancel, resume playing.

			self.playMovie()
