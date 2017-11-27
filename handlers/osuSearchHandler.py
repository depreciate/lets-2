import tornado.gen
import tornado.web
import requests
import re
import numpy as np

from common.ripple import userUtils
from objects import glob
from common.web import requestsManager
from constants import exceptions
from common.sentry import sentry
from helpers import levbodHelper
from objects.sqlUtils import pandasQuery, connectToDB
from common.log import logUtils as log

MODULE_NAME = "direct"

def parseBeatmapsetIdsFromDirect(directInfo):
	rows = directInfo.split('\n')[1:]
	#log.warning(rows)
	ids = [ids.split('|')[7] for ids in rows if len(ids) > 1]
	return ids

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
			if not requestsManager.checkArguments(self.request.arguments, ["u", "h"]):
				raise exceptions.invalidArgumentsException(MODULE_NAME)

			username = self.get_argument("u","")
			password = self.get_argument("h","")
			userID = userUtils.getID(username)
			if not userUtils.checkLogin(userID, password):
				raise exceptions.loginFailedException(MODULE_NAME, username)
			gameMode = self.get_argument("m", "-1")
			rankedStatus = self.get_argument("r", "-1")
			query = self.get_argument("q", "")
			page = int(self.get_argument("p", "0"))
			
			glob.db = connectToDB(1)
			
			query = query.lower()

			whereClause = []

			#stars filter
			regexp = r"stars[<>=]\d+(\*\d*)?"
			for match in re.finditer(regexp,query):
				matchStr = match.group(0)
				query = query.replace(matchStr,"")
				num = float(matchStr[6:])
				whereClause.append("difficulty_std " + matchStr[5] + " " + str(num))

			#ar filter
			regexp = r"ar[<>=]\d+(\*\d*)?"
			for match in re.finditer(regexp,query):
				matchStr = match.group(0)
				query = query.replace(matchStr,"")
				num = float(matchStr[3:])
				whereClause.append("ar " + matchStr[2] + " " + str(num))

			#cs filter
			regexp = r"cs[<>=]\d+(\*\d*)?"
			for match in re.finditer(regexp,query):
				matchStr = match.group(0)
				query = query.replace(matchStr,"")
				num = float(matchStr[3:])
				whereClause.append("cs " + matchStr[2] + " " + str(num))
			
			#max_combo
			regexp = r"combo[<>=]\d+"
			for match in re.finditer(regexp,query):
				matchStr = match.group(0)
				query = query.replace(matchStr,"")
				num = int(matchStr[6:])
				whereClause.append("max_combo " + matchStr[5] + " " + str(num))
			
			#length filter
			regexp = r"length[<>=]\d+"
			for match in re.finditer(regexp,query):
				matchStr = match.group(0)
				query = query.replace(matchStr,"")
				num = int(matchStr[7:])
				whereClause.append("hit_length " + matchStr[6] + " " + str(num))
			
			#bpm filter
			regexp = r"bpm[<>=]\d+"
			for match in re.finditer(regexp,query):
				matchStr = match.group(0)
				query = query.replace(matchStr,"")
				num = int(matchStr[4:])
				whereClause.append("bpm " + matchStr[3] + " " + str(num))
			
			if query.lower() in ["newest", "top rated", "most played"]:
				query = ""
				
			#get response from API
			response = requests.get("https://osu.gatari.pw/api/v1/beatmaps/search?r={0}&q={1}&m={2}&p={3}".format(rankedStatus,query,gameMode,page))

			if len(whereClause) > 0 and userUtils.getPrivileges(userID) & 4 > 0:
				#join with Database
				bs_ids = parseBeatmapsetIdsFromDirect(response.text)
				
				if len(bs_ids) == 0:
					return
				
				whereClause.append("beatmapset_id IN (" + ",".join(bs_ids) + ")")
				
				pandasResult = pandasQuery("select DISTINCT beatmapset_id from beatmaps WHERE " + " AND ".join(whereClause))
				
				if len(pandasResult) == 0:
					return
				
				filtered_bs_ids = np.array(pandasResult["beatmapset_id"])
				response_rows = response.text.split("\n")[1:-1]
				new_rows = [row for row in response_rows if row.split('|')[7] in list(map(str,filtered_bs_ids))]
				result = str(len(new_rows)) + "\n" + "\n".join(new_rows) + "\n"
				output += result
			else:
				output += response.text
			
		finally:
			self.write(output)