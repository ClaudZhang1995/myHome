#!/bin/bash
#
weekinfo=$1
num=$2
SOS_VERSION=$3
UOS_VERSION="30210"
echo "weekinfo:$weekinfo"
echo "num:$num"

waagPath="http://10.239.147.147/acrn_daily_build/2019$weekinfo/$num/WSL/waag"
isdPath="http://10.239.147.147/acrn_daily_build/2019$weekinfo/$num/WSL/wsl"
vxworksPath="http://10.239.147.147/acrn_daily_build/2019$weekinfo/$num/WSL/vxworks"

env(){
	
	if [  -z  $weekinfo  ];then
		echo "pleae add  weekinfo(ww26.3) as first parameter" &&  exit 1
	fi
	if [  -z  $num  ];then
		echo "plase add build times(1) as second parameter" && exit 1
	fi
	if [ -z $SOS_VERSION  ];then
		echo "no SOS_VERSION" 
	else
		swupd mirror -s http://linux-ftp.sh.intel.com/pub/mirrors/clearlinux/update 
		echo "swupd repair --picky -m $SOS_VERSION"
		swupd repair --picky -m $SOS_VERSION --force --allow-insecure-http || exit 1
		sed -i 's|\/home\/clear\/uos\/uos.img|\/root\/clear-'${UOS_VERSION}'-kvm.img|' /usr/share/acrn/samples/nuc/launch_uos.sh || exit 1
		cp /root/launch_hard_rt_vm.sh /usr/share/acrn/samples/nuc/ || exit 1
	fi

	weekday=`date +%w`
	week=$((10#`date +%W`+1))
	time=ww$week.$weekday
	echo "today is $time,mkdir it"
	mkdir -p preintegration
	cd preintegration
	rm -rf $time
	mkdir $time
	cd $time
	path=`pwd`
	umount /mnt
	mount /dev/sda1 /mnt  || exit 1
 	wget $isdPath/acrn.efi  &&  acrnefi=`md5sum acrn.efi`   || exit 1
	wget $isdPath/acrn-dm  && acrndm=`md5sum acrn-dm`  || exit 1
	wget $isdPath/sos_bzImage && sosbzImage=`md5sum sos_bzImage`  || exit 1
	wget $isdPath/sos_kernel.tar.gz  && tar xzf sos_kernel.tar.gz -C /lib/modules  || exit 1
	wget $isdPath/OVMF.fd && ovmffd=`md5sum OVMF.fd`  || exit 1
	wget $isdPath/launch_hard_rt_vm.sh  && chmod 777 launch_hard_rt_vm.sh   || exit 1
	wget $vxworksPath/launch_vxworks.sh && chmod 777 launch_vxworks.sh || exit 1
	wget $vxworksPath/VxWorks.img && VxWorksimg=`md5sum VxWorks.img` || exit 1
	wget $waagPath/launch_win.sh && chmod 777 launch_win.sh   || exit 1
	cd /mnt/EFI/acrn/  &&  mv acrn.efi acrn.efi.old
	cp $path/acrn.efi /mnt/EFI/acrn/acrn.efi  && acrnefi2=`md5sum acrn.efi`   || exit 1
	cd /usr/bin/ && mv acrn-dm acrn-dm.old
	cp $path/acrn-dm /usr/bin/acrn-dm  && acrndm2=`md5sum acrn-dm`  || exit 1
	chmod 777 /usr/bin/acrn-dm
	cd /mnt/EFI/org.clearlinux/ && mv sos_bzImage sos_bzImage.old
	cp $path/sos_bzImage /mnt/EFI/org.clearlinux/sos_bzImage   && sosbzImage2=`md5sum sos_bzImage`  || exit 1
	cd /root/vxworks/ &&  mv VxWorks.img VxWorks.img.old 
	cp $path/VxWorks.img ./&& VxWorksimg2=`md5sum VxWorks.img` || exit 1
	chmod 777 VxWorks.img
	cd /usr/share/acrn/bios/ && mv  OVMF.fd  OVMF.fd.old
	cp $path/OVMF.fd ./ && ovmffd2=`md5sum OVMF.fd` || exit 1
	cd /usr/share/acrn/samples/nuc &&  mv launch_hard_rt_vm.sh launch_hard_rt_vm.sh.old  
        cp $path/launch_hard_rt_vm.sh ./ 
	sed -i 's/$pm_channel/-s 4,virtio-net,tap1 \\\n  $pm_channel/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh || exit 1
	#sed -i 's/\/dev\/ttyS1"/\/dev\/ttyS1"\n ip tuntap add dev tap1 mode tap\n brctl addif acrn-br0 tap1\n ip link set dev tap1 down\n ip link set dev tap1 up/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh || exit 1
	#sed -i 's/default-iot-lts2018-preempt-rt/default-iot-lts2018-preempt-rt -U d2795438-25d6-11e8-864e-cb7a18b34643/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh || exit 1
	sed -i 's/hostbridge/hostbridge -U d2795438-25d6-11e8-864e-cb7a18b34643/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh
	sed -i 's/-U 495ae2e5-2603-4d64-af76-d4bc5a8ec0e5//g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh 
	sed -i 's/02:0.0/02:00.0/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh || exit 1
	sed -i 's/02\/0\/0/02\/00\/0/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh || exit 1
	sed -i 's/1024/512/g' /usr/share/acrn/samples/nuc/launch_hard_rt_vm.sh || exit 1
	cd /root/vxworks && mv launch_vxworks.sh launch_vxworks.sh.old 
	cp $path/launch_vxworks.sh ./ || exit 1
	sed -i 's/hostbridge/hostbridge -U 495ae2e5-2603-4d64-af76-d4bc5a8ec0e5/g' /root/vxworks/launch_vxworks.sh || exit 1
	sed -i 's/2048/1024/g' /root/vxworks/launch_vxworks.sh || exit 1
	sed -i 's/1024/512/g' /root/vxworks/launch_vxworks.sh || exit 1
	cd /root/waag && mv launch_win.sh launch_win.sh.old 
	cp $path/launch_win.sh ./  || exit 1
	sed -i 's/tap0/tap0,mac=00:16:3E:AF:06:03/g' /root/waag/launch_win.sh || exit 1
	sed -i 's/stdio/stdio -U 38158821-5208-4005-b72a-8a609e4190d0/g' /root/waag/launch_win.sh  || exit 1
	sed -i 's/4096/1024/g' /root/waag/launch_win.sh
	sed -i 's/\/home\/clear\/uos\/uos.img/\/root\/clear-31300-kvm.img/g' /usr/share/acrn/samples/nuc/launch_uos.sh 
	cd ~ && umount /mnt && sync
	echo "download"
	echo "acrn.efi:$acrnefi"
    echo "acrn-dm:$acrndm"
    echo "sos_bzImage:$sosbzImage"
	echo "OVMF.fd:$ovmffd"
	echo "VxWorks.img:$VxWorksimg"
	
	echo "local"
	echo "acrn.efi:$acrnefi2"
	echo "acrn-dm:$acrndm2"
	echo "sos_bzImage:$sosbzImage2"
	echo "OVMF.fd:$ovmffd2"
	echo "VxWorks.img:$VxWorksimg2"

	if [[ $VxWorksimg == $VxWorksimg2  ]]  &&  [[ $acrnefi == $acrnefi2 ]] && [[ $acrndm == $acrndm2 ]]  &&  [[ $sosbzImage == $sosbzImage2 ]] && [[ $ovmffd == $ovmffd2   ]]   ;then
		echo "env set successfully"
	else
		echo "md5sum check error" &&  exit 1
	fi
}


env
