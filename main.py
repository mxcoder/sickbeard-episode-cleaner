#!/usr/bin/python
import os
import time
import json
import glob
import logging
import argparse
import urllib
from operator import itemgetter

DEBUG = False
CONFIG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
LOG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'logger.log')

parser = argparse.ArgumentParser(description="Script to remove Sickbeard episodes using threshold on downloaded or wiping archived episodes")
parser.add_argument("-d", "--debug", action="store_true", help="No action performed on files or database, verbose logging to stdout")
parser.add_argument("-c", "--config", type=argparse.FileType('r'), help="Custom configuration json file")
parser.add_argument("--tvdbid-forced", help="Sickbeard Show ID (tvdbid) to force operations on one show")
parser.add_argument("full_path", nargs="?")
parser.add_argument("original_name", nargs="?")
parser.add_argument("tvdbid", nargs="?")
parser.add_argument("season", nargs="?")
parser.add_argument("episode", nargs="?")
parser.add_argument("air_date", nargs="?")
args = parser.parse_args()

# debugging
if args.debug:
	DEBUG = args.debug

# configure logging
logger = logging.getLogger()
logger.setLevel( logging.DEBUG )
if DEBUG:
	lh = logging.StreamHandler()
else:
	lh = logging.FileHandler( LOG_FILE )
lh.setFormatter( logging.Formatter('%(asctime)s %(message)s') )
logger.addHandler( lh )

if args.tvdbid_forced:
	TVDBID = args.tvdbid_forced
elif args.tvdbid:
	TVDBID = args.tvdbid
else:
	logger.info( "No TV ID specified" )
	raise SystemExit

if args.config:
	CONFIG_FILE = args.config
elif os.path.isfile(CONFIG_FILE):
	CONFIG_FILE = open(CONFIG_FILE, 'r')
else:
	logger.info( "No config.json file found" )
	raise SystemExit

try:
	config = json.load(CONFIG_FILE)
except ValueError:
	logger.info( "Decoding config.json failed" )
	raise SystemExit

GLOBAL_REMOVE = (config.get('global',{})).get('remove', 'ALL')
REMOVE_ARCHIVED = (GLOBAL_REMOVE == 'ALL' or GLOBAL_REMOVE == 'ARCHIVED')
REMOVE_DOWNLOADED = (GLOBAL_REMOVE == 'ALL' or GLOBAL_REMOVE == 'DOWNLOADED')
if DEBUG:
	logger.info( "DEBUG: Global removal switches, Archived=%s, Downloaded=%s" % (REMOVE_ARCHIVED, REMOVE_DOWNLOADED) )

# make a SB api call
def sb_request( params ):
	server = config.get('server', {})
	query = urllib.urlencode(params)
	url = "http://%s:%s%s/api/%s/?%s" % (server.get('hostname', 'localhost'), server.get('port', "8081"), server.get("web_root"), server.get('api_key', "REQUIRED-GENERATED-API-KEY"), query)
	return json.loads( urllib.urlopen(url).read().decode('utf-8') )

# delete files associated with an episode
def delete_episode( showid, season, episode ):
	# get the filename
	params = {'cmd': 'episode', 'tvdbid': showid, 'season': season, 'episode': episode, 'full_path': 1}
	episode_json = sb_request(params)
	filename = episode_json['data']['location']

	# delete the episode from disk
	logger.info( "cleaning: S%sE%s" % (season, episode) )
	name, ext = os.path.splitext( filename )

	for f in glob.glob(name + "*"):
		logger.info( "Delete file: %s" % f )
		if not DEBUG:
			os.remove( f )
		else:
			logger.info( "DEBUG: Deleted file: %s" % f )

	# update episode status in SB
	if not DEBUG:
		params = {'cmd': 'episode.setstatus', 'tvdbid': showid, 'season': season, 'episode': episode, 'status': 'ignored', 'force': 1}
		status_json = sb_request( params )
	else:
		logger.info( "DEBUG: S%sE%s update status: OK" % (season, episode) )

def process_episode( showid ):
	# get config
	shows_config = config.get('shows', {})
	show_config = shows_config.get(showid, {})
	show_name = show_config.get('name', 'N/A Name')
	show_remove = show_config.get('remove', 'ALL');
	if not show_config:
		logger.info( "Unconfigured show %s: %s" % (showid, show_name) )
		return

	# get episodes
	if DEBUG:
		logger.info( "DEBUG: Reading show: %s - %s" % (showid, show_name) )
	params = {'cmd': 'show.seasons', 'tvdbid': showid}
	episodes_json = sb_request(params)
	if not episodes_json:
		logger.info( "Can't find show with tvdbid: %s" % showid )
		return

	# skip 'specials'
	if '0' in episodes_json['data']:
		del episodes_json['data']['0']

	# find episodes that have been downloaded
	downloaded_episodes = []
	archived_episodes = []

	for season_key, season in episodes_json['data'].items():
		for episode_key, episode in season.items():
			if episode['status'] == 'Downloaded':
				downloaded_episodes.append( [int(season_key), int(episode_key)] )
			elif episode['status'] == 'Archived':
				archived_episodes.append( [int(season_key), int(episode_key)] )
	
	# delete all archived episodes
	logger.info( "Show %s: Found %s archived episodes" % (showid, len(archived_episodes)) )
	if (REMOVE_ARCHIVED and (show_remove == 'ALL' or show_remove == 'ARCHIVED')):
		logger.info( "Show %s: Deleting %s archived episodes" % (showid, len(archived_episodes)) )
		while archived_episodes:
			curr_season, curr_episode = archived_episodes.pop(0)
			delete_episode( showid, curr_season, curr_episode )
	elif (not REMOVE_ARCHIVED or show_remove == 'NONE'):
		logger.info( "Show %s: %s" % (showid, "Archived episodes won't be deleted") )	
	else:
		logger.info( "Show %s: %s" % (showid, "No archived episodes to delete") )

	# sort episodes by season, episode number
	logger.info( "Show %s: Found %s downloaded episodes" % (showid, len(downloaded_episodes)) )
	if REMOVE_DOWNLOADED and (show_remove == 'ALL' or show_remove == 'DOWNLOADED') and len(downloaded_episodes) > show_config['keep_episodes']:
		logger.info( "Show %s: Deleting %s downloaded episodes" % (showid, len(downloaded_episodes) - show_config['keep_episodes']) )
		downloaded_episodes = sorted( downloaded_episodes, key=itemgetter(0,1) )
		# delete oldest episodes until we are within the threshold of episodes to keep
		while len(downloaded_episodes) > show_config['keep_episodes']:
			season, episode = downloaded_episodes.pop(0)
			delete_episode( showid, season, episode )
	elif (not REMOVE_DOWNLOADED or show_remove == 'NONE'):
		logger.info( "Show %s: %s" % (showid, "Downloaded episodes won't be deleted") )	
	else:
		logger.info( "Show %s: %s" % (showid, "No downloaded episodes to delete") )

	# tell sickbeard to rescan local files
	if not DEBUG:
		params = {'cmd': 'show.refresh', 'tvdbid': showid}
		refresh_json = sb_request( params )
	else:
		logger.info( "%s: %s" % (showid, "DEBUG: Refreshing show") )


if __name__ == '__main__':
	# see if we are supposed to process this show
	if TVDBID in config['shows']:
		process_episode( TVDBID )
	else:
		logger.info( "Show not found in the config.json" )

