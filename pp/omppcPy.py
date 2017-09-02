import os
from pp import omppc

from common import generalUtils
from common.constants import bcolors
from common.ripple import scoreUtils
from constants import exceptions
from helpers import consoleHelper
from helpers import osuapiHelper

# constants
MODULE_NAME = "omppcPy"
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

class piano:
	"""
	Oppai calculator
	"""
	# Folder where oppai is placed
	OPPAI_FOLDER = "../lets/omppc"

	def __init__(self, __beatmap, __score = None, acc = 0, mods = 0):
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
		self.beatmap = __beatmap
		self.map = "{}.osu".format(self.beatmap.beatmapID)

		if __score is not None:
			self.score = __score
			self.acc = self.score.accuracy*100
			self.mods = self.score.mods

		self.getPP()

	def getPP(self):
		"""
		Calculate total pp value with oppai and return it

		return -- total pp
		"""
		# Set variables
		self.pp = 0
		try:
			# Build .osu map file path
			mapFile = "/oppai/maps/{map}".format(map=self.map)

			try:
				# Check if we have to download the .osu file
				download = False
				if not os.path.isfile(mapFile):
					# .osu file doesn't exist. We must download it
					consoleHelper.printColored("[!] {} doesn't exist".format(mapFile), bcolors.YELLOW)
					download = True
				else:
					# File exists, check md5
					if generalUtils.fileMd5(mapFile) != self.beatmap.fileMD5:
						# MD5 don't match, redownload .osu file
						consoleHelper.printColored("[!] Beatmaps md5 don't match", bcolors.YELLOW)
						download = True

				# Download .osu file if needed
				if download:
					consoleHelper.printRippoppaiMessage("Downloading {} from osu! servers...".format(self.beatmap.beatmapID))

					# Get .osu file from osu servers
					fileContent = osuapiHelper.getOsuFileFromID(self.beatmap.beatmapID)

					# Make sure osu servers returned something
					if fileContent is None:
						raise exceptions.osuApiFailException(MODULE_NAME)

					# Delete old .osu file if it exists
					if os.path.isfile(mapFile):
						os.remove(mapFile)

					# Save .osu file
					with open(mapFile, "wb+") as f:
						f.write(fileContent.encode("latin-1"))
				else:
					# Map file is already in folder
					consoleHelper.printRippoppaiMessage("Found beatmap file {}".format(mapFile))
			except Exception:
				pass

			# Base command

			calc = omppc.Calculator(mapFile, score=self.score.score, mods=self.mods, accuracy=self.acc)
			pp = calc.calculate_pp()[0]
			consoleHelper.printRippoppaiMessage("calculated pp {}".format(pp))
			self.pp = pp
		finally:
			return self.pp
