#! /usr/bin/env python
####################

import indigo

import os
import sys
import datetime
import time
import json
import copy
from copy import deepcopy

from ImageProcessingAdapter import ImageProcessingOptions
from GoogleVisionAdapter import GoogleImageProcessingAdapter
from AWSRekognitionAdapter import AWSImageProcessingAdapter

from ghpu import GitHubPluginUpdater

DEFAULT_UPDATE_FREQUENCY = 24 # frequency of update check

emptyEVENT = {
	"eventType": "OCR",
	"OCR" : "",
	"label" : "",
	"logo" : "",
	"notLabel": "0",
	"labelScore" : ".9",
	"logoScore" : ".9",
	"faceScore" : ".9",
	"noFace" : "0",
	"enableDisable" : "0"
}

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("chkDebug", False)

		self.updater = GitHubPluginUpdater(self)
		self.updater.checkForUpdate(str(self.pluginVersion))
		self.lastUpdateCheck = datetime.datetime.now()
		self.pollingInterval = 60

		self.configServices(pluginPrefs)

		self.currentEventN = "0"

		if "EVENTS" in self.pluginPrefs:
			self.EVENTS = json.loads(self.pluginPrefs["EVENTS"])
		else:
			self.EVENTS =  {}


	########################################
	def startup(self):
		self.debugLog(u"startup called")


	def checkForUpdates(self):
		self.updater.checkForUpdate()

	def updatePlugin(self):
		self.updater.update()

	def shutdown(self):
		self.pluginPrefs["EVENTS"] = json.dumps(self.EVENTS)
		self.debugLog(u"shutdown called")

	def deviceStartComm(self, dev):
		self.debugLog(u"deviceStartComm: %s" % (dev.name,))

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	def updateConfig(self, valuesDict):
		return valuesDict

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			self.configServices(valuesDict)
			self.debug = valuesDict["chkDebug"]

	def configServices(self, pluginPrefs):
		self.imageProcessors = []

		APIKey = pluginPrefs.get("GoogleAPIKey", None)

		if APIKey is not None:
			self.imageProcessors.append(GoogleImageProcessingAdapter(self.logger, [APIKey]))

		APIKey = pluginPrefs.get("AWSAPIKey", None)
		APIKey2 = pluginPrefs.get("AWSSecretAPIKey", None)

		if APIKey is not None:
			self.imageProcessors.append(AWSImageProcessingAdapter(self.logger, [APIKey, APIKey2]))

	def eventConfigCallback(self, valuesDict,typeId=""):
		self.currentEventN=str(valuesDict["selectEvent"])

		if self.currentEventN =="0":
			errorDict = valuesDict
			return valuesDict
		
		if not self.currentEventN in self.EVENTS:
			self.EVENTS[self.currentEventN]= copy.deepcopy(emptyEVENT)
	
		valuesDict["eventType"] = str(self.EVENTS[self.currentEventN]["eventType"])
		valuesDict["OCR"] = str(self.EVENTS[self.currentEventN]["OCR"])
		valuesDict["label"] = str(self.EVENTS[self.currentEventN]["label"])
		valuesDict["logo"] = str(self.EVENTS[self.currentEventN]["logo"])
		valuesDict["notLabel"] = str(self.EVENTS[self.currentEventN]["notLabel"])
		valuesDict["labelScore"] = str(self.EVENTS[self.currentEventN]["labelScore"])
		valuesDict["faceScore"]	= str(self.EVENTS[self.currentEventN]["faceScore"])
		valuesDict["logoScore"]	= str(self.EVENTS[self.currentEventN]["logoScore"])
		valuesDict["noFace"] = self.EVENTS[self.currentEventN]["noFace"]
		valuesDict["enableDisable"] = self.EVENTS[self.currentEventN]["enableDisable"]

		self.updatePrefs =True
		return valuesDict

	def getMenuActionConfigUiValues(self, menuId):
		#indigo.server.log(u'Called getMenuActionConfigUiValues(self, menuId):')
		#indigo.server.log(u'     (' + unicode(menuId) + u')')

		valuesDict = indigo.Dict()
		valuesDict["selectEvent"] = "0"
		valuesDict["eventType"] = "0"
		valuesDict["enableDisable"] = "0"
		errorMsgDict = indigo.Dict()
		return (valuesDict, errorMsgDict)


	def sendImageAction(self, pluginAction, dev):
		result = None
		processOCR = False
		processFace = False
		processLabel = False
		processLogo = False

		for i in self.EVENTS:
			evnt = self.EVENTS[i]
			if pluginAction.props["event" + str(i)]:
				if evnt["eventType"] == "OCR":
					processOCR = True

				if evnt["eventType"] == "Face":
					processFace = True

				if evnt["eventType"] == "Label":
					processLabel = True

				if evnt["eventType"] == "Logo":
					processLogo = True

		if not (processOCR or processLabel or processLogo or processFace):
			self.logger.error("No configured events for this action")
			return

		options = ImageProcessingOptions(processOCR, processFace, processLabel, processLogo)
		image = None

		if pluginAction.props["locationOption"] == "static":
			image = pluginAction.props["location"]
		else:
			image = indigo.variables[int(pluginAction.props["locationVariable"])].value

		### SEND TO GOOGLE
		if pluginAction.pluginTypeId == "sendImageGoogle":
			imageProcessor = None

			for processor in self.imageProcessors:
				if isinstance(processor, GoogleImageProcessingAdapter):
					imageProcessor = processor

			if imageProcessor == None:
				indigo.server.log("Not properly configured for Google Vision API")
				return

			indigo.server.log("sending " + image + " to Google Vision API")

			result = imageProcessor.sendImage(image, options)

		### SEND TO AWS
		elif pluginAction.pluginTypeId == "sendImageAWS":
			imageProcessor = None

			for processor in self.imageProcessors:
				if isinstance(processor, AWSImageProcessingAdapter):
					imageProcessor = processor

			if imageProcessor == None:
				indigo.server.log("Not properly configured for AWS Rekognition API")
				return

			indigo.server.log("sending " + image + " to AWS Rekognition API")

			result = imageProcessor.sendImage(image, options)

		if result is None:
			self.logger.error("Returned no results")
			return

		### PROCESS RESULTS
		buildstr = ""
		facecounter = 0
		resultsFound = False


		## OUTPUT TO INDIGO
		if len(result.Label_Results) > 0:
			resultsFound = True
			for lbl in result.Label_Results:
				buildstr += lbl.description + " (score:" + str(lbl.confidence) +"), "

			indigo.server.log("Label Results: " + buildstr[:-2])
			buildstr = ""

		if len(result.OCR_Results) > 0:
			resultsFound = True
			for ocr in result.OCR_Results:
				buildstr += ocr.description.replace('\n','') + " (language:" + ocr.other + "), "

			indigo.server.log("OCR Results: " + buildstr[:-2])
			buildstr = ""

		if len(result.Face_Results) > 0:
			resultsFound = True
			for face in result.Face_Results:
				facecounter += 1

				buildstr += "Face " + str(facecounter) + " with confidence of " + str(face.Confidence) + ".  "

			buildstr = "Found a total of " + str(facecounter) + " face(s).  " + buildstr
			indigo.server.log("Face Results: " + buildstr[:-2])
			buildstr = ""

		if len(result.Logo_Results) > 0:
			resultsFound = True
			for logo in result.Logo_Results:
				buildstr += logo.description + " (score:" + str(logo.confidence) + ", language: " + logo.other + "), "

			indigo.server.log("Logo Results: " + buildstr[:-2])
			buildstr = ""

		if not resultsFound:
			indigo.server.log("No results found in image.")

		for trigger in indigo.triggers.iter("self"):
			eventID = trigger.pluginTypeId[5:].strip()

