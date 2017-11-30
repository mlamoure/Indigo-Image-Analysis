import sys

from ImageProcessingAdapter import ImageProcessingAdapter
from ImageProcessingAdapter import ImageProcessingResult
from ImageProcessingAdapter import SimpleResult
from ImageProcessingAdapter import FaceResult
import boto3

ENDPOINT_URL = "https://rekognition.us-east-1.amazonaws.com"
REGION = "us-east-1"
MAX_RESULTS = 10

class AWSImageProcessingAdapter(ImageProcessingAdapter):
	def sendImage(self, image, options):

		if options.processOCR:
			self.logger.warn("OCR Processing not supported for AWS rekognition, skipping (" + image + ")")

		if options.processLogo:
			self.logger.warn("Logo Processing not supported for AWS rekognition, skipping (" + image + ")")

		client = boto3.client('rekognition', region_name=REGION, endpoint_url=ENDPOINT_URL, verify=False, aws_access_key_id=self.apikey, aws_secret_access_key=self.apikey2)
		
		response_faces = []
		response_labels = []

		if options.processLabel:
			with open(image, 'rb') as image:
				response_labels = client.detect_labels(Image={'Bytes': image.read()})
				self.logger.debug(response_labels)

		if options.processFace:
			with open(image, 'rb') as image:
				response_faces = client.detect_faces(Image={'Bytes': image.read()})
				self.logger.debug(response_faces)
		

		return self.processResults([response_labels, response_faces])


	def processResults(self, result):
		processedResults = ImageProcessingResult()

		for res in result:
			if 'Labels' in res:
				for lbl in res["Labels"]:
					newLabel = SimpleResult(lbl["Name"], lbl["Confidence"])
					processedResults.Label_Results.append(newLabel)

			if 'FaceDetails' in res:
				for faceDetail in res['FaceDetails']:
					newFace = FaceResult()

					newFace.Confidence = faceDetail['Confidence']
					newFace.Details = faceDetail
					
					processedResults.Face_Results.append(newFace)

		return processedResults