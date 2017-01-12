import subprocess, os 
import fcntl 
import time
import binascii
import sys

###CONFIG BEGIN###

EMULATOR_PATH = "/home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate"
SYS_DIR_PATH = "/home/yduan/yueduan/android-5.0.0_r3/out/target/product/generic"
KERNEL_FILE_PATH = "/home/yduan/yueduan/android-5.0.0_r3/android_art_kernel/goldfish/arch/arm/boot/zImage"
PLUGIN_PATH = "/home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate/DECAF_plugins/old_dex_extarctor/libunpacker.so"
APP_PATH = "/test_apps/"

EXECUTION_TIME = 20

###CONFIG END#####

def input_cmd(p, cmd): 
	if not cmd.endswith("\n"): 
		cmd += "\n" 
	p.stdin.write(cmd) 
	p.stdin.write("MARK\n") 
	while True: 
		time.sleep(0.1) 
		try: 
			s = p.stdout.read() 
 		except Exception, e:
			continue 
		print s 
		if "unknown command: 'MARK'" in s: 
			break


def wait_start(proc):
	proc.stdin.write("ps\n")
	proc.stdin.write("MARK\n")
	while True:
		time.sleep(0.1)
		try:    
			s = proc.stdout.read()
		except Exception, e:
			continue
		if "unknown command: 'MARK'" in s:
			if "com.android.managedprovisioning" in s:
				break
			else:
				proc.stdin.write("ps\n")
				proc.stdin.write("MARK\n")
	print "emulator ready"
	time.sleep(10)



def main():
	try:
		# start droidscope   
		p = subprocess.Popen(args="sudo /home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate/objs/emulator -no-audio -no-window -partition-size 1000 -sysdir /home/yduan/yueduan/android-5.0.0_r3/out/target/product/generic -kernel /home/yduan/yueduan/android-5.0.0_r3/android_art_kernel/goldfish/arch/arm/boot/zImage -memory 2048 -qemu -monitor stdio", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
 		fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
 		fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
 		time.sleep(5)
	
		# wait for the emulator to fully start
	 	input_cmd(p, "ps")
	 	wait_start(p)
	
		# go over every file in APP_PATH, install the app, run it in emulator to analyze and then uninstall the app
	 	for dirname, dirnames, filenames in os.walk(APP_PATH):
			for filename in filenames:
				file_path = os.path.join(dirname, filename)
				print "Installing: " + file_path
				cmd = "/install_uninstall.sh {} 1".format(file_path)
				proc_install = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    				(output, err) = proc_install.communicate()
				print output
					
				# after installation, load the plugin
				print "Loading plugin"
 				input_cmd(p, "load_plugin {plugin}".format(plugin=PLUGIN_PATH))

				# get package name of the app and hook the process
				out = subprocess.check_output(['/getPackageNameFromApk.sh',file_path])
				cmd = "do_hookapitests {}".format(out)
				input_cmd(p, cmd)
		
				# launch the app
				print "Launching the app"
				cmd = "/launch_KillApp.sh {} 1".format(file_path)
				proc_launch = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				(output, err) = proc_launch.communicate()
					
				input_cmd(p,"ps")
				# let the app execute for certain time
				time.sleep(EXECUTION_TIME)

				# unload the plugin and uninstall the app
				print "unloading plugin"
				input_cmd(p, "unload_plugin")
		
				# clean up the app
				print "Uninstalling: " + file_path
				cmd = "/install_uninstall.sh {} 2".format(file_path)
				proc_uninstall = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				(output, err) = proc_uninstall.communicate()
				print output
	except IOError as e:
		print "I/O error({0}): {1}".format(e.errno, e.strerror)
	except:
		print "Unexpected error:", sys.exc_info()[0]
		raise


if __name__ == '__main__':
 	main()