#			self.logger.debug("size of self.EVENTS: " + str(len(self.EVENTS)) + " , eventID: " + eventID)
			if int(eventID) <= len(self.EVENTS):
				eventType = self.EVENTS[eventID]["eventType"]
			else:
				self.logger.error("Trigger '" + trigger.name + "'' is configured for a disabled Google Vision event, skipping...")
				continue

			if not self.EVENTS[eventID]["enableDisable"]:
				self.logger.error("Trigger '" + trigger.name + "'' is configured for a disabled Google Vision event, skipping...")
				continue

			if not pluginAction.props["event" + eventID]:
				self.logger.debug("Trigger '" + trigger.name + "' is not applicable for event " + eventID + ", skipping...")
				continue	

			self.logger.debug("Evaluating trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")

			if eventType == "OCR":
				ocrSearch = self.EVENTS[eventID]["OCR"]

				if len(result.OCR_Results) > 0:
					for ocr in result.OCR_Results:
						if ocrSearch.lower() in ocr.description.lower():
							self.logger.debug("Executing trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")
							indigo.trigger.execute(trigger)
							break

			elif eventType == "Face":
				if facecounter == 0 and self.EVENTS[eventID]["noFace"]:
					self.logger.debug("Executing trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")
					indigo.trigger.execute(trigger)
				elif facecounter == 0:
					continue
				else:
					for face in result.Face_Results:
						if face.detectionConfidence >= float(self.EVENTS[eventID]["faceScore"]):
							self.logger.debug("Executing trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")
							indigo.trigger.execute(trigger)
							break

			elif eventType == "Label":
				foundLabel = False

				if len(result.Label_Results) > 0:
					for lbl in result.Label_Results:
						if len(self.EVENTS[eventID]["label"]) > 0:
							for lblSearch in self.EVENTS[eventID]["label"].replace(" ", "").split(","):
								if lblSearch.lower() == lbl.description.lower() and lbl.confidence >= float(self.EVENTS[eventID]["labelScore"]):
									self.logger.debug("Trigger '" + trigger.name + "' Found label of interest: " + lblSearch)
									foundLabel = True

				if (foundLabel and not self.EVENTS[eventID]["notLabel"]) or (not foundLabel and self.EVENTS[eventID]["notLabel"]):
					self.logger.debug("Executing trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")
					indigo.trigger.execute(trigger)

			elif eventType == "Logo":
				foundLogo = False
				self.logger.debug("Looking for logos: " + self.EVENTS[eventID]["txtLogo"])

				if len(result.Logo_Results) > 0:
					for logo in result.Logo_Results:
						if len(self.EVENTS[eventID]["logo"]) > 0:
							for logoSearch in self.EVENTS[eventID]["logo"].replace(" ", "").split(","):
								if logoSearch.lower() == logo.description.lower() and logo.confidence >= float(self.EVENTS[eventID]["logoScore"]):
									self.logger.debug("Found logo of interest: " + logoSearch)
									foundLogo = True

				if foundLogo:
					self.logger.debug("Executing trigger '" + trigger.name + "' (eventID: " + eventID + ", eventType: " + eventType + ")")
					indigo.trigger.execute(trigger)

