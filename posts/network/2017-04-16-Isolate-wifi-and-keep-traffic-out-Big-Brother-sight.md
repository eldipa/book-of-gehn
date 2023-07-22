---
layout: post
title: Isolate a wifi card and keep your traffic out of the Big Brother sight
tags: [wifi, container, hacking]
---

{{ marginfig('isolate_wifi_big_brother_sight.png', indexonly=True) }}

HTTP Proxies blacklisting evil domains, firewalls blocking weird traffic
and IDSs looking for someone that shouldn't be there are reasonable and
understandable policies for a corporate environment.

But when a friend opened his browser this week and went to ``google.com``
the things got odd.

The browser refused the connection warning him that the SSL certificate
of the server wasn't issue by ``google.com`` at all or signed by a
trusted authority.<!--more-->

My first thought was, *"this is a man in the middle attack"* but it turned out
that the IT guys said to him: *"it's OK, just accept the new certificate and
ignore the warning of the browser"*.

They were tampering the internet access of all the company!{{ marginfig('isolate_wifi_big_brother_sight.png') }}

All his credentials, emails and documents could be read by someone else.
That was unacceptable.

Fortunately he has a Starbucks near with a decent wifi signal strength.

{% call marginnotes() %}
**tl;dr:** this [script]({{ asset('isolate_wifi.sh') }})
 is all what you need to have an isolated wifi network.
{% endcall %}

Now the challenge is how to separate the private traffic so it can go
only through the wifi while ensuring that the corporate traffic stays
where it belongs, under the sight of the *Big Brother*.

### Isolate a wifi card with Network Namespaces

In a modern linux implementation we can use a ``Network Namespace`` that
can create isolated full network stacks with their own routes and firewall
rules.

Any program running inside that namespace will see only that network stack
that it is perfect for our purpose.

Let's create it first; pick a nice name and run:

```shell
$ ip netns add "starbucks"
```

With that we have our ``"starbucks"`` namespace, empty for now.

Now, we cannot put our wifi card into that namespace directly using
the ``ip`` command.

Typically you should use something like:

```shell
$ ip link set DEVICE netns "starbucks"
```

to move the ``DEVICE`` from the default namespace to the ``"starbucks"``
namespace, **but no**, we cannot use this.

A wireless card is a little more exotic.

First, we need to know the *physical id* of our card:

```shell
$ iw dev "wlan0" info
Interface
    ifindex 3
    wdev 0x1
    addr <mac-addr>
    type managed
    wiphy <phy-id>
```

where ``"wlan0"`` is the name of our wifi interface.

If you are lazy like me then you may find useful this shortcut.
The ``iw`` manpage warns that the output of this command shouldn't be scrapped,
but let's be disobedient for a while:

```shell
$ PHYNUM=$(iw dev "wlan0" info | sed -n 's/^.*wiphy \([0-9]\+\)$/\1/p')
$ echo "$PHYNUM"
<phy-id>
```

Now, it comes the tricky part.

To move a wifi card to a namespace we need to have a process already
running there in the first place.

Then we use ``iw`` to move the card.

Here are the bits that do the magic:

```shell
$ ip netns exec "starbucks" sleep 3 &
$ PID=$!

$ iw phy "phy<phy-id>" set netns "$PID"
```

Just run a process in the namespace in background,
grab its process id, and move the ``"phy<phy-id>"`` card to the same
namespace of that process.


### Connect to a wifi network

With the card in its place, we are left is configure it. Pretty standard.

First, up the interfaces in the ``"starbucks"`` namespace:

```shell
$ ip netns exec "starbucks" rfkill unblock "<phy-id>"

$ ip -n "starbucks" link set "wlan0" up
$ ip -n "starbucks" link set "lo" up
```

And connect to the access point.

This of course will depend of the authentication method used by
your local Starbucks.

For an open network it is quite easy:

```shell
$ ip netns exec "starbucks" iw "wlan0" connect -w "$SSID"
wlan0 (phy #<phy-id>): connected to <ap-mac-addr>
```

For a WPA/WPA2 protected network we need to generate a passphrase
(and configuration) and then run ``wpa_supplicant``, an agent that will
handle the negotiation between your machine and the access point and
it will keep it alive in background.

```shell
$ wpa_passphrase "$SSID" > "/tmp/starbucks_wpa_file"
$ ip netns exec "starbucks" wpa_supplicant -B -i "wlan0" -c "/tmp/starbucks_wpa_file"
```

In both cases, the ``$SSID`` is the name of the wifi network
that you want to connect.

To setup the IP address, the gateway and the DNS server we can use
a DHCP client:

```shell
$ ip netns exec "starbucks" dhclient "wlan0"
```

Or we can setup them manually:

```shell_session
$ ip -n "starbucks" addr add "192.168.0.22/24" dev "wlan0"
$ ip -n "starbucks" route add default via "192.168.0.1" dev "wlan0"

$ mkdir -p "/etc/netns/starbucks"
$ echo "nameserver 8.8.8.8" > /etc/netns/starbucks/resolv.conf
```

The network namespace will mount on ``/etc`` each custom file
inside ``/etc/netns/starbucks`` so any unaware program executed
by ``ip netns exec`` that wants to read/write a file in ``/etc`` will be
actually accessing to the files in ``/etc/netns/starbucks``.

In our case, we created a custom ``/etc/netns/starbucks/resolv.conf`` to
configure the DNS lookup.

> Upss: ``dhclient`` will no be able to write its ``resolv.conf`` and you will
> require to setup the DNS manually.
>
> If you are brave enough you can try another [hack](https://stackoverflow.com/questions/38102481/how-can-dhclient-be-made-namespace-aware).

### *Surf* out of the Big Brother sight

To navigate free, open your favorite browser (or other network application)
*inside* the network namespace.

To do that open a shell inside the namespace and log in as a normal user; only
then open your browser:

```shell
$ ip netns exec "starbucks" su -l "gehn"
in namespace) firefox
```

This is an important detail: if you run ``ip netns exec firefox`` directly
you will end up running your browser with root privileges.

### Close everything

In order to clean up everything, you need to ensure that all the processes
running inside the namespace are killed and only then remove the namespace
itself.

Otherwise if some process keeps alive the namespace will not be deleted.

```shell
$ ip netns pids "starbucks" | xargs kill -15 # be polite
$ sleep 12
$ ip netns pids "starbucks" | xargs kill -9  # but being bad is more fun
$ ip netns delete "starbucks"
$ rm -Rf /etc/netns/starbucks/
```

If you are a little paranoiac you can also block the wifi card
before leaving the namespace to ensure that nobody will use it after that
the namespace is gone:

```shell
$ ip netns exec "starbucks" rfkill block "<phy-id>"
```
