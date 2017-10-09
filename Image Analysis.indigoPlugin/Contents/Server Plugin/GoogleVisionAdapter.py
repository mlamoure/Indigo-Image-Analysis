import requests
import json
import io

from base64 import b64encode
from ImageProcessingAdapter import ImageProcessingAdapter
from ImageProcessingAdapter import ImageProcessingResult
from ImageProcessingAdapter import SimpleResult
from ImageProcessingAdapter import FaceResult

CONTENT_TYPE = "application/json"
MAX_RESULTS = 10

class GoogleImageProcessingAdapter(ImageProcessingAdapter):
	def sendImage(self, image, options):
		request = {"requests": []}

		if image[:4].lower() == "http":
			request["requests"].append({"image": {"source": {"imageUri": image}}})
		else:
			try:
				with io.open(image, 'rb') as image_file:
					content = image_file.read()
			except:
				self.logger.error("Error opening image to send to Google Vision")
				return

			request["requests"].append({"image": {"content": b64encode(content)}})

		request["requests"][0]["features"] = []

		if options.processOCR:
			request["requests"][0]["features"].append({"type": "TEXT_DETECTION","maxResults": MAX_RESULTS})

		if options.processLabel:
			request["requests"][0]["features"].append({"type": "LABEL_DETECTION","maxResults": MAX_RESULTS})

		if options.processFace:
			request["requests"][0]["features"].append({"type": "FACE_DETECTION","maxResults": MAX_RESULTS})

		if options.processLogo:
			request["requests"][0]["features"].append({"type": "LOGO_DETECTION","maxResults": MAX_RESULTS})

#		self.logger.debug(json.dumps(request))

		try:
			response = requests.post(
				url="https://vision.googleapis.com/v1/images:annotate?" + "key=" + self.apikey,
				headers={
					"Content-Type": CONTENT_TYPE
				},
				data=json.dumps(request)
			)
			self.logger.debug('Response HTTP Status Code: {status_code}'.format(
				status_code=response.status_code))
			self.logger.debug('Response HTTP Response Body: {content}'.format(
				content=response.content))
		except requests.exceptions.RequestException:
			self.logger.error('HTTP Request failed')

		return self.processResults(response.json())


	def processResults(self, result):
		self.logger.debug(json.dumps(result))

		processedResults = ImageProcessingResult()

		if "error" in result:
			self.logger.error("Error message in result")
			return

		if "labelAnnotations" in result["responses"][0]:
			for lbl in result["responses"][0]["labelAnnotations"]:
				newLabel = SimpleResult(lbl["description"], lbl["score"])
				processedResults.Label_Results.append(newLabel)

		if "textAnnotations" in result["responses"][0]:
			for ocr in result["responses"][0]["textAnnotations"]:
				newOCR = None

				if "locale" in ocr:
					newOCR = SimpleResult(ocr["description"], None, ocr["locale"])
				else:
					newOCR = SimpleResult(ocr["description"])

				processedResults.OCR_Results.append(newOCR)

		if "faceAnnotations" in result["responses"][0]:
			for face in result["responses"][0]["faceAnnotations"]:

				newFace = FaceResult(face["detectionConfidence"])
				newFace.Details = face
				
				processedResults.Face_Results.append(newFace)

		if "logoAnnotations" in result["responses"][0]:
			for logo in result["responses"][0]["logoAnnotations"]:
				newLogo = None

				if "locale" in logo:
					newLogo = SimpleResult(ocr["description"], logo["score"], logo["locale"])
				else:
					newLogo = SimpleResult(ocr["description"], logo["score"])

				processedResults.Logo_Results.append(newLogo)

		return processedResults

