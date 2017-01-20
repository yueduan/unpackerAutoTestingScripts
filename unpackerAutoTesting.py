import subprocess, os 
import fcntl 
import time
import binascii
import sys
import shutil

###CONFIG BEGIN###

EMULATOR_PATH = "/home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate/"
SYS_DIR_PATH = "/home/yduan/yueduan/android-5.0.0_r3/out/target/product/generic"
KERNEL_FILE_PATH = "/home/yduan/yueduan/android-5.0.0_r3/android_art_kernel/goldfish/arch/arm/boot/zImage"
SYS_DIR_SRC_PATH = "/androidSysImages/"

PLUGIN_PATH = "/home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate/DECAF_plugins/old_dex_extarctor/libunpacker.so"
TEMP_RESULT_PATH = "/home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate/DECAF_plugins/old_dex_extarctor/out/"
RESULT_PATH = "/results/"
APP_PATH = "/test_apps/"

EXECUTION_TIME = 20

###CONFIG END#####


# added for cleanup when emulator crashes
crashed = False
curr_file = ""


# Given one directory, delete all its files and subdirectories
def cleanDir(path):
	for root, dirs, files in os.walk(path):
		for f in files:
			os.unlink(os.path.join(root, f))
		for d in dirs:
 			shutil.rmtree(os.path.join(root, d))

# Move all the files from directory 'pathSrc' to directory 'pathDst'
def moveAllFiles(pathSrc, pathDst):
	for root, dirs, files in os.walk(pathSrc):
		for f in files:
			src = os.path.join(pathSrc, f)
			dst = os.path.join(pathDst, f)
			os.rename(src, dst)

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
		#print s 
		if "unknown command: 'MARK'" in s: 
			break


def wait_start(proc):
	proc.stdin.write("ps\n")
	proc.stdin.write("MARK\n")
	while True:
		time.sleep(5)
		try:    
			s = proc.stdout.read()
		except Exception, e:
			continue
		if "unknown command: 'MARK'" in s:
			if "com.android.providers.calendar" in s:
				break
			else:
				proc.stdin.write("ps\n")
				proc.stdin.write("MARK\n")
	print "emulator ready"
	time.sleep(10)



def checkProcess(proc, name):
	proc.stdin.write("ps\n")
	proc.stdin.write("MARK\n")
	time.sleep(1)

	try:
		s = proc.stdout.read()
	except Exception, e:
		return 0
	if "unknown command: 'MARK'" in s:
		if name in s:
			#print "app launched"
			return 1
	return 0



def main():
	shutil.copyfile("/unpackerAutoTestingScripts/libunpacker.so", PLUGIN_PATH)
	cleanDir(RESULT_PATH)
	while ((os.listdir(APP_PATH) != [])):
		try:
			pl = subprocess.Popen(['ps', '-U', '0'], stdout=subprocess.PIPE).communicate()[0]
        		if not 'emulator' in pl:
				# move all system image files to the destination folder in order to run multiple docker containers in parallel
				moveAllFiles(SYS_DIR_SRC_PATH, SYS_DIR_PATH)
	
				# start droidscope   
				p = subprocess.Popen(args="sudo /home/yduan/yueduan/android-5.0.0_r3/external/droidscope_art_alternate/objs/emulator -no-audio -no-window -partition-size 1000 -sysdir /home/yduan/yueduan/android-5.0.0_r3/out/target/product/generic -kernel /home/yduan/yueduan/android-5.0.0_r3/android_art_kernel/goldfish/arch/arm/boot/zImage -memory 2048 -qemu -monitor stdio", stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
	 			fl = fcntl.fcntl(p.stdout, fcntl.F_GETFL)
 				fcntl.fcntl(p.stdout, fcntl.F_SETFL, fl | os.O_NONBLOCK)
 				time.sleep(5)
		
				# wait for the emulator to fully start
		 		input_cmd(p, "ps")
		 		wait_start(p)
				
				if crashed:
					crashed = False
					# clean up the app
					cmd = "/unpackerAutoTestingScripts/install_uninstall.sh {} 2".format(os.path.join(APP_PATH, curr_file))
					proc_uninstall = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					(output, err) = proc_uninstall.communicate()
					os.rename(os.path.join(APP_PATH, curr_file), os.path.join(RESULT_PATH, curr_file))
			else:
				print 'kill existing emulator first!'
				return
	
			# go over every file in APP_PATH, install the app, run it in emulator to analyze and then uninstall the app
		 	for dirname, dirnames, filenames in os.walk(APP_PATH):
				for filename in filenames:
					file_path = os.path.join(dirname, filename)
					curr_file = filename
					cmd = "/unpackerAutoTestingScripts/install_uninstall.sh {} 1".format(file_path)
					proc_install = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    					(output, err) = proc_install.communicate()
					print output
			
					# after installation, load the plugin
 					input_cmd(p, "load_plugin {plugin}".format(plugin=PLUGIN_PATH))
	
					# get package name of the app and hook the process
					packageName = subprocess.check_output(['/unpackerAutoTestingScripts/getPackageNameFromApk.sh',file_path])
					packageName = packageName[:-1]
					cmd = "do_hookapitests {}".format(packageName)
					input_cmd(p, cmd)
					

					# launch the app
					cmd = "/unpackerAutoTestingScripts/launch_KillApp.sh {} 1".format(file_path)
					proc_launch = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					(output, err) = proc_launch.communicate()
					#print output
	
					# let the app execute for certain time if it is successfully launched
					time.sleep(5)
					check_ret = checkProcess(p, packageName)
					if check_ret == 1:				
						time.sleep(EXECUTION_TIME)
	
					# unload the plugin and uninstall the app
					input_cmd(p, "unload_plugin")
			
					# clean up the app
					cmd = "/unpackerAutoTestingScripts/install_uninstall.sh {} 2".format(file_path)
					proc_uninstall = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					(output, err) = proc_uninstall.communicate()
					#print output
					
					# delete apk file after getting the packageName
					os.remove(file_path)	
	
					# move the result files into a specific folder
					result_path_new = RESULT_PATH + filename
					os.mkdir(result_path_new)
					moveAllFiles(TEMP_RESULT_PATH, result_path_new)
		except IOError as e:
			print "{} caused a crash!".format(curr_file)
			crashed = True
			continue


if __name__ == '__main__':
 	main()
