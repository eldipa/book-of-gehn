---
layout: post
title: "QEMUlating Rasbian ARM"
---

Quick how-to Download and run a Raspbian Buster (ARM) emulating
the vm with QEMU.<!--more-->

 - Download [Raspbian lite image (Buster)](https://downloads.raspberrypi.org/raspios_lite_armhf/images/raspios_lite_armhf-2020-12-04/)
 - Download [kernel image](https://github.com/dhruvvyas90/qemu-rpi-kernel) for
   Raspbian (`kernel-qemu-*-buster`) and the *dtb* file for that kernel
   (`versatile-pb-buster-*.dtb`)
 - Install QEMU: `apt-get install qemu-system`


## Preparing the image

Unpack and check the disk file.

```shell
$ unzip 2020-12-02-raspios-buster-armhf-lite.zip
Archive:  2020-12-02-raspios-buster-armhf-lite.zip
  inflating: 2020-12-02-raspios-buster-armhf-lite.img

$ sudo fdisk -l 2020-12-02-raspios-buster-armhf-lite.img
Disk 2020-12-02-raspios-buster-armhf-lite.img: 1.7 GiB, 1858076672
bytes, 3629056 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0x067e19d7

Device                                    Boot  Start     End Sectors Size Id Type
2020-12-02-raspios-buster-armhf-lite.img1        8192  532479  524288 256M  c W95 FAT32 (LBA)
2020-12-02-raspios-buster-armhf-lite.img2      532480 3629055 3096576 1.5G 83 Linux
```

Mount the second partition. Because the file has 2 partitions, we need
to set the offset where the second starts: the start sector number
multiplied by the size of each sector in bytes.

```shell
$ sudo mount -v -o offset=$((532480* 512)) -t ext4 2020-12-02-raspios-buster-armhf-lite.img ~/mnt
```

Comment out any entry of `ld.so.preload` adding a `#` at the begin of
each line.
Why we need to do this? No idea. May be is related with
[this](https://stackoverflow.com/questions/45253755/why-is-the-stack-segment-executable-on-raspberry-pi)

```shell
$ cat ~/mnt/etc/ld.so.preload
/usr/lib/arm-linux-gnueabihf/libarmmem-${PLATFORM}.so

$ sudo sed -i 's/^.*$/#\0/' ~/mnt/etc/ld.so.preload
```


Check the `fstab`. Replace `/dev/mmcblk0p1` and
`/dev/mmcblk0p2` with `/dev/sda1` and `/dev/sda2`.

In my case there are not explicit names like `/dev/mmcblk0p1`. Instead,
there are UUIDs so I didn't touch them.

```
$ cat ~/mnt/etc/fstab
proc                  /proc    proc    defaults             0   0
PARTUUID=067e19d7-01  /boot    vfat    defaults             0   2
PARTUUID=067e19d7-02  /        ext4    defaults,noatime     0   1
```

We are done.

```shell
$ sudo umount ~/mnt
```

Now it is show time!

## Running the OS

```shell
$ qemu-system-arm                       \
  -M versatilepb                        \
  -cpu arm1176                          \
  -m 256                                \
  -drive "file=2020-12-02-raspios-buster-armhf-lite.img,if=none,index=0,media=disk,format=raw,id=disk0"  \
  -device "virtio-blk-pci,drive=disk0,disable-modern=on,disable-legacy=off"                              \
  -net "user,hostfwd=tcp::3022-:22"     \
  -dtb versatile-pb-buster-5.4.51.dtb   \
  -kernel kernel-qemu-5.4.51-buster     \
  -append 'root=/dev/vda2 panic=1'      \
  -no-reboot                            \
  -net nic                              \
  -nographic
```


Enable ssh (now and on boot); login with `pi`/`raspberry`. This will
allows us to upload/retrieve files to the vm and have additional
consoles.

```ssh
$ sudo service ssh start
$ sudo update-rc.d ssh enable
```

Now, from your host connect to the vm through the port 3020.

Install `gdbserver` for remote debugging:

```shell
sudo apt-get install gdbserver
Reading package lists... Done
Building dependency tree
Reading state information... Done
The following NEW packages will be installed:
  gdbserver
0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.
<...>
Preparing to unpack .../gdbserver_8.2.1-2_armhf.deb ...
Unpacking gdbserver (8.2.1-2) ...
Setting up gdbserver (8.2.1-2) ...
```

## Enlarge the disk

Optionally, you can expand the disk image to have more room for your
programs.

First, with QEMU turned off, expand the disk image

```shell
$ qemu-img resize 2020-12-02-raspios-buster-armhf-lite.img +1G
```

Now, turn on the vm and redefine the partition. In my case is the
partition number 2 (`/dev/vda2`):

```shell
pi@raspberrypi:~$ sudo fdisk /dev/vda

Welcome to fdisk (util-linux 2.33.1).
Changes will remain in memory only, until you decide to write them.
Be careful before using the write command.


Command (m for help): p
Disk /dev/vda: 2.7 GiB, 2931818496 bytes, 5726208 sectors
Units: sectors of 1 * 512 = 512 bytes
Sector size (logical/physical): 512 bytes / 512 bytes
I/O size (minimum/optimal): 512 bytes / 512 bytes
Disklabel type: dos
Disk identifier: 0x067e19d7

Device     Boot  Start     End Sectors  Size Id Type
/dev/vda1         8192  532479  524288  256M  c W95 FAT32 (LBA)
/dev/vda2       532480 3629055 3096576  1.5G 83 Linux

Command (m for help): d
Partition number (1,2, default 2): 2

Partition 2 has been deleted.

Command (m for help): n
Partition type
   p   primary (1 primary, 0 extended, 3 free)
   e   extended (container for logical partitions)
Select (default p): p
Partition number (2-4, default 2): 2
First sector (2048-5726207, default 2048): 532480
Last sector, +/-sectors or +/-size{K,M,G,T,P} (532480-5726207, default 5726207):

Created a new partition 2 of type 'Linux' and of size 2.5 GiB.
Partition #2 contains a ext4 signature.

Do you want to remove the signature? [Y]es/[N]o: n

Command (m for help): w

The partition table has been altered.
Syncing disks.
```

Note that `fdisk` offered by default the first sector to be 2048. This
is the space *before* `/dev/vda1` and it is too small, only 8kb.

Instead we want to start *after* `/dev/vda1`, in the same sector that
the original `/dev/vda2`: the 532480.

From there, to the end of the disk: 5726207.

With the partition expanded, reboot and then update the filesystem:

```shell
pi@raspberrypi:~$ sudo resize2fs /dev/vda2
resize2fs 1.44.5 (15-Dec-2018)
Filesystem at /dev/vda2 is mounted on /; on-line resizing required
old_desc_blocks = 1, new_desc_blocks = 1
The filesystem on /dev/vda2 is now 649216 (4k) blocks long.
```

## References

This tutorial setups a [Raspbian Jessie in Qemu](https://azeria-labs.com/emulate-raspberry-pi-with-qemu/).

I adapted the steps to use a modern Raspbian Buster image.

The tutorial is super complete and includes how to enlarge the disk and
setup the network.

But for the enlarge the disk part, this
[gist](https://gist.github.com/larsks/3933980) explains a little better.