########################################
	def buttonConfirmDevicesCALLBACK(self, valuesDict,typeId=""):
		errorDict=indigo.Dict()

		self.currentEventN=str(valuesDict["selectEvent"])

		if self.currentEventN == "0" or  self.currentEventN =="":
			return valuesDict

		if not self.currentEventN in self.EVENTS:
			self.EVENTS[self.currentEventN] = copy.deepcopy(emptyEVENT)

		if valuesDict["DeleteEvent"]:
			valuesDict["DeleteEvent"] = False

			valuesDict["eventType"] = "OCR"
			valuesDict["OCR"] = ""
			valuesDict["label"] = ""
			valuesDict["logo"] = ""
			valuesDict["notLabel"] = False
			valuesDict["labelScore"] = .90
			valuesDict["logoScore"] = .90
			valuesDict["faceScore"]	= .90
			valuesDict["enableDisable"] = False
			valuesDict["noFace"] = False

			self.EVENTS[self.currentEventN] = copy.deepcopy(emptyEVENT)
			self.currentEventN ="0"
			valuesDict["selectEvent"] ="0"
			valuesDict["EVENT"] =json.dumps(self.EVENTS)
			return valuesDict

##### not delete
		if valuesDict["enableDisable"]      != "": self.EVENTS[self.currentEventN]["enableDisable"] = valuesDict["enableDisable"]
		else: self.EVENTS[self.currentEventN]["enableDisable"] = emptyEVENT["enableDisable"]; valuesDict["enableDisable"] =  emptyEVENT["enableDisable"];errorDict["enableDisable"]=emptyEVENT["enableDisable"]

		self.EVENTS[self.currentEventN]["eventType"] = valuesDict["eventType"]
		self.EVENTS[self.currentEventN]["OCR"] = valuesDict["OCR"]
		self.EVENTS[self.currentEventN]["label"] = valuesDict["label"]
		self.EVENTS[self.currentEventN]["logo"] = valuesDict["logo"]
		self.EVENTS[self.currentEventN]["notLabel"] = valuesDict["notLabel"]
		self.EVENTS[self.currentEventN]["labelScore"] = valuesDict["labelScore"]
		self.EVENTS[self.currentEventN]["logoScore"] = valuesDict["logoScore"]
		self.EVENTS[self.currentEventN]["faceScore"] = valuesDict["faceScore"]
		self.EVENTS[self.currentEventN]["noFace"] = valuesDict["noFace"]
		self.EVENTS[self.currentEventN]["enableDisable"] = valuesDict["enableDisable"]

		valuesDict["EVENTS"] = json.dumps(self.EVENTS)

		if len(errorDict) > 0: return  valuesDict, errorDict
		return  valuesDict

