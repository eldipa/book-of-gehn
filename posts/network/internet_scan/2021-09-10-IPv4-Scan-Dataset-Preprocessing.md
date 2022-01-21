---
layout: post
title: "IPv4 Scan 2021 - Dataset Preprocessing"
tags: [pandas, reset_index, json, categorical, parquet]
inline_default_language: python
---

The [dataset](https://www.kaggle.com/signalspikes/internet-port-scan-1)
is a survey or port scan of the whole IPv4 range made
with [masscan](https://github.com/robertdavidgraham/masscan).

The dataset however is much smaller than the expected mostly because
most of the hosts didn't response and/or they had all the scanned ports
closed.

Only open ports were registered.

More over, of the 65536 available ports only a few were scanned and only
for the TCP protocol.

Even with such reduced scope the dataset occupies around 9 GB.

This post is a walk-through for loading and preprocessing it.<!--more-->

## Loading JSON

The original dataset is in JSON which it is not the most
space-efficient format.

It consists in an array of hosts and per host we have an array of ports.

```javascript
  {
    'ip': '165.221.32.138',
    'timestamp': '1619562631',
    'ports': [
       {
         'port': 21,
         'proto': 'tcp',
         'status': 'open',
         'reason': 'syn-ack',
         'ttl': 245
       }
    ]
  }
```

So there is plenty room for improvements.

Python's `json` library loads everything to memory. This is a no-go.
We use instead [ijson](https://github.com/ICRAR/ijson) that iterates
over the elements of the file loading only what it is needed.

```python
import ijson
import sys

# read from standard input and yield each host from it
hosts = ijson.items(sys.stdin, 'item')

for host in hosts:
    ip, timestamp, ports = host['ip'], int(host['timestamp']), host['ports']
    ...
```

## IPv4 packing

The IP address can be stored in 4 bytes and Python's `ipaddress` can pack
it for us:

```python
import ipaddress

for host in hosts:
    ip, timestamp, ports = host['ip'], int(host['timestamp']), host['ports']

    ip = ipaddress.ip_address(ip)
    assert ip.version == 4

    ip = int(ip)
    ...
```

## Categorical data

Each port has a `status` and protocol (`proto`). Because those two
are fixed to `open` and `tcp` respectively, it is pointless to store
them.

The rest of the port's attributes are more interesting:

```python
for host in hosts:
    ...
    for port in ports:
        num, ttl = int(port['port']), int(port['ttl'])
        reason = port['reason']
        ...
```

`reason` is a string that represent why the port is open. But strings
are expensive.

We can use instead a *categorical type*, a mapping between these strings
and integers that represent them more efficiently:

```python
from pandas.api.types import CategoricalDtype

# all the reasons that are in the dataset
reason_cat = CategoricalDtype([
    'syn-ack',
    'syn-ack-ece-cwr',
    'syn-ack-ece',
    'syn-psh-ack',
    'syn-ack-cwr',
    'fin-syn-ack'
    ])
```

Pandas already generates the categories for us but this requires to feed
Pandas with all the dataset at once.

Instead we create the categories beforehand, split the dataset
into manageable subsets, *buckets* or *partitions* and create one Pandas'
`DataFrame` per bucket/partition.

We use the *same* `reason_cat` object for all the dataframes created.

This is critical because merging/concatenating two dataframes
with different (but semantically-equivalent) category sets will
**not** raise any error but it will convert the column(s) into
object type.

Quiet unhappy.

{% call marginnotes() %}
Yes, I know, 22 is less than 80
but it is meaningless: "ssh" is less than "http", what could you draw
from it?
 {% endcall %}

The port numbers are also categories as they are not quantities
nor have a meaningful order.

```python
# all the port numbers that are in the dataset
port_cat = CategoricalDtype([
    '21',
    '22',
    '23',
    '80',
    '443',
    '3389',
    '4444',
    '5601',
    '8000',
    '8443',
    '9200',
    ])
```

## Serialization in Apache's Parquet format

To keep the dataset as small as possible we can use smaller types
for each column:

 - `ip` and `timestamp` can be represented by `uint32`
 - `ttl` fits perfectly in `uint8`

Finally, we store each dataframe in disk using
Apache's [Parquet format](https://parquet.apache.org/). We use version 2
that supports a much richer set of data types including `uint32`.

```python
def save_df(rows, fileno):
    columns = ['ip', 'timestamp', 'port', 'ttl', 'reason']
    df = pd.DataFrame(rows, columns=columns)
    df = df.astype({
        'ip': np.uint32,   'timestamp': np.uint32,
        'port': port_cat,  'reason': reason_cat,
        'ttl': np.uint8,
        })

    # clean up
    rows.clear()

    # Save. 'brotli' yielded better compression ratio
    # when compared with snappy y gzip.
    df.to_parquet(f'scan{fileno:04}.pq', compression='brotli', version='2.0')


i, fileno = 0, 0
rows = []
for host in hosts:
    ...
    for port in ports:
        ...
        rows.append(ip, timestamp, num, ttl, reason)

    i += 1
    if i % bucket_size == 0:
        save_df(rows, fileno)
        fileno += 1
...
```

The dataframes are in *tidy format*: each row represents a single
observation, or in this case, a single port scan.

We repeat over and over data that it is shared between port scans
like the IP address or the timestamp (it is the opposite format
of the *normalized format*).

It occupies more space, yes, but the manipulation of the dataset is *much
simpler* and Pandas and Seaborn *are* tidy-centric.

## Host aggregation

We know that all the ports for the same host are in the same `df`
object so we can do some analysis here instead on the whole dataset.

We could count how many ports each host has, how many *different*
reasons were found on each host and the minimum and maximum
TTL seen.

```python
df = df[['ip', 'port', 'ttl', 'reason']].groupby('ip').agg({
    'port': 'count',
    'ttl': ['min', 'max'],
    'reason': 'nunique',
})
```

After a group by/aggregation, the columns will be *multi-index* (to
access the minimum of the TTL we will write `df['ttl']['min']`).

We don't want that so we can remap the columns and reset the index.

```python
df.columns = df.columns.map('_'.join)
df = df.reset_index()

df = df.astype({
    'port_count': np.uint8,
    'reason_count': np.uint8
})
```

Then we can extend `save_df()`:

```python
def save_df(rows, fileno):
    df = pd.DataFrame(rows, columns=columns)
    ...
    df.to_parquet(f'scan/scan{fileno:04}.pq', version='2.0')

    df = df[['ip', 'port', 'ttl', 'reason']].groupby('ip').agg({
        'port': 'count',
        'ttl': ['min', 'max'],
        'reason': 'nunique',
    })
    ...
    df.to_parquet(f'agg/agg{fileno:04}.pq', version='2.0')
```

## Final bits

Putting all this together in [repack.py]({{ asset('repack.py') }})
and presto!

```shell
unzip -p archive.zip | python repack.py
```
