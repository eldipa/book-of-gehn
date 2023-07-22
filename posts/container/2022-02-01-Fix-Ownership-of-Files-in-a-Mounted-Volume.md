---
layout: post
title: "Fix Ownership of Files in a Mounted Volume"
tags: [docker]
inline_default_language: shell
---

The file system of a docker container is ephemeral: it will disappear as
soon as the container is destroyed.

To prevent data losses you can mount a folder *of the host* into the
container that will survive the destroy of the container.

But it is not uncommon to find issues with the ownership and permissions
of the *shared* files.

The file system of the host represents who is the owner of each file
with an user and a group numbers.

Plain numbers.

Humans, on the other hand, think in terms of user names: *"this is
the file of Alice; this other is of Bob"*.

The mapping between the numbers that the file system uses and the names
that the humans understand is stored in `/etc/passwd` and `/etc/groups`.

And here we have a problem.

These two files, `/etc/passwd` and `/etc/groups`, live in the host's
file system and they are used to map the files' numbers to names when
you are seeing the files *from the host*.

When you enter into the docker container (or run a command inside), the
shared files, mounted with `-v`, will have the **same** file numbers.

But, an here is the twist, inside the container you will be using for
the mapping the `/etc/passwd` and `/etc/groups` files *of the container*
and not of the host.

Same file numbers, different mappings.<!--more-->

## UID/GID

Imagine the following folder in the host:

```shell
(host) $ ls -lah /home/alice/blog
drwxr-xr-x 12 alice devel 4.0K Jan 30 21:28 .
drwxr-xr-x 63 alice devel 4.0K Jan 30 21:25 ..
drwxr-xr-x  2 alice devel 4.0K Jan 30 20:35 docker
drwxr-xr-x  8 alice devel 4.0K Jan 31 02:40 .git
-rw-r--r--  1 alice devel   52 Jan 22 14:23 .gitignore
-rw-r--r--  1 alice devel 1.9K Jan 30 21:10 Makefile
drwxr-xr-x 26 alice devel 4.0K Jan 31 02:22 posts
```

All those files and folders belong to the user `alice` and the group
`develop`.

But that's with the host's mapping.

We can see the file numbers behind running:

```shell
(host) $ ls -lah --numeric-uid-gid /home/alice/blog
drwxr-xr-x 12 1001 1024 4.0K Jan 30 21:28 .
drwxr-xr-x 63 1001 1024 4.0K Jan 30 21:25 ..
drwxr-xr-x  2 1001 1024 4.0K Jan 30 20:35 docker
drwxr-xr-x  8 1001 1024 4.0K Jan 31 02:43 .git
-rw-r--r--  1 1001 1024   52 Jan 22 14:23 .gitignore
-rw-r--r--  1 1001 1024 1.9K Jan 30 21:10 Makefile
drwxr-xr-x 26 1001 1024 4.0K Jan 31 02:22 posts
```

So, for the host user `alice` maps to the UID `1001`; the same goes for
the group `develop` and the GID `1024`.

Now, imagine that we run a docker container and mount that folder above

```shell
(host) $ docker run -it -v /home/alice/blog:/wd ubuntu bash
```

The host's `/home/alice/blog` is mounted in `/wd` inside the container.

If we list the files from *inside* the container we will see the *same*
UIDs and GIDs

```shell
(container) $ ls -lah --numeric-uid-gid /wd
drwxr-xr-x 12 1001 1024 4.0K Jan 30 21:28 .
drwxr-xr-x 63 1001 1024 4.0K Jan 30 21:25 ..
drwxr-xr-x  2 1001 1024 4.0K Jan 30 20:35 docker
drwxr-xr-x  8 1001 1024 4.0K Jan 31 02:43 .git
-rw-r--r--  1 1001 1024   52 Jan 22 14:23 .gitignore
-rw-r--r--  1 1001 1024 1.9K Jan 30 21:10 Makefile
drwxr-xr-x 26 1001 1024 4.0K Jan 31 02:22 posts
```

But not necessary we will see the same mapping.

## Incorrect mapping: two scenarios

There are 2 cases.

**Scenario 1**: there is no user/group with those IDs in the container
so you will see this:

```shell
(container) $ ls -lah /wd
drwxr-xr-x 12 1001 1024 4.0K Jan 30 21:28 .
drwxr-xr-x 63 1001 1024 4.0K Jan 30 21:25 ..
drwxr-xr-x  2 1001 1024 4.0K Jan 30 20:35 docker
drwxr-xr-x  8 1001 1024 4.0K Jan 31 02:43 .git
-rw-r--r--  1 1001 1024   52 Jan 22 14:23 .gitignore
-rw-r--r--  1 1001 1024 1.9K Jan 30 21:10 Makefile
drwxr-xr-x 26 1001 1024 4.0K Jan 31 02:22 posts
```

