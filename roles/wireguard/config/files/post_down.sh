#!/bin/sh
# 
# Default "PostUp" script - executed after the Wireguard interface is brought
# up. Handles the firewall (iptables) stuff that needs to be done for the serve
# to act in the "standard" role of forwarding traffic out to the internet.
# 

# Common / useful `set` commands
set -Ee # Exit on error
set -u # Error on undefined vars
# set -v # Print everything
# set -x # Print commands (with expanded vars)

if [ "$#" -lt 2 ]; then
  echo "ERROR Expected 2 arguments."
  echo
  echo "Usage:  $0 CONFIG DEV"
  echo "Like    $0 wg0 eth0"
  exit 1
fi

config="$1"
dev="$2"

iptables -D FORWARD -i "$config" -j ACCEPT
iptables -t nat -D POSTROUTING -o "$dev" -j MASQUERADE
ip6tables -D FORWARD -i "$config" -j ACCEPT
ip6tables -t nat -D POSTROUTING -o "$dev" -j MASQUERADE
