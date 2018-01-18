import tornado.gen
import tornado.web
import requests

from common.web import requestsManager
from constants import exceptions
from common.sentry import sentry
from helpers import levbodHelper

MODULE_NAME = "direct_np"
class handler(requestsManager.asyncRequestHandler):
	"""
	Handler for /web/osu-search-set.php
	"""
	@tornado.web.asynchronous
	@tornado.gen.engine
	@sentry.captureTornado
	def asyncGet(self):
		output = ""
		try:
			# Get data by beatmap id or beatmapset id
			if "b" in self.request.arguments:
				response = requests.get("https://osu.gatari.pw/api/v1/beatmaps/searchset?b={}".format(self.get_argument("b")))
			elif "s" in self.request.arguments:
				response = requests.get("https://osu.gatari.pw/api/v1/beatmaps/searchset?s={}".format(self.get_argument("s")))
			else:
				return
			output += response.text
		finally:
			self.write(output)