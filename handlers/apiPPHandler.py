import json
import sys
import traceback
import math

import tornado.gen
import tornado.web
from raven.contrib.tornado import SentryMixin

from objects import beatmap
from common.constants import gameModes
from common.log import logUtils as log
from common.web import requestsManager
from constants import exceptions
from objects import glob
from pp import rippoppai
from pp import omppcPy
from common.sentry import sentry

MODULE_NAME = "api/pp"
class handler(requestsManager.asyncRequestHandler):
	"""
	Handler for /api/v1/pp
	"""
	@tornado.gen.coroutine
	@tornado.web.asynchronous
	@tornado.gen.engine
	@sentry.captureTornado
	def asyncGet(self):
		statusCode = 400
		data = {"message": "unknown error"}
		try:
			# Check arguments
			if not requestsManager.checkArguments(self.request.arguments, ["b"]):
				raise exceptions.invalidArgumentsException(MODULE_NAME)

			# Get beatmap ID and make sure it's a valid number
			beatmapID = self.get_argument("b")
			if not beatmapID.isdigit():
				raise exceptions.invalidArgumentsException(MODULE_NAME)

			# Get mods
			if "m" in self.request.arguments:
				modsEnum = self.get_argument("m")
				if not modsEnum.isdigit():
					raise exceptions.invalidArgumentsException(MODULE_NAME)
				modsEnum = int(modsEnum)
			else:
				modsEnum = 0

			# Get game mode
			if "g" in self.request.arguments:
				gameMode = self.get_argument("g")
				if not gameMode.isdigit():
					raise exceptions.invalidArgumentsException(MODULE_NAME)
				gameMode = int(gameMode)
			else:
				gameMode = 0

			# Get acc
			if "a" in self.request.arguments:
				accuracy = self.get_argument("a")
				try:
					accuracy = float(accuracy)
					if math.isnan(accuracy):
						accuracy = -1.0
				except ValueError:
					raise exceptions.invalidArgumentsException(MODULE_NAME)
			else:
				accuracy = -1.0

			if "x" in self.request.arguments:
				misses = self.get_argument("x")
				try:
					misses = int(misses)
				except ValueError:
					raise exceptions.invalidArgumentsException(MODULE_NAME)
			else:
				misses = 0

			if "c" in self.request.arguments:
				combo = self.get_argument("c")
				if not combo.isdigit():
					raise exceptions.invalidArgumentsException(MODULE_NAME)
				combo = int(combo)
			else:
				combo = 0


			# Print message
			log.info("Requested pp for beatmap {}".format(beatmapID))

			# Get beatmap md5 from osuapi
			# TODO: Move this to beatmap object
			"""osuapiData = osuapiHelper.osuApiRequest("get_beatmaps", "b={}".format(beatmapID))
			if osuapiData is None or "file_md5" not in osuapiData or "beatmapset_id" not in osuapiData:
				raise exceptions.invalidBeatmapException(MODULE_NAME)
			beatmapMd5 = osuapiData["file_md5"]
			beatmapSetID = osuapiData["beatmapset_id"]"""
			dbData = glob.db.fetch("SELECT beatmap_md5, beatmapset_id, mode FROM beatmaps WHERE beatmap_id = {}".format(beatmapID))
			if dbData is None:
				raise exceptions.invalidBeatmapException(MODULE_NAME)

			beatmapMd5 = dbData["beatmap_md5"]
			beatmapSetID = dbData["beatmapset_id"]

			# Create beatmap object
			bmap = beatmap.beatmap(beatmapMd5, beatmapSetID)
			stars = 0
			# Check beatmap length
			if bmap.hitLength > 900:
				raise exceptions.beatmapTooLongException(MODULE_NAME)

			returnPP = []
			if gameMode == gameModes.STD and bmap.starsStd == 0:
				gameMode = dbData["mode"]
				if(gameMode == 2):
					raise exceptions.unsupportedGameModeException
			if accuracy > 100 or combo > bmap.maxCombo or misses < 0 or math.isnan(accuracy):
				raise exceptions.invalidArgumentsException(MODULE_NAME)
			# Calculate pp
			if gameMode != 2:
				# Std pp
				if accuracy < 0 and combo == 0 and misses == 0 and gameMode == dbData["mode"]:
					# Generic acc
					# Get cached pp values
					cachedPP = bmap.getCachedTillerinoPP()
					if(modsEnum == 0 and cachedPP != [0,0,0,0]):
						log.debug("Got cached pp.")
						returnPP = cachedPP
						stars = bmap.starsStd
					else:
						log.debug("Cached pp not found. Calculating pp with oppai...")
						# Cached pp not found, calculate them
						if(gameMode == 1 or gameMode == 0):
							oppai = rippoppai.oppai(bmap, mods=modsEnum, tillerino=True, stars=True)
							returnPP = oppai.pp
							stars = oppai.stars
						else:
							xeno = omppcPy.piano(bmap, mods=modsEnum, tillerino=True, stars=True)
							returnPP = xeno.pp
							stars = xeno.stars

						# Cache values in DB
						log.debug("Saving cached pp...")
						if(modsEnum == 0 and type(returnPP) != int and len(returnPP) == 4):
							bmap.saveCachedTillerinoPP(returnPP)
				else:
					# Specific accuracy, calculate
					# Create oppai instance
					if(gameMode == 3):
							log.info("Specific request ({}%/{}). Calculating pp with omppc...".format(accuracy, modsEnum))
							xeno = omppcPy.piano(bmap, acc=accuracy, mods=modsEnum, tillerino=False, stars=True)
							returnPP.append(xeno.pp)
							stars = xeno.stars	
					else:
						if(gameMode != 0 and gameMode != 1):
							raise exceptions.unsupportedGameModeException
						log.debug("Specific request ({}%/{}). Calculating pp with oppai...".format(accuracy, modsEnum))
						oppai = rippoppai.oppai(bmap, mods=modsEnum, tillerino=False, stars=True)
						stars = oppai.stars
						if accuracy > 0:
							oppai.acc = accuracy
						if combo > 0:
							oppai.combo = combo
						if misses > 0:
							oppai.misses = misses	
						oppai.getPP()
						returnPP.append(oppai.pp)
			else:
				raise exceptions.unsupportedGameModeException

			# Data to return
			data = {
				"song_name": bmap.songName,
				"pp": returnPP,
				"length": bmap.hitLength,
				"stars": stars,
				"ar": bmap.AR,
				"od": bmap.OD,
				"bpm": bmap.bpm,
			}
			# Set status code and message
			statusCode = 200
			data["message"] = "ok"
		except exceptions.invalidArgumentsException:
			# Set error and message
			statusCode = 400
			data["message"] = "missing required arguments"
		except exceptions.invalidBeatmapException:
			statusCode = 400
			data["message"] = "beatmap not found"
		except exceptions.beatmapTooLongException:
			statusCode = 400
			data["message"] = "requested beatmap is too long"
		except exceptions.unsupportedGameModeException:
			statusCode = 400
			data["message"] = "Unsupported gamemode"
		finally:
			# Add status code to data
			data["status"] = statusCode

			# Debug output
			log.debug(str(data))

			# Send response
			#self.clear()
			self.write(json.dumps(data))
			self.set_header("Content-Type", "application/json")
			self.set_status(statusCode)
