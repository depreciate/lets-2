import os
import sys
import traceback

import tornado.gen
import tornado.web
from raven.contrib.tornado import SentryMixin

from common.constants import privileges
from common.log import logUtils as log
from common.ripple import userUtils
from common.web import requestsManager
from constants import exceptions
from common import generalUtils
from objects import glob
from common.sentry import sentry

MODULE_NAME = "get_trace"
class handler(requestsManager.asyncRequestHandler):
	"""
	Handler for osu-getreplay.php
	"""
	@tornado.web.asynchronous
	@tornado.gen.engine
	@sentry.captureTornado
	def asyncGet(self):
		try:
			# Get request ip
			ip = self.getRequestIP()

			# Check arguments
			if not requestsManager.checkArguments(self.request.arguments, ["c", "k"]):
				raise exceptions.invalidArgumentsException(MODULE_NAME)

			# Get arguments
			key = self.get_argument("k")
			targetID = self.get_argument("c")

			if key is None or key != generalUtils.stringMd5(glob.conf.config["server"]["apikey"]):
				raise exceptions.invalidArgumentsException(MODULE_NAME)

			targetUsername = userUtils.getUsername(targetID)
			if(targetUsername is None):
				raise exceptions.invalidArgumentsException(MODULE_NAME)

			# Serve replay
			log.info("Serving {}.txt".format(targetUsername))
			fileName = ".data/pl/{}.txt".format(targetUsername)
			if os.path.isfile(fileName):
				with open(fileName, "rb") as f:
					fileContent = f.read()
				self.write(fileContent)
				self.set_header("Content-length", len(fileContent))
				self.set_header("Content-Description", "File Transfer")
				self.set_header("Content-Disposition", "attachment; filename=\"{}_trace.txt\"".format(targetUsername))
			else:
				log.warning("Trace {} doesn't exist".format(targetUsername))
				self.write("")
		except exceptions.invalidArgumentsException:
			pass
		except exceptions.loginFailedException:
			pass