#!/bin/bash

file=$1
install=$2

filename=$(basename $file)

if [ "$install" = "1" ] 
then
	#echo installing $filename
	adb shell setprop dalvik.vm.dex2oat-filter "interpret-only"
	adb shell setprop dalvik.vm.image-dex2oat-filter "interpret-only"
	adb install $file
elif [ "$install" = "2" ]
then
	#echo uninstalling $filename
	packageName=$(aapt dump badging $file | awk -v FS="'" '/package: name=/{print $2}')
	adb shell pm uninstall -k $packageName
fi
