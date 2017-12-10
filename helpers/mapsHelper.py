import os

from common import generalUtils
from common.log import logUtils as log
from constants import exceptions
from helpers import osuapiHelper

def isBeatmap(fileName=None, content=None):
    if fileName is not None:
        try:
            with open(fileName, "rb") as f:
                firstLine = f.readline().decode("utf-8").strip()
        except IndexError:
            return False
    elif content is not None:
        try:
            firstLine = content.decode("utf-8").split("\n")[0].strip()
        except:
            return False
    else:
        return False
    try:
        if(firstLine[0] != "o"):
            firstLine = firstLine.lower()[1:]
    except IndexError:
        return False
    return firstLine.lower().startswith("osu file format v")

def cacheMap(mapFile, _beatmap):
    # Check if we have to download the .osu file
    download = False
    if not os.path.isfile(mapFile):
        # .osu file doesn't exist. We must download it
        download = True
    else:
        # File exists, check md5
        if generalUtils.fileMd5(mapFile) != _beatmap.fileMD5 or not isBeatmap(mapFile):
            # MD5 don't match, redownload .osu file
            log.info("beatmap md5 does not match!")
            if (_beatmap.beatmapID != 850252):
                download = True

    # Download .osu file if needed
    if download:
        log.debug("maps ~> Downloading {} osu file".format(_beatmap.beatmapID))

        # Get .osu file from osu servers
        fileContent = osuapiHelper.getOsuFileFromID(_beatmap.beatmapID)

        # Make sure osu servers returned something
        if fileContent is None or not isBeatmap(content=fileContent):
            raise exceptions.osuApiFailException(_beatmap.beatmapID)

        # Delete old .osu file if it exists
        if os.path.isfile(mapFile):
            os.remove(mapFile)

        # Save .osu file
        with open(mapFile, "wb+") as f:
            f.write(fileContent)
    else:
        # Map file is already in folder
        log.debug("maps ~> Beatmap found in cache!")