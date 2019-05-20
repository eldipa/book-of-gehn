---
layout: post
title: Separate your SSH Agent Identities
---

Using a ``ssh-agent`` to handle our keys is handy.

When you need to access to different hosts jumping from one to another,
*forwarding* the agent is much more secure than copying and pasting
your keys around.

But if one host gets compromised it will expose your agent: even if the
attacker will not get your secret keys he will be able to login into
any system as you.

You cannot prevent this, but you can restrict this to reduce the splash
damage.<!--more-->

## Explicit is better than implicit

You can instruct to your ``ssh-agent`` to request your *explicit* permission
to use a particular key.

This gives you the opportunity to detect when someone is trying to use
your agent.

A simple alias is enough:

```shell
$ alias ssh-add='ssh-add -c'
```

To make it usable you are going to need a program that can ask you
if a particular key can be used or not.
There are several options but if you want simplicity I think that
``ssh-askpass`` is good enough.

## Multiple ``ssh-agent``s

Even using an explicit confirmation, you agent may leak some info exposing
all the public keys that it has.

This is because when you (or the attacker in your behalf) request a secure
shell to a remote host, ``ssh`` will offer **all** the available public keys that
the agent has.

Only if one is accepted, the agent will ask you confirmation; technically
a public key is for that but it may reveal more than you want.

For example you could have ssh key for your personal ``github`` account
and another key for your work.

You use the latter ssh key to log in to some work-related host and
forward the agent.

But if you loaded *both* keys to the *same* agent, it may leak the fact
that you have a personal ``github`` account.

The only way to prevent this is to not load all the keys in the same agent
and use *different* ``ssh-agent``s instead.

### Switch by hand

Assuming that you have two ``ssh-agent``s running, to use a particular one you
need to set some environment variables in your current shell:

```shell
$ export SSH_AGENT_PID="$agent_pid"
$ export SSH_AUTH_SOCK="$sock_file"
```

Where ``$agent_pid`` and ``$sock_file`` are the process id of the agent and
the socket file that it created for IPC.

But doing that by hand is error prone.

## ``ssh-use-agent``

For this I wrote [ssh-use-agent](https://github.com/eldipa/ssh-use-agent),
a simple script to spawn and switch between ``ssh-agent``s.

To install it, save the script somewhere and give it execution permissions.

For simplicity, create an ``alias`` to invoke it without remembering to
source it.

```shell
$ alias ssh-use-agent=". ~/your-scripts/ssh-use-agent"
```

And to have a quick feedback about which ``ssh-agent`` is begin use,
modify your prompt:

```shell
$ PS1='${SSH_AGENT_NAME:+(agent $SSH_AGENT_NAME) } \$ '
```

> That works for ``Bash``, depending of your shell and your personal
> configuration and taste those bits may vary.

To start using an agent run:

```shell
$ ssh-use-agent use personal
```

That will *use* an already running ``ssh-agent`` registered under the name
``personal`` and it will *source* into your terminal the required environment
variables so any program spawned from there will use that agent.

```shell
$ echo $SSH_AGENT_PID
<pid>

$ echo $SSH_AUTH_SOCK
/tmp/<...>

$ echo $SSH_AGENT_NAME
personal
```

If no agent is registered under that name, ``ssh-use-agent`` will spawn a new
``ssh-agent`` for you.

It is up to you to load any ssh key to it later with ``ssh-add``
(or ``ssh-add -c``).

Run ``ssh-use-agent disuse`` to dis-configure your terminal. Keep in mind
that no agent will be shutdown.

```shell
$ ssh-use-agent disuse

$ echo $SSH_AGENT_PID
$ echo $SSH_AUTH_SOCK
$ echo $SSH_AGENT_NAME
```

To remove a key or all the keys use ``ssh-add`` as usual; to kill
a particular ``ssh-agent`` use the traditional ``kill -15``.
