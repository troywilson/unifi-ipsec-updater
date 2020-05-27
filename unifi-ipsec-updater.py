#!/usr/bin/env python

import argparse
import dns.resolver
import logging
import os
import sched
import time
import unificontrol

__author__ = 'Troy Wilson'
__version__ = '0.1.1'

# setup args
parser = argparse.ArgumentParser()
parser.add_argument('--host', default=os.environ.get('HOST', 'unifi'),
	help='host(name/ip) for the controller (default "unifi")')
parser.add_argument('--port', default=os.environ.get('PORT', 8443), type=int,
	help='port of the controller (default "8443")')
parser.add_argument('--username', default=os.environ.get('USERNAME', 'admin'),
	help='username for the controller (default "admin")')
parser.add_argument('--password', default=os.environ.get('PASSWORD'),
	help='password for the controller')
parser.add_argument('--site', default=os.environ.get('SITE', 'default'),
	help='the site on the controller (default "default")')
parser.add_argument('--network', default=os.environ.get('NETWORK'),
	help='the VPN network to update')
parser.add_argument('--local-dns', default=os.environ.get('LOCAL-DNS'),
	help='the DNS record to lookup for the local gateway')
parser.add_argument('--peer-dns', default=os.environ.get('PEER-DNS'),
	help='the DNS record to lookup for the peer gateway')
parser.add_argument('--interval', default=os.environ.get('INTERVAL', 60), type=int,
	help='interval in seconds between lookups (default 60)')
parser.add_argument('--once', default=os.environ.get('ONCE', False), type=bool,
	help='only run the update once and exit (default False)')
parser.add_argument('--log-level', default=os.environ.get('LOG-LEVEL', 'INFO'),
	choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
	help='logging level (default INFO)')
args = vars(parser.parse_args())

# setup logging
log_num = args.get('log_level', 'INFO')
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=log_num)

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
				logging.warning('File: %s could not be read for argument: %s', filename, arg_name)
		else:
			logging.warning('No filename supplied for argument: %s', arg_name)

# setup scheduler
s = sched.scheduler(time.time, time.sleep)

def updater(sc):
	# lookup DNS entries
	dnsIP = {'local': None, 'peer': None}

	logging.debug('Local DNS to lookup: %s', args.get('local_dns'))
	if args.get('local_dns'):
		try:
			dnsIP['local'] = dns.resolver.query(args.get('local_dns'), 'A')[0].to_text()
		except:
			logging.warning('DNS A record: %s could not be retrieved', args.get('local_dns'))
	logging.debug('Local IP address from DNS: %s', dnsIP['local'])

	logging.debug('Peer DNS to lookup: %s', args.get('local_dns'))
	if args.get('peer_dns'):
		try:
			dnsIP['peer'] = dns.resolver.query(args.get('peer_dns'), 'A')[0].to_text()
		except:
			logging.warning('DNS A record: %s could not be retrieved', args.get('peer_dns'))
	logging.debug('Peer IP address from DNS: %s', dnsIP['local'])

	# connect to controller
	client = None

	try:
		client = unificontrol.UnifiClient(host=args.get('host'),
			port=args.get('port'), username=args.get('username'),
			password=args.get('password'), site=args.get('site'))
	except:
		logging.warning('No controller found at: %s:%s', args.get('host'), args.get('port'))

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
		except unificontrol.exceptions.UnifiLoginError:
			logging.warning('Login to the controller failed')
		except:
			logging.warning('Could not retrieve network: %s from controller', args.get('network'))

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
					logging.warning('Error burning update to network: %s', args.get('network'))
				else:
					if change_local:
						logging.info('%s(local): %s => %s', args.get('network'),
							gwIP['local'], dnsIP['local'])

					if change_peer:
						logging.info('%s(peer): %s => %s', args.get('network'),
							gwIP['peer'], dnsIP['peer'])
			else:
				logging.info('No changes')

	# re-schedule
	if not args.get('once'):
		s.enter(args.get('interval'), 1, updater, (sc,))

# start
updater(s)

# schedule
if not args.get('once'):
	s.run()
