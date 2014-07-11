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

parser = argparse.ArgumentParser(description="Script to remove Sickbeard episodes using threshold or using archived state")
parser.add_argument("-d", "--debug", action="store_true")
parser.add_argument("-c", "--config", type=argparse.FileType('r'))
parser.add_argument("--tvdbid-forced")
parser.add_argument("full_path", nargs="?")
parser.add_argument("original_name", nargs="?")
parser.add_argument("tvdbid", nargs="?")
parser.add_argument("season", nargs="?")
parser.add_argument("episode", nargs="?")
parser.add_argument("air_date", nargs="?")

args = parser.parse_args()

if args.debug:
	DEBUG = args.debug

if args.tvdbid:
	TVDBID = args.tvdbid
elif args.tvdbid_forced:
	TVDBID = args.tvdbid_forced
else:
	print "No TV ID specified"
	raise SystemExit

if args.config:
	CONFIG_FILE = args.config
elif os.path.isfile(CONFIG_FILE):
	CONFIG_FILE = open(CONFIG_FILE, 'r')
else:
	print "No config.json file found"
	raise SystemExit

try:
	config = json.load(CONFIG_FILE)
except ValueError:
	print "Decoding config.json failed"
	raise SystemExit

# configure logging
logger = logging.getLogger()
logger.setLevel( logging.DEBUG )
if DEBUG:
	lh = logging.StreamHandler()
else:
	lh = logging.FileHandler( LOG_FILE )
lh.setFormatter( logging.Formatter('%(asctime)s %(message)s') )
logger.addHandler( lh )

# make a SB api call
def sb_request( params ):
	p = urllib.urlencode(params)
	url = "http://%s:%s%s/api/%s/?%s" % (config['server']['hostname'], config['server']['port'], config['server']['web_root'], config['server']['api_key'], p)
	return json.loads( urllib.urlopen(url).read().decode('utf-8') )

# delete files associated with an episode
def delete_episode( tvdbid, season, episode ):
	# get the filename
	params = {'cmd': 'episode', 'tvdbid': tvdbid, 'season': season, 'episode': episode, 'full_path': 1}
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
		params = {'cmd': 'episode.setstatus', 'tvdbid': tvdbid, 'season': season, 'episode': episode, 'status': 'ignored', 'force': 1}
		status_json = sb_request( params )
	else:
		logger.info( "DEBUG: S%sE%s update status: OK" % (season, episode) )

def process_episode( tvdbid ):
	# get episodes
	params = {'cmd': 'show.seasons', 'tvdbid': tvdbid}
	episodes_json = sb_request(params)

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
	logger.info( "%s: Deleting %s archived episodes" % (tvdbid, len(archived_episodes)) )
	while archived_episodes:
		season, episode = archived_episodes.pop(0)
		delete_episode( tvdbid, season, episode )

	# sort episodes by season, episode number
	downloaded_episodes = sorted( downloaded_episodes, key=itemgetter(0,1) )
	logger.info( "%s: Found %s downloaded episodes" % (tvdbid, len(downloaded_episodes)) )

	# delete oldest episodes until we are within the threshold of episodes to keep
	if len(downloaded_episodes) > config['shows'][tvdbid]['keep_episodes']:
		while len(downloaded_episodes) > config['shows'][tvdbid]['keep_episodes']:
			season, episode = downloaded_episodes.pop(0)
			delete_episode( tvdbid, season, episode )
	else:
		logger.info( "%s: %s" % (tvdbid, "No downloaded episodes to delete") )

	# tell sickbeard to rescan local files
	if not DEBUG:
		params = {'cmd': 'show.refresh', 'tvdbid': tvdbid}
		refresh_json = sb_request( params )
	else:
		logger.info( "%s: %s" % (tvdbid, "DEBUG: Refreshing show") )


if __name__ == '__main__':
	# see if we are supposed to process this show
	if TVDBID in config['shows']:
		process_episode( TVDBID )
