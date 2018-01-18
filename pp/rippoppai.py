"""
oppai interface for ripple 2 / LETS
"""
import json
import os
import subprocess

from common.constants import gameModes
from common import generalUtils
from common.constants import bcolors
from common.ripple import scoreUtils
from constants import exceptions
from helpers import consoleHelper
from helpers import osuapiHelper
from objects import glob
from common.log import logUtils as log
from helpers import mapsHelper


# constants
MODULE_NAME = "rippoppai"
UNIX = True if os.name == "posix" else False

def fixPath(command):
	"""
	Replace / with \ if running under WIN32

	commnd -- command to fix
	return -- command with fixed paths
	"""
	if UNIX:
		return command
	return command.replace("/", "\\")


class OppaiError(Exception):
	def __init__(self, error):
		self.error = error

class oppai:
	"""
	Oppai calculator
	"""
	# Folder where oppai is placed
	OPPAI_FOLDER = "../oppai"

	def __init__(self, __beatmap, __score = None, acc = 0, mods = 0, tillerino = False, stars = False):
		"""
		Set oppai params.

		__beatmap -- beatmap object
		__score -- score object
		acc -- manual acc. Used in tillerino-like bot. You don't need this if you pass __score object
		mods -- manual mods. Used in tillerino-like bot. You don't need this if you pass __score object
		tillerino -- If True, self.pp will be a list with pp values for 100%, 99%, 98% and 95% acc. Optional.
		stars -- If True, self.stars will be the star difficulty for the map (including mods)
		"""
		# Default values
		self.pp = 0
		self.score = None
		self.acc = 0
		self.mods = 0
		self.combo = 0
		self.misses = 0
		self.stars = 0
		self.gameMode = None
		# Beatmap object
		self.beatmap = __beatmap
		self.map = "{}.osu".format(self.beatmap.beatmapID)
		self.tillerino = tillerino
		# If passed, set everything from score object
		if __score is not None:
			self.score = __score
			self.acc = self.score.accuracy*100
			self.mods = self.score.mods
			self.gameMode = self.score.gameMode
			self.combo = self.score.maxCombo
			self.misses = self.score.cMiss
		else:
			# Otherwise, set acc and mods from params (tillerino)
			self.acc = acc
			self.mods = mods
			if float(self.beatmap.starsStd) > 0:
				self.gameMode = gameModes.STD
			elif float(self.beatmap.starsTaiko) > 0:
				self.gameMode = gameModes.TAIKO
			else:
				self.gameMode = None

		# Calculate pp
		self.getPP(tillerino, stars)


	def _runOppaiProcess(self, command):
		log.debug("oppai ~> running {}".format(command))
		process = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
		try:
			output = json.loads(process.stdout.decode("utf-8", errors="ignore"))
			if "code" not in output or "errstr" not in output:
				raise OppaiError("No code in json output")
			if output["code"] != 200:
				raise OppaiError("oppai error {}: {}".format(output["code"], output["errstr"]))
			if "pp" not in output or "stars" not in output:
				raise OppaiError("No pp/stars entry in oppai json output")
			pp = output["pp"]

			stars = output["stars"]
			if(self.gameMode == gameModes.STD):
				mod = "difficulty_{}".format(scoreUtils.readableMods(self.mods & 80))
				if(mod == "difficulty_HR" or mod == "difficulty_DT"):
					diff = glob.db.fetch("SELECT {} FROM beatmaps WHERE beatmap_md5 = '{}'".format(mod, self.beatmap.fileMD5))[mod]
					if(diff == 0):
						glob.db.execute("UPDATE beatmaps SET {} = {} WHERE beatmap_md5 = '{}'".format(mod, round(stars,5), self.beatmap.fileMD5))
			log.debug("oppai ~> full output: {}".format(output))
			log.debug("oppai ~> pp: {}, stars: {}".format(pp, stars))
		except (json.JSONDecodeError, IndexError, OppaiError) as e:
			raise OppaiError(e)
		return pp, stars


	def getPP(self, tillerino = False, stars = False):
		"""
		Calculate total pp value with oppai and return it

		return -- total pp
		"""
		# Set variables
		self.pp = 0
		try:
			# Build .osu map file path
			mapFile = "{path}/maps/{map}".format(path=self.OPPAI_FOLDER, map=self.map)

			mapsHelper.cacheMap(mapFile, self.beatmap)

			# Base command
			command = fixPath("{path}/oppai {mapFile}".format(path=self.OPPAI_FOLDER, mapFile=mapFile))

			# Use only mods supported by oppai.
			modsFixed = self.mods & 14303
			command += " scorev{ver}".format(ver=scoreUtils.scoreType(self.mods))
			# Add params if needed
			if not self.tillerino:
				if self.acc > 0:
					command += " {acc:.2f}%".format(acc=self.acc)

			if self.mods > 0:
				command += " +{mods}".format(mods=scoreUtils.readableMods(modsFixed))
			if self.combo > 0:
				command += " {combo}x".format(combo=self.combo)
			if self.misses > 0:
				command += " {misses}xm".format(misses=self.misses)
			if self.gameMode == gameModes.TAIKO:
				command += " -taiko"
			command += " -ojson"
			# Calculate pp
			if not self.tillerino:
				# self.pp, self.stars = self._runOppaiProcess(command)
				temp_pp, self.stars = self._runOppaiProcess(command)
				if (self.gameMode == gameModes.TAIKO and self.beatmap.starsStd > 0 and temp_pp > 800) or self.stars > 50:
					# Invalidate pp for bugged taiko converteds and bugged inf pp std maps
					self.pp = 0
				else:
					self.pp = round(temp_pp, 2)
			else:
				pp_list = []
				for acc in [100, 99, 98, 95]:
					temp_command = command
					temp_command += " {acc:.2f}%".format(acc=acc)
					pp, self.stars = self._runOppaiProcess(temp_command)

					# If this is a broken converted, set all pp to 0 and break the loop
					if self.gameMode == gameModes.TAIKO and self.beatmap.starsStd > 0 and pp > 800:
						pp_list = [0, 0, 0, 0]
						break

					pp_list.append(round(pp, 2))
				self.pp = pp_list

			# Debug output
			if glob.debug:
				consoleHelper.printRippoppaiMessage("Executing {}".format(command))

			# oppai output
			"""process = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
			output = process.stdout.decode("utf-8")

			# Get standard or tillerino output
			sep = "\n" if UNIX else "\r\n"
			if output == ['']:
				# This happens if mode not supported or something
				self.pp = 0
				self.stars = None
				return self.pp

			output = output.split(sep)

			# get rid of pesky warnings!!!
			try:
				float(output[0])
			except ValueError:
				del output[0]

			if tillerino:
				# Get tillerino output (multiple lines)
				if stars:
					self.pp = output[:-2]
					self.stars = float(output[-2])
				else:
					self.pp = output.split(sep)[:-1]	# -1 because there's an empty line at the end
			else:
				# Get standard output (:l to remove (/r)/n at the end)
				l = -1 if UNIX else -2
				if stars:
					self.pp = float(output[len(output)-2][:l-1])
				else:
					self.pp = float(output[len(output)-2][:l])
"""
			# Debug output
			consoleHelper.printRippoppaiMessage("Calculated pp: {}".format(self.pp))
		except OppaiError:
			log.error("oppai ~> oppai-ng error!")
			self.pp = 0
		except exceptions.osuApiFailException:
			log.error("oppai ~> osu!api error!")
			self.pp = 0
		except exceptions.unsupportedGameModeException:
			log.error("oppai ~> Unsupported gamemode")
			self.pp = 0
		except Exception as e:
			log.error("oppai ~> Unhandled exception: {}".format(str(e)))
			self.pp = 0
			raise

		finally:
			log.debug("oppai ~> Shutting down, pp = {}".format(self.pp))
