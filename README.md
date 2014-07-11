# Sickbeard Episode Cleaner

A post processing script for Sickbeard that allows you to set the number of episodes of a show that you would like to keep. Useful for shows that air daily.

The script sorts the episodes you have for a show by the season and episode number, and then deletes the oldest episodes past the threshold you set.

## How to use - common

1. Clone the repository
``` git clone https://github.com/spoatacus/sickbeard-episode-cleaner.git ```
2. Change owner to your Sickbeard user
``` chown -R sickbeard.sickbeard sickbeard-episode-cleaner ```
3. Make main.py executable by your Sickbeard user
``` chmod ug+x sickbeard-episode-cleaner/main.py ```
4. Configure the script. See section below for details.

## How to use with Sickbeard extra-scripts

1. Configure Sickbeard to use the script
    - Stop Sickbeard
    - Edit Sickbeard's config.ini
    - Add the full path of sickbeard-episode-cleaner/main.py to the extra_scripts setting (under [General])
    - Start Sickbeard

## How to use from command line

```
usage: main.py [-h] [-d] [-c CONFIG] [--tvdbid-forced TVDBID_FORCED]
               [full_path] [original_name] [tvdbid] [season] [episode]
               [air_date]

Script to remove Sickbeard episodes using threshold on downloaded or wiping
archived episodes

positional arguments:
  full_path
  original_name
  tvdbid
  season
  episode
  air_date

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           No action performed on files or database, verbose
                        logging to stdout
  -c CONFIG, --config CONFIG
                        Custom configuration json file
  --tvdbid-forced TVDBID_FORCED
                        Sickbeard Show ID (tvdbid) to force operations on one
                        show
```

- Force operations on a single Show
``` main.py [-d|--debug] [-c|--config config.json] --tvdbid-force 12345 ```

- Using Sickbeard extra-script call: http://code.google.com/p/sickbeard/wiki/AdvancedSettings


## Configuration

Configuration is pretty straight forward as this sample config file shows. The keys under shows are the tvdb id's for the shows you want to clean.

There is a sample config included. Just move it to config.json.
``` mv sickbeard-episode-cleaner/config.json.sample sickbeard-episode-cleaner/config.json ```

```json
{
	"global": {
		"remove": "ALL" // (ALL or DOWNLOADED or ARCHIVED or NONE, default ALL)
	},
	"server": {
		"hostname": "localhost", // default localhost
		"port": "8081", // default 8081
		"web_root": "", // default empty
		"api_key": "REQUIRED-GENERATED-API-KEY" // default
	},
	"shows": {
		"12345": {
			"name": "Some show", // (Informative only, doesn't need to comply with DB)
			"keep_episodes": 3, // Positive integer
			"remove": "ALL" // (ALL or DOWNLOADED or ARCHIVED or NONE, default ALL)
		},
		... // add more dict entries
	}
}
```

# TODO

- Populate config.json from sickbeard database
- Allow running on ALL shows
- Allow custom log file
