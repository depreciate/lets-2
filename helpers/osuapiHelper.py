import json
import random
from urllib.parse import quote
import requests.auth

import requests

from common.log import logUtils as log
from common import generalUtils
from objects import glob
from constants import exceptions

def osuApiRequest(request, params, getFirst=True):
	"""
	Send a request to osu!api.

	request -- request type, string (es: get_beatmaps)
	params -- GET parameters, without api key or trailing ?/& (es: h=a5b99395a42bd55bc5eb1d2411cbdf8b&limit=10)
	return -- dictionary with json response if success, None if failed or empty response.
	"""
	# Make sure osuapi is enabled
	if not generalUtils.stringToBool(glob.conf.config["osuapi"]["enable"]):
		log.warning("osu!api is disabled")
		return None

	# Api request
	resp = None
	try:

		#proxies = {"https": "https://"}
		finalURL = "{}/api/{}?k={}&{}".format(glob.conf.config["osuapi"]["apiurl"], request, random.choice(["60cf2fa07293511a9d7a8eb54544de7e0a8f687b","2a1d6adde543badbf3d3430fadca15730b7cb1bd","eaff68a8f9e565deadfb6cf3ecda7187dc5fa139","72f5c9a004c0de5b1cc465742fc66dd6bfc25fb5","ad10649c1e71221de38c3a6d2245b1276e7c38a5", "2a6d00bc2444281b89c67726f361185b54bd0425","cf3fd4097091b0b1dc8105b4469fec84c38a4d2b","8c2ef88410a587ca8b17c2233751c094a50bd9ea"]), params)
		log.debug(finalURL)
		#resp = requests.get(finalURL, timeout=25, proxies=proxies).text
		resp = requests.get(finalURL, timeout=15).text
		if resp is None:
			return "timeout" 
		data = json.loads(resp)
		if getFirst:
			if len(data) >= 1:
				resp = data[0]
			else:
				resp = None
		else:
			resp = data
	except Exception:
		return "timeout"
	finally:
		glob.dog.increment(glob.DATADOG_PREFIX+".osu_api.requests")
		return resp

def getOsuFileFromName(fileName):
	"""
	Send a request to osu! servers to download a .osu file from file name
	Used to update beatmaps

	fileName -- .osu file name to download
	return -- .osu file content if success, None if failed
	"""
	# Make sure osuapi is enabled
	proxies = random.choice ([{"https": "https://quCSK5:4zgJze@217.29.53.105:23879"}, {"https": "https://quCSK5:4zgJze@217.29.53.105:23879"}, {"https": "https://quCSK5:4zgJze@217.29.53.105:23877"}, {"https": "https://quCSK5:4zgJze@217.29.53.105:23878"}]) 
	if not generalUtils.stringToBool(glob.conf.config["osuapi"]["enable"]):
		print("osuapi is disabled")
		return None

	response = None
	try:
		URL = "{}/web/maps/{}".format(glob.conf.config["osuapi"]["apiurl"], quote(fileName))
		req = requests.get(URL, timeout=20, proxies=proxies)
		req.encoding = "utf-8"
		response = req.text
	finally:
		glob.dog.increment(glob.DATADOG_PREFIX+".osu_api.osu_file_requests")
		return response

def getOsuFileFromID(beatmapID):
	"""
	Send a request to osu! servers to download a .osu file from beatmap ID
	Used to get .osu files for oppai

	beatmapID -- ID of beatmap (not beatmapset) to download
	return -- .osu file content if success, None if failed
	"""
	# Make sure osuapi is enabled
	proxies = random.choice ([{"https": "https://quCSK5:4zgJze@217.29.53.105:23879"}, {"https": "https://quCSK5:4zgJze@217.29.53.105:23879"}, {"https": "https://quCSK5:4zgJze@217.29.53.105:23877"}, {"https": "https://quCSK5:4zgJze@217.29.53.105:23878"}]) 
	if not generalUtils.stringToBool(glob.conf.config["osuapi"]["enable"]):
		print("osuapi is disabled")
		return None

	response = None
	try:
		URL = "{}/osu/{}".format(glob.conf.config["osuapi"]["apiurl"], beatmapID)
		response = requests.get(URL, timeout=20, proxies=proxies).text
	finally:
		glob.dog.increment(glob.DATADOG_PREFIX+".osu_api.osu_file_requests")
		return response