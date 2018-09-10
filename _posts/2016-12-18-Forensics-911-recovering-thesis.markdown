---
layout: post
title: Forensics 911 - recovering a thesis of one year work
---

A friend of mine called me: a girl friend of him was hopeless trying to recover her thesis from a corrupted usb stick *three days* before her presentation.

She was working in her thesis for almost a year, saving all the progresses in that usb stick. But what she didn't know was that an usb memory has a limited number of writes and with more writes eventually the file system gets corrupted.

This is the real story behind a forensics rally trying to recover her one year work.<!--more-->

*"Ok"* -- I said to my friend -- *"bring me the pendrive. Tell to this girl that she must unplug it to avoid any further corruption. She mustn't to touch anything..."*

*"Well, I can't give you the pendrive right now"* -- he said -- *"She gave it to his father to see if he could recover the file. He couldn't. She also asked to a friend of hers who also couldn't and I think that she took it to a guy that works with these things."*

**Rule number one:** don't touch it, it will only get worse. Obviously this wasn't the case.

## Why `dd` is not the best option for cloning a disk

It was 11 pm and the pen drive was at last in my hands: *it's forensic time*

First that all we need an image of the disk to work with it without worrying to damage the original usb with our tests.

There are quite a few options out there, and `dd` is the first choice that crossed my mind but not the best.

`dd` can be found in any linux box by default. It can copy the disk to a file reading one block of data at time and avoiding mounting the file system at all.

The disk can only be read and written in terms of sectors which in general have a 512 bytes of size. Because of that it is desired to set the size of the blocks of `dd` for reading and writing to a multiple of the sector size.

Using a different value, it will result in reading and writing incomplete sectors: it will work but you will need at least a second disk access to complete the same sector so it's a complete waste of time.

**Rule number two:** the sector size is a key parameter. Some tools will work better with it, others will don't work at all without it. Always check this size.

Lets check that with `fdisk`

```shell_session
$ fdisk -l /dev/sdc
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
```

So, why we should change the size of the block used by `dd` anyway? Well, larger blocks may improve the performance accessing less times to the disk. But it also can be a disadvantage.

`dd` will **stop** if a read fails. Even if `dd` goes on, the whole failed block is discarded and skipped. That means that a single bad sector of just 512 bytes can make that the whole block of, lets say 2k, gets discarded. 
Worse, `dd` will *skip* the failed block meaning that he won't write anything to the output, leading to a shorter image.
And most of the forensic tools don't like these kind of images.

So we need to make sure that `dd` will not stop and at least write something in replace of a failed block.

```shell_session
$ dd if=/dev/sdc of=sdc.dd bs=2k conv=noerror,sync
```

Those two flags in the `conv` parameter do the magic:

 - `noerror` will force to continue the copy even if there is a reading error.
 - `sync` will replace a failed block by a block full of zeros in the output.

If `dd` is new to you, the other parameters are:

 - `if` is the name of the file or device to read, `/dev/sdc` was the pendrive in this case
 - `of` the same but to write, `sdc.dd` is the name of disk image
 - `bs` the block size, 2k in this case.

But as I said before, `dd` is not the best choice. Think in the above setting, `bs=2k` means blocks of 2k of size. With only one single bad sector the whole 2k bytes block is lost.

Don't get me wrong, `dd` is not a bad software but it was never been designed for forensics purposes.

## Cloning the disk with `GNU ddrescue`

There are a lot of tools for recovering out there, some are based in `dd`, other don't. I found quite useful the tool `GNU ddrescue` which despite the name it's not based in `dd` at all.

Watch out there, there is also a tool called `dd_rescue` (notice the underscore) that has nothing to do with `GNU ddrescue`.

`GNU ddrescue`, from now on just `ddrescue`, will copy a disk through three stages.

In the first, it reads blocks of data and copy them to the output in the same manner that `dd` but unlike the latter, `ddrescue` will not stop if it found an error nor will put zeros nor discard the block if the reading fails.

{% marginfigure 'Trimming and Scraping' 'assets/trimming_scraping_ddrescue.png' 'Trimming and Scraping' %}

Instead, it will *keep track* of all the failed blocks in a log file.

In the second phase, it will try to read again *only* the failed blocks, but this time will read sector by sector from the begin of the block until it reaches a bad sector and then it will do the same but starting from the end and going backwards. This is called *trimming* the block.

In the third and last phase, it will try to read all the remained trimmed blocks again, sector by sector, but without stopping at the first bad sector. Every single sector will be tried. This is called *scraping* the block.


What is the output of all this process? An image of the disk with holes in it representing the missing bad sectors and the log file which keeps track of those holes.

Here there are the lines of code:

For the first phase

```shell_session
$ ddrescue --no-trim --no-scrape /dev/sdc sdc.img sdc.ddrescue.logfile
```

And for the second and third phases

```shell_session
$ ddrescue -r3 /dev/sdc sdc.img sdc.ddrescue.logfile
```

Just for the record, the flags are:

 - `no-trim` disables the second phase
 - `no-scrape` disables the third phase
 - `r3` retries each bad sector at most three times

By default, `ddrescue` performs the three phases at once so, why I separated the first phase from the rest two?

The first will give you a first approximation probably with all the data that you need.

If the disk has a lot of bad sectors, `ddrescue` will spend a lot of time trying to recover the data in the second and third phases. When the disk has several gigabytes of size this will take a longer time (boring!). The first phase gives you a trade off between to get a result *faster but incomplete*. 

