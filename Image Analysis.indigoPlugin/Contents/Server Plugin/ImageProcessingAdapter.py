class ImageProcessingAdapter():
	configured = False

	def __init__(self, logger, apikeys = []):
		self.configured = len(apikeys) > 0
		self.apikey = None
		self.apikey2 = None
		self.logger = logger

		if len(apikeys) == 0: return

		self.apikey = apikeys[0]

		if len(apikeys) == 2:
			self.apikey2 = apikeys[1]

class ImageProcessingOptions():
	def __init__(self, processOCR, processFace, processLabel, processLogo):
		self.processOCR = processOCR
		self.processFace = processFace
		self.processLabel = processLabel
		self.processLogo = processLogo

class ImageProcessingResult():
	def __init__(self):
		self.OCR_Results = []
		self.Face_Results = []
		self.Label_Results = []
		self.Logo_Results = []

class SimpleResult():
	def __init__(self, description, confidence = -1, other = ""):
		self.description = description
		self.confidence = confidence
		self.other = other

class FaceResult():
	def __init__(self, confidence = 0):
		self.Confidence = confidence
		self.Details = None
