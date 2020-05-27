# Unifi IPsec Updater

[![Build Status](https://travis-ci.org/troywilson/unifi-ipsec-updater.svg?branch=master)](https://travis-ci.org/troywilson/unifi-ipsec-updater) [![Docker Pulls](https://img.shields.io/docker/pulls/troywilson/unifi-ipsec-updater.svg)](https://hub.docker.com/r/troywilson/unifi-ipsec-updater/) [![Apache V2 License](https://img.shields.io/badge/license-Apache%20V2-blue.svg)](https://github.com/troywilson/unifi-ipsec-updater/blob/master/LICENSE)

The strongSwan install on Unifi Gateways doesn't allow DNS entries for IPsec peering. This image gets around this restriction by querying DNS records to update a site-to-site IPsec VPN on the controller.

## Installation

1. Configure your DNS provider with A records pointing to each end of the IPsec tunnels' external IP addresses. If you only need 1 IP address to be updated that will work too.

2. Create a site-to-site VPN on the Unifi controller.

3. Optionally, create a service account on the Unifi controller that has read/write access to the network configuration.

4. Find the docker image at: [troywilson/unifi-ipsec-updater](https://hub.docker.com/r/troywilson/unifi-ipsec-updater)

```
docker run --name unifi-ipsec-updater --restart=always --detach \
  -e "HOST=unifi" \
  -e "PORT=8443" \
  -e "USERNAME=admin" \
  -e "PASSWORD=changeme" \
  -e "SITE=default" \
  -e "NETWORK=my-network-name" \
  -e "LOCAL-DNS=local.example.com" \
  -e "PEER-DNS=peer.example.com" \
  -e "INTERVAL=60" \
  -e "ONCE=False" \
  -e "LOG-LEVEL=INFO" \
  troywilson/unifi-ipsec-updater:latest
```

## ENV Settings

| Setting | Default | Type | Description |
| --- | --- | --- | --- |
| HOST | unifi | string | host(name/IP) for the controller |
| PORT | 8443 | integer | port of the controller |
| USERNAME | admin | string | username for the controller |
| PASSWORD | None | string | password for the controller |
| SITE | default | string | the site name on the controller |
| NETWORK | None | string| the VPN network name to update |
| LOCAL-DNS | None | string | the DNS record to lookup for the local gateway |
| PEER-DNS | None | string | the DNS record to lookup for the peer gateway |
| INTERVAL | 60 | integer | interval in seconds between lookups |
| ONCE | False | boolean | only run the update once and exit |
| LOG-LEVEL | INFO | [DEBUG INFO WARNING ERROR CRITICAL] | logging level |

### Secrets

If any of the above settings values start with "FILE_" the image will open the file listed after the "FILE_" prefix and replace the setting with the contents of the file.

```
docker run --name unifi-ipsec-updater --restart=always --detach \
  -e "USERNAME=admin" \
  -e "PASSWORD=FILE_/run/secrets/password" \
  -e "NETWORK=my-network-name" \
  -e "LOCAL-DNS=local.example.com" \
  -e "PEER-DNS=peer.example.com" \
  troywilson/unifi-ipsec-updater:latest
```

## Warning

While this image works for my needs, it has not been tested throughly and may break stuff. **Use at your own risk**.
