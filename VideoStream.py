import cv2
import os 
import numpy as np 
class VideoStream:
	path = ''	
	def __init__(self, filename):
		self.filename = filename

		# self.totalFrame number of frames
		self.path = os.path.join('Movies',filename)
		video = cv2.VideoCapture(self.path)		
		
		success = True
		self.totalFrame = 0		
		
		while success:
			success,image = video.read()
			if success == False:
				break
			self.totalFrame += 1
			#print(self.totalFrame)
		video.release()
		
		try:
			# self.file = cv2.VideoCapture(path)
			self.file =  open(self.path, 'rb')
		except:
			raise IOError
		self.frameNum = 0

	def nextFrame(self):
		"""Get next frame."""
		try:
			
			data = self.file.read(5) # Get the framelength from the first 5 bits			
			if data: 
				framelength = int(data)								
				# Read the current frame
				data = self.file.read(framelength)
				self.frameNum += 1		
			return data
		except:
			pass
		return None
	def setFrame(self, frameNum):
		"""Go to the require frame number"""
		if frameNum < self.frameNum:
			self.file.close()
			self.frameNum = 0			
			self.file = open(self.path, 'rb')
			print('reset here')
		while(self.frameNum < frameNum):
			try: 
				data = self.file.read(5) # Get the framelength from the first 5 bits			
				if data: 
					framelength = int(data)								
					# Read the current frame
					data = self.file.read(framelength)
					self.frameNum += 1
			except:
				pass
			
		return None
			
	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum
	
	def currentFile(self):
		return self.file
	
	def getTotalFrame(self):
		return self.totalFrame