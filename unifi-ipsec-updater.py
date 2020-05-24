#!/usr/bin/env python

import argparse
import dns.resolver
import os
import sched
import time
import unificontrol

__author__ = 'Troy Wilson'
__version__ = '0.01'

# setup args
parser = argparse.ArgumentParser()
parser.add_argument('--host', default=os.environ.get('HOST', 'unifi'), help='host(name/ip) for the controller (default "unifi")')
parser.add_argument('--port', default=os.environ.get('PORT', '8443'), help='port of the controller (default "8443")')
parser.add_argument('--username', default=os.environ.get('USERNAME', 'admin'), help='username for the controller (default "admin")')
parser.add_argument('--password', default=os.environ.get('PASSWORD'), help='password for the controller')
parser.add_argument('--site', default=os.environ.get('SITE', 'default'), help='the site on the controller (default "default")')
parser.add_argument('--network', default=os.environ.get('NETWORK'), help='the VPN network to update')
parser.add_argument('--local-dns', default=os.environ.get('LOCAL-DNS'), help='the DNS record to lookup for the local gateway')
parser.add_argument('--peer-dns', default=os.environ.get('PEER-DNS'), help='the DNS record to lookup for the peer gateway')
parser.add_argument('--interval', default=os.environ.get('INTERVAL', 60), help='interval in seconds between lookups (default 60)')
parser.add_argument('--once', default=os.environ.get('ONCE', False), help='only run the update once and exit (default False)')
args = vars(parser.parse_args())

# read settings from file
file_prefix = 'FILE_'
for arg_name,arg_value in args.items():
	if isinstance(arg_value, str) and arg_value.startswith(file_prefix):
		if len(arg_value) > len(file_prefix):
			filename = arg_value[len(file_prefix):]
			try:
				with open(filename) as f:
					args[arg_name] = f.read().rstrip(os.linesep)
			except:
				print(f"File: {filename} could not be read for argument: {arg_name}")
		else:
			print(f"No filename supplied for argument: {arg_name}")

# setup scheduler
s = sched.scheduler(time.time, time.sleep)

def updater(sc):
	# lookup DNS entries
	dnsIP = {'local': None, 'peer': None}

	try:
		dnsIP['local'] = dns.resolver.query(args.get('local_dns'), 'A')[0].to_text()
	except:
		print(f"DNS A record: {args.get('local_dns')} could not be retrieved")

	try:
		dnsIP['peer'] = dns.resolver.query(args.get('peer_dns'), 'A')[0].to_text()
	except:
		print(f"DNS A record: {args.get('peer_dns')} could not be retrieved")

	# connect to controller
	client = None

	try:
		client = unificontrol.UnifiClient(host=args.get('host'),
			port=args.get('port'), username=args.get('username'),
			password=args.get('password'), site=args.get('site'))
	except:
		print(f"No controller found at: {args.get('host')}:{args.get('port')}")

	# retrieve current network settings
	unifi_settings = None
	gwIP = {'local': None, 'peer': None}

	if client:
		try:
			for net in client.list_networkconf():
				if net.get('name', None) == args.get('network'):
					unifi_settings = net
			gwIP['local'] = unifi_settings.get('ipsec_local_ip', None)
			gwIP['peer'] = unifi_settings.get('ipsec_peer_ip', None)
		except:
			print(f"Could not retrieve network: {args.get('network')} from controller")

		if unifi_settings:
			# remove id from update set
			unifi_net_id = unifi_settings.pop('_id', None)

			# check for local ip change
			change_local = False
			if gwIP['local'] != dnsIP['local'] and dnsIP['local']:
				unifi_settings['ipsec_local_ip'] = dnsIP['local']
				change_local = True

			# check for peer ip change
			change_peer = False
			if gwIP['peer'] != dnsIP['peer'] and dnsIP['peer']:
				unifi_settings['ipsec_peer_ip'] = dnsIP['peer']
				change_peer = True

			# commit change
			if change_local or change_peer:
				try:
					client.set_networksettings(unifi_net_id, unifi_settings)
				except:
					print(f"Error burning update to network: {args.get('network')}")

				if change_local:
					print(f"{args.get('network')}(local): {gwIP['local']} => {dnsIP['local']}")

				if change_peer:
					print(f"{args.get('network')}(peer): {gwIP['peer']} => {dnsIP['peer']}")
			else:
				print('No change needed')

	# re-schedule
	if not args.get('once'):
		s.enter(args.get('interval'), 1, updater, (sc,))

# start
updater(s)

# schedule
if not args.get('once'):
	s.run()
