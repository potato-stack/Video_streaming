from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket
import time
import os

class ServerWorker:	
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	STARTAGAIN = 'STARTAGAIN'
	SPEEDUP = 'SPEEDUP'
	SLOWDOWN = 'SLOWDOWN'
	DESCRIBE = 'DESCRIBE'
	LOAD = 'LOAD'
	REWIND = 'REWIND'

	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2
	
	default_speed = 2
	speeds = [0.0125,0.025, 0.05, 0.075, 0.1]
	curSpeedIndex = default_speed
	SPEED = speeds[default_speed] #the current speeds is 0.05



	clientInfo = {} #define an object for attribute
	
	def __init__(self, clientInfo):
		self.clientInfo = clientInfo
		self.clientInfo['sent_packet_count'] = 0
		self.videoList = os.listdir("Movies")			

	def run(self):
		threading.Thread(target=self.recvRtspRequest).start()
	
	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket'][0]
		# this loop is run in a seperate thread to receive rtsp request
		while True:            
			data = connSocket.recv(256)					
			if data:
				print(data)	
				print("Data received:\n" + data.decode("utf-8"))
				self.processRtspRequest(data.decode("utf-8"))
	
	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.split('\n')
		print(request)
		line1 = request[0].split(' ')
		requestType = line1[0]
		
		# Get the media file name
		filename = line1[1]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		if requestType == self.REWIND:
			
			frameNum = request[3].split(' ')[1]
			if(self.clientInfo['videoStream'].currentFile()):
				self.clientInfo['videoStream'].setFrame(int(float(frameNum)))
				
			print("processing REWIND\n")
			if(self.state == self.PLAYING):
				self.clientInfo['event'].set()
			# Create a new socket for RTP/UDP
			self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.state = self.PLAYING
			
			# Create a new thread and start sending RTP packets
			self.clientInfo['event'] = threading.Event()
			self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
			self.clientInfo['worker'].start()
			self.replyRtsp(self.OK_200, seq[1])
		# Process LOADING request
		elif requestType == self.LOAD:
			# Prepare file information (state not yet change here)
			print("processing LOADING\n")

			# Generate a randomized RTSP session ID for communicate with client
			# This session ID is sent to client to hold the connection	
			self.clientInfo['session'] = randint(100000, 999999)
				
			# Send RTSP reply
			self.replyRtsp(self.OK_200, seq[1], requestType)
				
			# Get the RTP/UDP port from the last line
			self.clientInfo['rtpPort'] = request[2].split(' ')[3]
		# process SETUP request
		elif requestType == self.SETUP:			
				# Update state
				print("processing SETUP\n")
				# print(f"rtspSocket = {self.clientInfo['rtspSocket']}")

				try:
					self.clientInfo['videoStream'] = VideoStream(filename)
					self.state = self.READY
					self.totalFrame = self.clientInfo['videoStream'].getTotalFrame()
					# print(f"Total Frame: {self.totalFrame}")
				except IOError:
					print(IOError)
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
				print('did get out here')
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1], requestType)
				
				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]
		# Process PLAY request 		
		elif requestType == self.PLAY:
			if self.state == self.READY:
				print("processing PLAY\n")
				self.state = self.PLAYING
				
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				
				self.replyRtsp(self.OK_200, seq[1])
				
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
		
		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.state == self.PLAYING:
				print("processing PAUSE\n")
				self.state = self.READY
				
				self.clientInfo['event'].set()
			
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print("processing TEARDOWN\n")

			self.SPEED = self.speeds[self.default_speed]
			try: # if the rtp socket has been setup
				self.clientInfo['event'].set()
				# Close the RTP socket
				self.clientInfo['rtpSocket'].close()
			except:
				pass

			self.replyRtsp(self.OK_200, seq[1])
		
		# Process STARTAGAIN request
		elif requestType == self.STARTAGAIN:
			if self.state != self.INIT:
				self.clientInfo['videoStream'].currentFile().close()
				self.clientInfo['videoStream'] = VideoStream(filename)
				
				print("processing STARTAGAIN\n")
				if(self.state == self.PLAYING):
					self.clientInfo['event'].set()
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				self.state = self.PLAYING
			
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process SPEEDUP request
		elif requestType == self.SPEEDUP:
			if self.state != self.INIT:
				if self.curSpeedIndex > 0: 
					self.curSpeedIndex = self.curSpeedIndex - 1
					self.SPEED = self.speeds[self.curSpeedIndex]
					
				print("processing SPEEDUP\n")
				
				self.replyRtsp(self.OK_200, seq[1])

		# Process SLOWDOWN request
		elif requestType == self.SLOWDOWN:
			if self.state != self.INIT:
				if self.curSpeedIndex < 2: 
					self.curSpeedIndex = self.curSpeedIndex + 1
					self.SPEED = self.speeds[self.curSpeedIndex]				
				
				print("processing SLOWDOWN\n")
				
				self.replyRtsp(self.OK_200, seq[1])

		# Process DESCRIBE request
		elif requestType == self.DESCRIBE:
			if self.state != self.INIT:
				self.replyRtsp(self.OK_200, seq[1], requestType)
			
	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(self.SPEED) 
			
			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet(): 
				break 
			data = self.clientInfo['videoStream'].nextFrame()								
			if data: 
				try:
					frameNumber = self.clientInfo['videoStream'].frameNbr()
					address = self.clientInfo['rtspSocket'][1][0]
					port = int(self.clientInfo['rtpPort'])					
					
					self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,port))
					self.clientInfo['sent_packet_count'] += 1
				except:					
					print("Connection Error")
					
					#print('-'*60)
					#traceback.print_exc(file=sys.stdout)
					#print('-'*60)

	def makeRtp(self, payload, frameNbr):
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0 
		
		rtpPacket = RtpPacket()
		
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)		
		return rtpPacket.getPacket()
	
	def  replyRtsp(self, code, seq, requestType=""):
		"""Send RTSP reply to the client."""
				
		if code == self.OK_200:
			# name = input("enter something: ")
			#print("200 OK")
			
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
			if requestType == self.LOAD:				
				reply += f"\nFile list: {self.videoList}"
			elif requestType == self.SETUP:
				reply += f"\nTotal frame: {self.totalFrame}"				
			elif requestType == self.DESCRIBE:
				# reply += f"\nSession ID: {self.clientInfo['session']}\nFile name: {self.clientInfo['videoStream'].filename}\nStream type: real-time\nEncoding: MJPEG\nProtocol: RTP/RTSP1.0\nRequests count: {seq}\n{self.clientInfo['sent_packet_count']}"
				reply += f"\nSession ID: {self.clientInfo['session']}\nFile name: {self.clientInfo['videoStream'].filename}\nStream type: real-time\nEncoding: MJPEG\nProtocol: RTP/RTSP1.0\nRequests count: {seq}\nPacket sent: {self.clientInfo['sent_packet_count']}"
			elif requestType in [self.PLAY, self.STARTAGAIN, self.SLOWDOWN, self.STARTAGAIN]:
				reply += f"\nSent time: {time.time()}"
			connSocket = self.clientInfo['rtspSocket'][0]
			#print('connSocket', connSocket)			
		
			connSocket.send(reply.encode())
			
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")
