import tornado.gen
import tornado.web
import requests

from common.web import requestsManager
from constants import exceptions
from common.sentry import sentry
from helpers import levbodHelper

MODULE_NAME = "direct"
class handler(requestsManager.asyncRequestHandler):
	"""
	Handler for /web/osu-search.php
	"""
	@tornado.web.asynchronous
	@tornado.gen.engine
	@sentry.captureTornado
	def asyncGet(self):
		output = ""
		try:
			gameMode = self.get_argument("m", "-1")
			rankedStatus = self.get_argument("r", "-1")
			query = self.get_argument("q", "")
			page = int(self.get_argument("p", "0"))
			if query.lower() in ["newest", "top rated", "most played"]:
				query = ""

			response = requests.get("https://osu.gatari.pw/api/v1/beatmaps/search?r={0}&q={1}&m={2}&p={3}".format(rankedStatus,query,gameMode,page))
			output += response.text
		finally:
			self.write(output)