The rest two phases will try to complete the image and sometimes those little chunks of data recovered will be the missing pieces of the puzzle so it is worth to try those phases too.

**Rule number three:** try to get an incomplete piece of data to work on as soon as possible while you get the complete picture in background.

In this point I prefer to take a copy of the image and the log file before doing anything else. Hashing is also a good practice so you can corroborate in the future if the image was altered. A sha1 should be enough.

The image will have holes, one for each bad sector that couldn't be recovered. Because most of the tools cannot work with images with holes we need to fill those with a custom string.

Some people fill them with zeros but I found that filling them with a cookie or special string is more useful. You can later use `grep` to search for the cookie to see which files were corrupted.

```shell_session
$ echo -n "BADxSEC!" > badsec_mark
$ ddrescue --fill-mode=- badsec_mark sdc.img sdc.ddrescue.logfile
```

## Mounting

To this point what we did was a clone of the entire disk, including the partition table so the next thing that we need is to check if the partition table is ok. It is important to check each value to see if it makes sense, *don't trust in the output* of a magical tool, use your own brain. Remember that you are reading corrupted data.

**Rule number four:** don't trust in anyone.

To see if the partition table is ok I used the `mmls` tool from the `sleuthkit` package.

```shell_session
$ mmls -B sdc.img
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000002063   0000002064   Unallocated
002:  000:000   0000002064   0008376319   0008374256   Win95 FAT32 (0x0b)
```

This looks good, the first sector is designated to the partition table and the disk has only one FAT32 partition.

The lengths are in sector terms so to know the size of the partition in bytes we can just do (8374256 * 512.0) / (1024 ** 3) which yields 3.99 gigabytes which it makes sense given that the usb stick is of 4 gigabytes.

The output of `mmls` can be a little confusing because it is showing that the first and the second slices start both at the 0 position. So those two slices overlaps and that is wrong and could mean that the partition table is corrupt but it is not.

`mmls` can show you four things at the same time: 

 - the allocated (`-a`) and unallocated (`-A`) spaces
 - the metadata (`-m`) and the non-metadata (`-M`) volumes

If you don't use any of those flags, `mmls` will show all the spaces and volumes and the concept of space and volume can overlap. To see if there is a real overlapping or not, we can see the allocated and unallocated spaces only:

```shell_session
$ mmls -a -A sdb.img
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
001:  -------   0000000000   0000002063   0000002064   Unallocated
002:  000:000   0000002064   0008376319   0008374256   Win95 FAT32 (0x0b)
```

And as you can see the spaces start and end at the correct position without overlapping. So this seems to be ok.

Let's try to mount that file system:

```shell_session
$ mount -o ro,loop,offset=1056768 sdc.img mnt/
```

Because the file system doesn't start at the begin of the image file we need to calculate the offset where it really starts: start sector (2064) multiplied by the sector size (512) or just 2064 * 512 = 1056768.

The mount didn't fail so at least the file system is not *so* damaged.

## Trying to recover the thesis politely 

Let's see if any file's data are corrupt

```shell_session
$ grep -R "BADxSEC!" *
```

None file seems to be corrupt. Of course, `grep` is not telling you the whole story. 

The file system doesn't see a file as a single unit but as a serie of small blocks of data chained. Those chains are stored and can be corrupted too. If that happen the files can be missing, truncated, merged, or who-knows-what-else because the file system cannot ensemble the file from the blocks.

Nevertheless, looking in the mounted file system, the thesis.docx was there, so we can try to recover it directly. It's a docx file (a zip file) so we can try:

```shell_session
$ zip -FF thesis.docx --out thesis.recovered.docx
```

But it didn't work, only a few pages were recovered.

## Recovering the thesis by bad

Trying to fix a damaged file system is not a trivial task but before even thinking about that, we may have some luck looking for an old deleted backup or a temporary file.

When a file is deleted the file system will remove the link between the file and the rest of the system preventing that anyone can access it again. The space is marked as free and ready to be used by others but is not *erased*, so the data is still there, inaccessible from the file system, but there.

We can recover those deleted files easily scanning the whole image instead of using the mounted file system.

```shell_session
$ foremost -t zip sdc.img
```

For the curious:

 - `-t zip` will try to extract all the zip like files including docx ones. `foremost` has a `-t doc` flag but it will not work with docx files 

The result? 41 files recovered. Cool! but it is 3 am of the early morning and checking one file at a time is not the best way to spend the night.

Is there any way to filter them to check only a few of them?

**Rule number five:** sleep. If you need to think out of the box, you had better to be rested.

It's 9 am, I have a strategy and the round two begins. *Fight!*

Most of the files, including the docx files, have metadata so I thought, "maybe I can filter the files using somes attribute in the metadata".

For that we can use a tool from the `libimage-exiftool-perl` package

```shell_session
$ exiftool  *.docx | grep "========\|File Name\|Heading\|Title\|Pages"
```


`exiftool` will extract all the metadata that it can. It's a very complex tool with a lot of flags and options and  is out of scope for this post to explain.

I was expecting that some of the documents have a clue in their titles or heading but it was the amount of pages what I used as a hint. From all those documents only three had more than 50 pages.

Those were three non-corrupted older versions of the thesis. In fact, one of them was only one old week.

It's 10 am we recovered the thesis.

**Rule number six:** next time, do a backup.

