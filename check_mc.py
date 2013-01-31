#!/usr/bin/python
import re, argparse, json, sys, os, mmap, time

parser = argparse.ArgumentParser(
    description='Process minecraft server logs for health info',
    epilog='Exit code is: 2 if no hearthbeat is found, 1 is a bad line is found, 0 if a good line or no bad lines and a heartbeat is found',
    fromfile_prefix_chars='@'
    )
parser.add_argument('logfile',type=argparse.FileType('r'),help='the logfile to process')
parser.add_argument('--ignore', action='store', nargs='*',default=[],help='lines to ignore')
parser.add_argument('--good', action='store', nargs='*',default=[],help='Immediately return 0 if one of these is found (server restart)')
parser.add_argument('--bad', action='store', nargs='*',default=[],help='Reuire none of these regex to return 0 (exception watcher)')
parser.add_argument('--hearthbeat', action='store', nargs='*',default=[],help='Require one of these regex to return 0 (to ensure no deadlocks)')
parser.add_argument('--searchwindow', action='store',type=int, default=5*60,help='Seconds it should search back in the log (default 5min)')
parser.add_argument('--timesplit', action='store', default='(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) (.*)',help=argparse.SUPPRESS)
parser.add_argument('--timeformat', action='store', default='%Y-%m-%d %H:%M:%S',help=argparse.SUPPRESS)

options = parser.parse_args()

timesplitter = re.compile(options.timesplit)

def reverse_lines(inputfile):
	data = mmap.mmap(inputfile.fileno(),0,access=mmap.ACCESS_READ)
	index = len(data)-1
	while index > 0:
		#TODO: limit max line size
		newindex = data.rfind('\n',0,index)
		yield data[newindex+1:index]
		index = newindex

stoptime = time.time() - options.searchwindow

regex_hearthbeat = map(re.compile,options.hearthbeat)
regex_good = map(re.compile,options.good)
regex_bad = map(re.compile,options.bad)
regex_ignore = map(re.compile,options.ignore)

def any_match(regexes,line):
	for regex in regexes:
		if regex.search(line):
			return True
	return False


def find_health(logfile):
	retval = 2 if regex_hearthbeat else 0
	for line in reverse_lines(logfile):
		result = timesplitter.match(line)
		if result:
			timestamp_string, line = result.groups()
			timestamp = time.mktime(time.strptime(timestamp_string,options.timeformat))
			if timestamp <= stoptime:
				return retval
		if any_match(regex_ignore,line):
			continue
		if any_match(regex_good,line):
			return 0
		if any_match(regex_hearthbeat,line):
			retval = 0
		if any_match(regex_bad,line):
			return 1
	return retval

exit(find_health(options.logfile))
	