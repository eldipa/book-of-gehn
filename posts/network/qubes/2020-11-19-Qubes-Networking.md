---
layout: post
title: "Qubes OS Networking"
tags: [qubes, networking, ip, route, arp, firewall, iptables]
artifacts:
 - path.svg
---

[Qubes OS](https://www.qubes-os.org/) has an interesting network system
to isolate more-or-less
trusted *application* virtual machines (App) from absolute untrusted
*network* VMs (Net).


{{ marginfig('qubes-ips.png', indexonly=True) }}

These last ones have the drivers required to handle ethernet and wifi cards
which expose them to a potentially deathly bug lurking in the drivers.

An additional VM is put in the middle between App VMs and Net VMs. This
absolute trusted *proxy* VM serves as a safe firewall (Proxy).

In this post will explore how these VMs connect and how the packets are
forwarded up and down along this chain of VMs.<!--more-->

{% call mainfig('qubes-network.png') %}
Three App VMs: one for work, other for personal stuff, both considered
relatively-trusted and one more VM for untrusted stuff, all connected
to the "firewall" VM which forwards the packets to the Net VM.

The "firewall" VM is isolated except for
the firewall/routing processing so it is considered trusted while Net VM
is not.
{% endcall %}


## Addresses

The first obvious thing to notice is the existence of ethernet cards
both in App VM and Proxy VM.

```shell
root@appvm:# ip address show
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 00:16:3e:5e:6c:19 brd ff:ff:ff:ff:ff:ff
    inet 10.137.7.27/32 brd 10.255.255.255 scope global eth0
       valid_lft forever preferred_lft forever
```

{{ hline() }}

```shell
root@proxyvm:# ip address show
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 1000
    link/ether 00:16:3e:5e:6c:18 brd ff:ff:ff:ff:ff:ff
    inet 10.137.1.26/32 brd 10.137.1.26 scope global eth0
       valid_lft forever preferred_lft forever
4: vif37.0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP group default qlen 32
    link/ether fe:ff:ff:ff:ff:ff brd ff:ff:ff:ff:ff:ff
    inet 10.137.7.1/32 scope global vif37.0
       valid_lft forever preferred_lft forever
```

{{ marginfig('qubes-ips.png') }}

> "The virtual interfaces in client VMs are called `ethX`,
> and are provided by the `xen_netfront` kernel module, and
> the corresponding interfaces in the Net/Proxy VM are
> called `vifX.Y` and are created by the `xen_netback` module."
> <br />--[Playing with Qubes networking for fun](https://theinvisiblethings.blogspot.com/2011/09/playing-with-qubes-networking-for-fun.html)


{% call marginnotes() %}
The most-right bit of the most-left byte (`fe`) is even so it is an unicast address.

The second most-right bit of the same byte is odd so it is a locally
administrated address and it means that was arbitrary set by Qubes/Xen.
 {% endcall %}

The `ethX` links have different addresses with the same
[Xensource OUI](https://hwaddress.com/company/xensource-inc/) `00:16:3e`
while the `vifX.Y` have the same [unicast-locally
administrated](https://en.wikipedia.org/wiki/MAC_address) MAC:
`fe:ff:ff:ff:ff:ff`.


## Routing

Here a ping from the App VM is routed to the Proxy VM which
in turns routes the packet to the Net VM and the outside world
and the response goes back through the same path to the App VM

```shell
root@appvm:# ping -c 1 8.8.8.8
64 bytes from 8.8.8.8: icmp_seq=1 ttl=53 time=12.1 ms
```

{{ hline() }}

```shell
root@appvm:# tcpdump -n -i eth0
23:56:57.072295 ARP, Request who-has 10.137.7.1 tell 10.137.7.27, length 28
23:56:57.072330 ARP, Reply 10.137.7.1 is-at fe:ff:ff:ff:ff:ff, length 28
(icmp omitted)
```

{{ hline() }}

```shell
root@proxyvm:# tcpdump -n -i vif37.0
23:56:57.072295 ARP, Request who-has 10.137.7.1 tell 10.137.7.27, length 28
23:56:57.072330 ARP, Reply 10.137.7.1 is-at fe:ff:ff:ff:ff:ff, length 28
(icmp omitted)
```

{{ marginfig('qubes-arp.png') }}

The ARP request/reply is the App VM asking for the MAC address
of its configured gateway, the `10.137.7.1` which it is the IP
of the Proxy VM's `vif37.0` interface.

```shell
root@appvm:# ip route show
default via 10.137.7.1 dev eth0
10.137.7.1 dev eth0 scope link
```


{% call marginnotes() %}
You may find `REACHABLE` or `STALE`:
the first means that the entry is valid while the second
means it *was* valid.

If you are quickly enough you may see `DELAY`: the learning about the
reachability is still in progress.
 {% endcall %}

As expected, the App VM saves this in its ARP cache:

```shell
root@appvm:# ip neigh show
10.137.7.1 dev eth0 lladdr fe:ff:ff:ff:ff:ff STALE
```

{{ marginfig('qubes-first-part-ping.png') }}

Once the App VM knows the Link Layer address (aka `lladdr`), it sends
the ICMP echo request, the Proxy VM *forwards* it and forwards back
the response.

```shell
root@appvm:# tcpdump -n -i eth0
(arp omitted)
23:56:58.014156 IP 10.137.7.27 > 8.8.8.8: ICMP echo request, id 1177, seq 1, length 64
23:56:58.027402 IP 8.8.8.8 > 10.137.7.27: ICMP echo reply, id 1177, seq 1, length 64
```

{{ hline() }}

```shell
root@proxyvm:# tcpdump -n -i vif37.0
(arp omitted)
23:56:58.019581 IP 10.137.7.27 > 8.8.8.8: ICMP echo request, id 1177, seq 1, length 64
23:56:58.032679 IP 8.8.8.8 > 10.137.7.27: ICMP echo reply, id 1177, seq 1, length 64
```

## Upstream - downstream forwarding

The Proxy VM acts as a router.

```shell
root@proxyvm:# cat /proc/sys/net/ipv4/ip_forward
1
```

However the VM will *drop* all the packets before forwarding them
with some exceptions:

```shell
root@proxyvm:# iptables-save -t raw
:PREROUTING ACCEPT [116:43405]
-A PREROUTING ! -s 10.137.7.27/32 -i vif37.0 -j DROP
...

root@proxyvm:# iptables-save -t filter
:FORWARD DROP [0:0]
...
-A FORWARD -s 10.137.7.27/32 -p icmp -j ACCEPT
-A FORWARD -s 10.137.7.27/32 -j ACCEPT
```

{% call marginfig('qubes-spoofed.png') %}
The *untrusted* VM spoofs the source address simulating a message
*from the work* VM; replies will be addresses to it.

This spoofing scenario is prevented with the `PREROUTING` rules.
{% endcall %}

The `PREROUTING` rule prevents a malicious downstream VM (App VM) to send
packets to a Proxy VM (via `vif37.0`) with a spoofed source IP.


Otherwise a malicious VM could hijack the traffic of its *siblings* VMs.

>>> Proxy VM will act as a router for a particular App VM **only**
>>> for the packets coming from **that** VM.

```shell
root@proxyvm:# ip route show
default via 10.137.1.1 dev eth0 proto static metric 100
10.137.1.1 dev eth0 proto static scope link metric 100
10.137.1.26 dev eth0 proto kernel scope link src 10.137.1.26 metric 100
10.137.7.27 dev vif37.0 scope link metric 32715
```

So the incoming ICMP echo request packet with source IP `10.137.7.27`
enters from `vif37.0`, it is accepted by the firewall, routed to
`eth0` due the default route and goes out.

Before leaving the Proxy VM, the packet is slightly modified...

## NAT

The Proxy VM allows routing packets coming from its App VM: we see
this in the firewall exceptions and in the route where the
**specific** App VM IP is used, `10.137.7.27`.

But if we have more Proxy VMs chained ?

Would the second Proxy VM need the IPs of the first Proxy VM and the
App VM to setup its routes?

```shell
App VM <-> Proxy VM <-> another Proxy VM <-> ...
```

In general, any Proxy VM would need the IPs of all the downstream VMs!

That's not only tedious but also would leak information: higher VMs
would know more about the topology. A Net VM would know all the IPs
that the environment has.

However sniffing on Proxy VM's `eth0` shows something different when
the ping of App VM is forwarded:

```shell
root@proxyvm:# tcpdump -n -i eth0
(arp omitted)
23:56:58.019649 IP 10.137.1.26 > 8.8.8.8: ICMP echo request, id 1177, seq 1, length 64
23:56:58.032636 IP 8.8.8.8 > 10.137.1.26: ICMP echo reply, id 1177, seq 1, length 64
```

The source of the request is set to Proxy VM's `eth0` IP, not App VM ones.

{% call mainfig('qubes-full-ping.png') %}
Ping to 8.8.8.8 from App VM. Notice how the request is forwarded and in
each *hop* the source address is changed (NAT).

The reply takes the same path but the source address is **not** changed.
{% endcall %}

This is due a NAT rule that **masquerade** the routed traffic:

```shell
root@proxyvm:# iptables-save -t nat
...
-A POSTROUTING -o vif+ -j ACCEPT
-A POSTROUTING -o lo -j ACCEPT
-A POSTROUTING -j MASQUERADE
```

The `-o vif+` rule prevents masquerade traffic going downward, back to
the App VM and the `-o lo` ignores loopback traffic.

The rest, including traffic routed to `eth0` is masquerade.

So all Proxy VMs and Net VMs only need to know the IP of the previous
VM and not the full chain.

## Packet walk-through

{% call margindiag('path.svg', 'plantuml') %}
```plantuml
hide empty description

state "AppVM" as app1 {
state "route" as route

[*] --> route
}

state "ProxyVM" as proxy1 {
state "route" as route2

route -down[dashed]-> prerouting : ping from .7.27 to .8.8
prerouting -left-> filter
filter -down-> route2
route2 -right-> postrouting
}

postrouting -down[dashed]-> upstream : ping from .7.26 to .8.8

state "ProxyVM" as proxy2 {
state "route" as route3
state "filter" as filter2
state "postrouting" as postrouting2

upstream -down[dashed]-> filter2 : reply from .8.8 to .7.26
filter2 -down-> route3
route3 -left-> postrouting2
}

state "AppVM" as app2 {
postrouting2 -down[dashed]-> [*] : reply from .8.8 to .7.27
}
```
{% endcall %}


App VM does a ping to `8.8.8.8`, this is the walk-through

```
App VM
| pkt:         10.137.7.27 > 8.8.8.8: ICMP echo request
|
| route:       default via 10.137.7.1 dev eth0
| eth0:        10.137.7.27 > 8.8.8.8: ICMP echo request

Proxy VM
| vif37.0:     10.137.7.27 > 8.8.8.8: ICMP echo request
| prerouting:  ! -s 10.137.7.27/32 -i vif37.0  => NO DROP
| filter:      FORWARD -s 10.137.7.27/32  => ACCEPT
|
| route:       default via 10.137.1.1 dev eth0
| postrouting: POSTROUTING  => MASQUERADE
|
| eth0:        10.137.1.26 > 8.8.8.8: ICMP echo request

--- request is sent to upstream; reply is received moments later ---

Proxy VM
| eth0:        8.8.8.8 > 10.137.1.26: ICMP echo reply
| (rev nat):   8.8.8.8 > 10.137.7.27: ICMP echo reply
| filter:      FORWARD -s 10.137.7.27/32  => ACCEPT
|
| route:       10.137.7.27 dev vif37.0
| postrouting: POSTROUTING -o vif+  => DONT MASQUERADE
|
| vif37.0:     8.8.8.8 > 10.137.7.27: ICMP echo reply

App VM
| eth0:          8.8.8.8 > 10.137.7.27: ICMP echo reply
```


## DNS

The DNS traffic is handled like the above but with a twist.

```shell
root@appvm:# nslookup google.com
Server:     10.137.7.1
Address:    10.137.7.1#53

Non-authoritative answer:
Name:   google.com
Address: 172.217.172.46
```

It is interesting to note that App VM queried `10.137.7.1` to resolve
the address: the Proxy VM is working as a DNS resolver.

```shell
root@appvm:# tcpdump -n -i eth0
...
23:58:30.214939 IP 10.137.7.27.46734 > 10.137.7.1.53: 26595+ A? google.com. (28)
23:58:30.337391 IP 10.137.7.1.53 > 10.137.7.27.46734: 26595 1/0/0 A 172.217.172.46 (44)
```

{{ hline() }}

```shell
root@proxyvm:# tcpdump -n -i vif37.0
...
23:58:30.220387 IP 10.137.7.27.46734 > 10.137.7.1.53: 26595+ A? google.com. (28)
23:58:30.342664 IP 10.137.7.1.53 > 10.137.7.27.46734: 26595 1/0/0 A 172.217.172.46 (44)
```

But that's a lie: there is no DNS resolver in Proxy VM and
the DNS request is forwarded upstream:

```shell
root@proxyvm:# tcpdump -n -i eth0
...
23:58:30.220455 IP 10.137.1.26.46734 > 10.137.1.1.53: 26595+ A? google.com. (28)
23:58:30.342616 IP 10.137.1.1.53 > 10.137.1.26.46734: 26595 1/0/0 A 172.217.172.46 (44)
```

Notice how the source address is masqueraded as we saw with the ping packet
but the **destination address is changed** too:

```
23:58:30.220387 IP 10.137.7.27.46734 > 10.137.7.1.53: 26595+ A? google.com. (28)
                    NAT  |                   |  DNAT
                         V                   V
23:58:30.220455 IP 10.137.1.26.46734 > 10.137.1.1.53: 26595+ A? google.com. (28)
```

## DNAT

Nobody is listening on the `53 udp` port so the DNAT is applied *before* routing.

```
root@proxyvm:# iptables-save -t nat
...
-A PREROUTING -j PR-QBS
-A PR-QBS -d 10.137.7.1/32 -p udp -m udp --dport 53 -j DNAT --to-destination 10.137.1.1
-A PR-QBS -d 10.137.7.1/32 -p tcp -m tcp --dport 53 -j DNAT --to-destination 10.137.1.1
-A PR-QBS -d 10.137.7.254/32 -p udp -m udp --dport 53 -j DNAT --to-destination 10.137.1.254
-A PR-QBS -d 10.137.7.254/32 -p tcp -m tcp --dport 53 -j DNAT --to-destination 10.137.1.254
...
```

Firewall rules also apply

```
root@proxyvm:# iptables-save -t filter
...
-A FORWARD -s 10.137.7.27/32 -d 10.137.1.1/32 -p udp -m udp --dport 53 -j ACCEPT
-A FORWARD -s 10.137.7.27/32 -d 10.137.1.254/32 -p udp -m udp --dport 53 -j ACCEPT
-A FORWARD -s 10.137.7.27/32 -d 10.137.1.1/32 -p tcp -m tcp --dport 53 -j ACCEPT
-A FORWARD -s 10.137.7.27/32 -d 10.137.1.254/32 -p tcp -m tcp --dport 53 -j ACCEPT
...
```

In the Net VM the destination is replaced by the DNS resolver address
configured:

```
root@netvm:# iptables-save -t nat
...
-A PR-QBS -d 10.137.3.1/32 -p udp -m udp --dport 53 -j DNAT --to-destination 8.8.8.8
-A PR-QBS -d 10.137.3.1/32 -p tcp -m tcp --dport 53 -j DNAT --to-destination 8.8.8.8
-A PR-QBS -d 10.137.3.254/32 -p udp -m udp --dport 53 -j DNAT --to-destination 8.8.8.8
-A PR-QBS -d 10.137.3.254/32 -p tcp -m tcp --dport 53 -j DNAT --to-destination 8.8.8.8
...
```


## Future readings

About networking and sysadmin:

 - [Linux Advanced Routing & Traffic Control HOWTO](https://lartc.org/howto/)
 - [Qubes OS VPN](https://www.qubes-os.org/doc/vpn/)
 - [Netfilter bug](https://bugzilla.netfilter.org/show_bug.cgi?id=693)
 - [Iptables notes](http://www.smythies.com/~doug/network/iptables_notes/)

Qubes related:

 - [QSB-056](https://www.qubes-os.org/news/2019/12/25/qsb-056/)
 - [PR 209](https://github.com/QubesOS/qubes-core-agent-linux/pull/209)
 - [PR 201](https://github.com/QubesOS/qubes-core-agent-linux/pull/201)

## References

 - [Linux IP](http://linux-ip.net/linux-ip/)
 - [Linux Advanced Routing Tutorial](https://www.linuxjournal.com/content/linux-advanced-routing-tutorial)
 - [Playing with Qubes networking for fun](https://theinvisiblethings.blogspot.com/2011/09/playing-with-qubes-networking-for-fun.html)


