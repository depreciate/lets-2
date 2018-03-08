import time
import threading
import json

from objects import glob
from common.log import logUtils as log
from helpers import osuapiHelper
from objects import beatmap
from constants import rankedStatuses

class BeatmapUpdater:
	def __init__(self, time=60):
		self.time = time
		self.stats = {
		"updated" : 0,
		"total" : 0
		}
		self.UpdateBeatmap()
		self.UpdateQualif()
		self.UpdateWrongDiff()
		
	def UpdateWrongDiff(self):
		bm = glob.db.fetch("SELECT beatmap_id,ranked, latest_update, beatmapset_id, beatmap_md5  FROM beatmaps WHERE mode = 0 AND difficulty_std = 0 AND hit_length>30 ORDER BY latest_update DESC LIMIT 1")
		if bm is not None:
			bmap = beatmap.beatmap(bm["beatmap_md5"], bm["beatmapset_id"], refresh=True)
			if(bmap.rankedStatus == rankedStatuses.NEED_UPDATE or bmap.rankedStatus < rankedStatuses.PENDING):
				self.stats["updated"] += 1
			self.stats["total"] += 1
		threading.Timer(15, self.UpdateWrongDiff).start()
		return

	def UpdateQualif(self):
		bm = glob.db.fetch("SELECT beatmap_id,ranked, latest_update, beatmapset_id, beatmap_md5 FROM beatmaps WHERE ranked = 4 ORDER BY latest_update ASC LIMIT 1")
		if bm is not None:
			bmap = beatmap.beatmap(bm["beatmap_md5"], bm["beatmapset_id"], refresh=True)
			if(bmap.rankedStatus == rankedStatuses.NEED_UPDATE or bmap.rankedStatus < rankedStatuses.PENDING):
				self.stats["updated"] += 1
			self.stats["total"] += 1
		threading.Timer(self.time, self.UpdateQualif).start()
		return

	def UpdateBeatmap(self):
		bm = glob.db.fetch("SELECT beatmap_id,ranked, latest_update, beatmapset_id, beatmap_md5 FROM beatmaps  WHERE ((ranked > 3 or ranked_status_freezed > 0) AND latest_update < %s) ORDER BY latest_update ASC LIMIT 1",[time.time() - 36400])
		if bm is not None:
			bmap = beatmap.beatmap(bm["beatmap_md5"], bm["beatmapset_id"], refresh=True)
			if(bmap.rankedStatus == rankedStatuses.NEED_UPDATE or bmap.rankedStatus < rankedStatuses.PENDING):
				self.stats["updated"] += 1
			self.stats["total"] += 1
		threading.Timer(self.time, self.UpdateBeatmap).start()
		return 
	def PrintStats(self, init = False):
		if(init == False):
			message = "Устаревших карт за последние 24 часа: {} из {} проверенных".format(self.stats["updated"],self.stats["total"])
			glob.redis.publish("hax:warrning", json.dumps({
			"message":"[BmUpdaterStats] "+message
			}))
			self.stats = {
			"updated" : 0,
			"total" : 0
			}	
		threading.Timer(86400, self.PrintStats).start()
		return 