**Scenario 2**: there is user/group in the container assigned to those IDs
but they are mapped, of course, to something different than
`alice`/`develop`:

```shell
(container) $ ls -lah /wd
drwxr-xr-x 12 apt sys 4.0K Jan 30 21:28 .
drwxr-xr-x 63 apt sys 4.0K Jan 30 21:25 ..
drwxr-xr-x  2 apt sys 4.0K Jan 30 20:35 docker
drwxr-xr-x  8 apt sys 4.0K Jan 31 02:43 .git
-rw-r--r--  1 apt sys   52 Jan 22 14:23 .gitignore
-rw-r--r--  1 apt sys 1.9K Jan 30 21:10 Makefile
drwxr-xr-x 26 apt sys 4.0K Jan 31 02:22 posts
```

## How to fix this?

We need a *common* user and group in the host and container with the
same UID and GID in both worlds.

In the scenario 1 we need to create an user and a group inside the
container with the same UID/GID that the one from the host (`1001` and
`1024` respectively)

In the scenario 1 we are lucky: the UID/GID `1001`/`1024` are not assigned
to any user/group so we can create the user `alice` and the group
`develop` in the container and that's it.

The scenario 2 is more complex because the UID/GID are already assigned.
We will have to create a totally new user/group, both in the host and
the container, to fix this.

Because the scenario 1 is a special subset of the scenario 1, I will
describe how to fix the scenario 2.

First, pick a UID/GID that is not used either in the host nor in the
container.

{% call marginnotes() %}
I'm using different numbers to make it easier to read but it is not
necessary. You could use the same number for the UID and the GID without
problems.

You can skip this step for the scenario 1 and use the original UID/GID
`1001`/`1024`
{% endcall %}

For example, let's pick `1201` for the UID and `1224` for the group.

We can check this running `grep` and getting a 0 response that means
that the id was not found (so it is not used)

```shell
(host) $ grep -c 1201 /etc/passwd
0
(host) $ grep -c 1224 /etc/group
0

(container) $ grep -c 1201 /etc/passwd
0
(container) $ grep -c 1224 /etc/group
0
```

With a free UID/GID we need to create a group and an user with those ids

```shell
(container) $ sudo groupadd -g 1224 devel2
(container) $ sudo useradd -s /bin/bash -u 1201 -M -g 1224 alice2
```

These creates a group named `devel2` with GID of `1224` and an user named
`alice2` with UID of `1201`. *Yes, I'm not very creative with the names.*

The `-M` says that you don't want a home folder and
`-s` sets the user's shell to `/bin/bash`.

{% call marginnotes() %}
You can skip this step for the scenario 1 as you can use `alice` and
`devel`
{% endcall %}

Now we do the same in the *host*

```shell
(host) $ sudo groupadd -g 1224 devel2
(host) $ sudo useradd -s /bin/bash -u 1201 -M -g 1224 alice2
```

Finally change the ownership of the shared files running

```shell
(host) $ sudo chown -R 1201:1224 /home/user/blog
```

Now before working with the files you need to log in as `alice2`

```shell
(host) $ sudo su alice2

(container) $ sudo su alice2
```

This applies to both the host and container.

Once logged in it may be convenient to set your `HOME`.

```shell
(host) $ export HOME=/home/alice
(container) $ export HOME=/wd
```

## Why a simplest `chown`/`chmod` does not work?

On internet the solution to the *"permission problem"* is to run
`chmod`.

You run `chmod` in the container to add a read-write-exec permissions ot
*everyone*. Indeed any user, from the host or container, will be able to
work with those files.

But what happen if you add a new shared file? That will have the user ownership
and default permissions and you will not be able to use it in the
host/container.

Not a stable fix, and `0777` looks suspicious.

Running `chown` to change the ownership is even more messier because you
may change and set the *"correct"* user/group inside the container but
you will be scrubbing the scenario in the host.

The ownership is not the problem. The permission are not the problem.
Who to interpret the UID/GID **is** the problem.

## (bonus track) To be a sudoer

```
$ sudo groupadd admin
$ sudo echo '%admin  ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/admin
$ sudo chmod 0400 /etc/sudoers.d/admin

$ sudo usermod -aG admin alice2
$ sudo usermod -aG sudo alice2
```
