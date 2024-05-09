#!/bin/bash
# used for debugging a problematic nvidia udev configuration

echo $(grep nvidia-uvm /proc/devices | cut -d ' ' -f 1)

[ -c /dev/nvidiactl ] || mknod -Z -m 666 /dev/nvidiactl c $(grep nvidia-frontend /proc/devices | cut -d ' ' -f 1) 255

for i in $(cat /proc/driver/nvidia/gpus/*/information | grep Minor | cut -d ' ' -f 4); do
    [ -c /dev/nvidia$i ] || mknod -Z -m 666 /dev/nvidia${i} c $(grep nvidia-frontend /proc/devices | cut -d ' ' -f 1) ${i}
done

[ -c /dev/nvidia-modeset ] || mknod -Z -m 666 /dev/nvidia-modeset c $(grep nvidia-frontend /proc/devices | cut -d ' ' -f 1) 254
[ -c /dev/nvidia-uvm ] || mknod -Z -m 666 /dev/nvidia-uvm c $(grep nvidia-uvm /proc/devices | cut -d ' ' -f 1) 0
[ -c /dev/nvidia-uvm-tools ] || mknod -Z -m 666 /dev/nvidia-uvm-tools c $(grep nvidia-uvm /proc/devices | cut -d ' ' -f 1) 1
