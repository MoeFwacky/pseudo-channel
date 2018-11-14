#!/bin/bash
# file: update-channels-from-git.sh

#----
# Simple script to update every channel with updates from the github repo. 
# BACKUP EACH XML/DB IN EACH CHANNEL.
# Code will take in one argument: To take from the master or development branch
# For ALL installs, simply place this file in the location you would like your channels to be installed/updated
#----

#---- 
# To Use:
# chmod +x update-channels-from-git.sh
# ./update-channels-from-git.sh
#----

#----BEGIN EDITABLE VARS----
if [ $# -gt 1 ]; then
	echo "ERROR: Please only supply one argument"
	exit 9999
elif [ "$1" == "develop" ]; then
	echo "Downloading the develop branch"
	SCRIPT_TO_EXECUTE_PLUS_ARGS='git clone https://github.com/mutto233/pseudo-channel . --branch develop'

else
	echo "Downloading the master branch"
	SCRIPT_TO_EXECUTE_PLUS_ARGS='git clone https://github.com/mutto233/pseudo-channel . --branch master'
fi

OUTPUT_PREV_CHANNEL_PATH=.

CHANNEL_DIR_INCREMENT_SYMBOL="_"

# This does a check for the pseudo-channel_## directories that manage each channel.
# As this script generates those directories on first run, if those directories do
# not exist, then logically this is the first run.
FIND_CHANNEL_FOLDER=''
FIND_CHANNEL_FOLDERS=$(find ./ -name "pseudo-channel_*" -type d)
if [[ "$FIND_CHANNEL_FOLDERS" == '' ]]
	then
		FIRST_INSTALL=true
	else
		FIRST_INSTALL=false
fi


#----END EDITABLE VARS-------



# First, we need to figure out if we have actually installed this already
# To do this, we are going to check if we go up one level we have the folder "channels"
# We will also check if the current directory has "channels"
# FIRST_INSTALL=true

# if [ -d "$INSTALL_FOLDER" ] || [ -d "../$INSTALL_FOLDER" ]; then
	# echo "This is NOT the first install"
	# FIRST_INSTALL=false
# else
	# echo "This IS the first install, installing 'channels' directory in current directory with five starting channels."
	# FIRST_INSTALL=true
# fi


# If this is our first install, we will now make all necessary directories to prepare for install
if [ "$FIRST_INSTALL" == "true" ]; then
echo "This is a FIRST INSTALL, ENTER the NUMBER of PSEUDO CHANNELS to SET UP"
read -p 'Number of Channels: ' number_of_channels
	if (( $number_of_channels >= 1 ))
	then
	entry_is_number=yes
	else
	entry_is_number=no
	fi
	while [[ $entry_is_number == "no" ]]
	do
		echo "Enter the number of channels you would like this script to generate?"
		read -p 'Number of Channels: ' number_of_channels
		if (( $number_of_channels >= 1 ))
		then
		entry_is_number=yes
		else
		entry_is_number=no
		fi
	done
	for (( num=1; num<="$number_of_channels"; num++ ))
	do
		if [ $num -ge 1 -a $num -le 9 ]
		then
		mkdir "pseudo-channel_0$num"
		else
		mkdir "pseudo-channel_$num"
		fi
	done
fi


#### Next, let's download the latest master version of information from GitHub and store it in a temporary folder
mkdir github_download
cd github_download
$SCRIPT_TO_EXECUTE_PLUS_ARGS

#### If necessary, install the required elements as defined by requirements.txt
#### Also, ask user for information to fill in the plex_token and pseudo_config files
if [ "$FIRST_INSTALL" == "true" ]
	then
	echo "INSTALLING REQUIREMENTS because this is a FIRST RUN"
	sudo pip install -r requirements.txt
	sudo apt-get -y install libxml2-utils recode # NEEDED FOR XML PARSING
	cd ..
	echo "ENTER the IP ADDRESS of your PLEX SERVER" #GET PLEX SERVER IP AND PORT
	read -p 'Plex Server IP: ' server_ip
	echo "ENTER the PUBLIC PORT number for your PLEX SERVER"
	read -p 'Public Port (default: 32400): ' server_port
	if [ "$server_port" == '' ]
		then
		server_port='32400'
	fi
	echo "ENTER your PLEX AUTHENTICATION TOKEN" # GET PLEX SERVER AUTH TOKEN
	echo "(for help finding token, check here: https://bit.ly/2p7RtOu)"
	read -p 'Plex Auth Token: ' server_token
	echo "PLEX SERVER is $server_ip:$server_port"
	echo "PLEX AUTH TOKEN is $server_token"
	echo "SELECT the PLEX CLIENT for this install or ENTER one manually"
	# DISPLAY A LIST OF CONNECTED CLIENTS AND ALLOW THE USER TO SELECT ONE OR ENTER ONE THAT ISN'T DISPLAYED
	clientlist=$(xmllint --xpath "//Server/@name" "http://$server_ip:$server_port/clients" | sed "s|name=||g" | sed "s|^ ||g" && echo -e " Other")
	eval set $clientlist
	select ps_client_entry in "$@"
		do
		if [[ "$ps_client_entry" == "Other" ]]
			then
			read -p 'Client Name: ' ps_client_entry
			ps_client_entry=$(eval echo $ps_client_entry)
		fi
			ps_client="[\"$ps_client_entry\"]"
			break
		done
	# ALLOW THE USER TO ENTER ALL PLEX LIBRARIES
	echo "++++++SETTING UP PLEX LIBRARIES WITH PSEUDO CHANNEL++++++"
        echo "Add ALL LIBRARIES that may be used for ANY CHANNEL here."
	echo "ENTER the name of EACH Plex library defined as TV SHOWS"
	enter_tv_shows=yes
	echo -n "[" > tv-libraries.temp
	while [[ "$enter_tv_shows" == @(Y|y|Yes|yes|YES) ]]
		do
			read -p 'TV Show Library Name: ' tv_library_entry
			echo -n "\"$tv_library_entry\"" >> tv-libraries.temp
			echo "ENTER another TV SHOW LIBRARY?"
			read -p 'Y/N: ' enter_tv_shows
			while [[ "$enter_tv_shows" != @(Y|y|Yes|yes|YES|N|n|No|no|NO) ]]
				do
				echo "ENTER another TV SHOW LIBRARY?"
				read -p 'Y/N: ' enter_tv_shows
				done
			if [[ "$enter_tv_shows" == @(Y|y|Yes|yes|YES) ]]
				then
				echo -n ", " >> tv-libraries.temp
			fi
		done
	echo -n "]," >> tv-libraries.temp
	echo "ENTER the name of EACH Plex library defined as MOVIES"
	enter_movies=yes
	echo -n "[" > movie-libraries.temp
	while [[ "$enter_movies" == @(Y|y|Yes|yes|YES) ]]
		do
			read -p 'Movie Library Name: ' movie_library_entry
			echo -n "\"$movie_library_entry\"" >> movie-libraries.temp
			echo "ENTER another MOVIE LIBRARY?"
			read -p 'Y/N: ' enter_movies
			while [[ "$enter_movies" != @(Y|y|Yes|yes|YES|N|n|No|no|NO) ]]
				do
				echo "ENTER another MOVIE LIBRARY?"
				read -p 'Y/N: ' enter_movies
				done
			if [[ "$enter_movies" == @(Y|y|Yes|yes|YES) ]]
				then
				echo -n ", " >> movie-libraries.temp
			fi
		done
	echo -n "]," >> movie-libraries.temp
	echo "Use COMMERCIALS in between scheduled content?" # ASK IF THE USER WANTS TO ADD COMMERCIAL LIBRARIES
	read -p 'Y/N: ' enter_commercials
	while [[ "$enter_commercials" != @(Y|y|Yes|yes|YES|N|n|No|no|NO) ]]
		do
		echo "Use COMMERCIALS in between scheduled content?"
		read -p 'Y/N: ' enter_commercials
		done
	if [[ "$enter_commercials" == @("Y"|"y"|"yes"|"Yes"|"YES") ]]
		then
		commercials_true=True
		echo "ENTER the name of EACH Plex library defined as COMMERCIALS"
		echo -n "[" > commercial-libraries.temp
		else
		commercials_true=False
	fi
		while [[ "$enter_commercials" == @(Y|y|Yes|yes|YES) ]]
			do
				read -p 'Commercial Library Name: ' commercial_library_entry
				echo -n "\"$commercial_library_entry\", " >> commercial-libraries.temp
				echo "ENTER another COMMERCIAL LIBRARY?"
				read -p 'Y/N: ' enter_commercials
				while [[ "$enter_commercials" != @(Y|y|Yes|yes|YES|N|n|No|no|NO) ]]
					do
					echo "ENTER another COMMERCIAL LIBRARY?"
					read -p 'Y/N: ' enter_commercials
					done
			done
	if [[ "$commercials_true" == "True" ]]
		then
		truncate -s-2 commercial-libraries.temp
		echo -n "]," >> commercial-libraries.temp
	fi
	# DEFINE THE DAILY RESET TIME
	echo "Set the TIME for PSEUDO CHANNEL to GENERATE the DAILY SCHEDULE"
	echo "USE 24H FORMAT (ex: 23:00)"
	read -p 'Schedule Reset Time: ' reset_time_entry
	reset_time_formatted=$(echo $reset_time_entry | sed -e "s|^[0-9]:.*|0$reset_time_entry|g")
	reset_time_hour="${reset_time_formatted:0:2}"
	reset_time_hour=$(echo $reset_time_hour | sed -e "s|^[0]||")
	reset_time_minute="${reset_time_formatted: -2}"
	reset_time_minute=$(echo $reset_time_minute | sed "-e s|^[0]||")
	# SET UP CRON JOB TO RUN DAILY RESET
	sudo crontab -l | grep -v 'daily-cron.sh' | crontab -
	sudo echo \#\!/bin/bash > ./daily-cron.sh && echo "cd $PWD" >> ./daily-cron.sh && echo "sudo ./generate-channels-daily-schedules.sh" >> ./daily-cron.sh
	( sudo crontab -l ; echo "$reset_time_minute $reset_time_hour * * * $PWD/daily-cron.sh" ) | sudo crontab -

	#### WRITE VARIABLES TO TOKEN AND CONFIG FILES ####
	reset_time="\"$reset_time_entry\""
	echo "token = '$server_token'" > plex_token.py # WRITE PLEX SERVER TOKEN TO FILE
	echo "baseurl = 'http://$server_ip:$server_port'" >> plex_token.py # WRITE PLEX URL TO FILE
	tv_libraries=$(cat tv-libraries.temp)
	sudo sed -i "s/plexClients = .*/plexClients = $ps_client/" github_download/both-dir/pseudo_config.py # WRITE CLIENT TO CONFIG
	sudo sed -i "/.\"TV Shows\" :*./c\     \"TV Shows\" : $tv_libraries" github_download/both-dir/pseudo_config.py # WRITE TV LIBRARIES TO CONFIG
	movie_libraries=$(cat movie-libraries.temp)
	sudo sed -i "/.\"Movies\" :*./c\     \"Movies\"   : $movie_libraries" github_download/both-dir/pseudo_config.py # WRITE MOVIE LIBRARIES TO CONFIG
	if [[ "$commercials_true" == "True" ]] #WRITE COMMERCIAL LIBRARIES TO CONFIG
		then
		commercial_libraries=$(cat commercial-libraries.temp)
		sudo sed -i "/.\"Commercials\" :*./c\     \"Commercials\" : $commercial_libraries" github_download/both-dir/pseudo_config.py
	fi
	# WRITE OTHER CONFIG OPTIONS TO THE CONFIG FILE
	sudo sed -i "s/useCommercialInjection =.*/useCommercialInjection = $commercials_true/" github_download/both-dir/pseudo_config.py
	sudo sed -i "s/dailyUpdateTime =.*/dailyUpdateTime = $reset_time/" github_download/both-dir/pseudo_config.py
	sudo sed -i "s/controllerServerPath =.*/controllerServerPath = \"\"/" github_download/both-dir/pseudo_config.py
	sudo sed -i "s/controllerServerPort =.*/controllerServerPort = \"\"/" github_download/both-dir/pseudo_config.py
	sudo sed -i "s/debug_mode =.*/debug_mode = False/" github_download/both-dir/pseudo_config.py
	# CLEAN UP TEMP FILES AND COPY CONFIG
	sudo rm movie-libraries.temp
	sudo rm tv-libraries.temp
	sudo rm commercial-libraries.temp
	sudo cp github_download/both-dir/pseudo_config.py ./
	sudo cp github_download/both-dir/PseudoChannel.py ./
	else
	cd ..
fi

#### With information downloaded, we will first go to each channel folder and update important things
#### This will take the following form
#### - Enter folder
#### - Copy database, xml, and config file to temporary folder
#### - copy all files from the download/channel-dir and download/both-dir to the channel folder.
#### - Replace files that were originally removed

# Scan the dir to see how many channels there are, store them in an arr.
CHANNEL_DIR_ARR=( $(find . -maxdepth 1 -type d -name '*'"$CHANNEL_DIR_INCREMENT_SYMBOL"'[[:digit:]]*' -printf "%P\n" | sort -t"$CHANNEL_DIR_INCREMENT_SYMBOL" -n) )

if [ "${#CHANNEL_DIR_ARR[@]}" -gt 1 ]; then
	echo "+++++ There are ${#CHANNEL_DIR_ARR[@]} channels detected."
	for channel in "${CHANNEL_DIR_ARR[@]}"
	do
		echo "+++++ Trying to update channel:"./"$channel"
		cd "$channel"

		# Export critical files
		mkdir ../.pseudo-temp
		does_pseudo_temp_exist=yes

		cp ./pseudo-channel.db ../.pseudo-temp 2>/dev/null

		cp ./pseudo_schedule.xml ../.pseudo-temp 2>/dev/null

		cp ./pseudo_config.py ../.pseudo-temp 2>/dev/null

		# Copy new elements

		cp -r ../github_download/channel-dir/* .
		cp -r ../github_download/both-dir/* .

		# Replace the files originally moved

		cp ../.pseudo-temp/pseudo-channel.db . 2>/dev/null

		cp ../.pseudo-temp/pseudo_schedule.xml . 2>/dev/null

		cp ../.pseudo-temp/pseudo_config.py . 2>/dev/null

		rm -rf ../.pseudo-temp

		cd ..
	done
fi

#### Now we will return to the original file, and ensure that everything is in the main folder
#### This will include the following form
#### - Return to folder
#### - Copy config, db, and token file
#### - Copy relevant files from github
#### - Replace files originally removed
echo "Updating channels folder"

#Export critical files
if [[ "$does_pseudo_temp_exist" != yes ]]
	then
		mkdir .pseudo-temp
fi

cp ./pseudo-channel.db .pseudo-temp 2>/dev/null

cp ./pseudo_config.py .pseudo-temp 2>/dev/null

cp ./plex_token.py .pseudo-temp 2>/dev/null

# Copy new elements

cp -r ./github_download/main-dir/* .
cp -r ./github_download/both-dir/* .

# Replace the files originally moved

cp ./.pseudo-temp/pseudo-channel.db . 2>/dev/null

cp ./.pseudo-temp/pseudo_config.py . 2>/dev/null

cp ./.pseudo-temp/plex_token.py  . 2>/dev/null

rm -rf ./.pseudo-temp

rm -rf ./github_download

#### Change permissions to 777 for all files, so that things will run
sudo chmod -R 777 .

echo "Update Complete"

#### Write variables to config.cache
sudo sed -i "s/server_ip=.*/server_ip=$server_ip/" config.cache
sudo sed -i "s/server_port=.*/server_port=$server_port/" config.cache
sudo sed -i "s/server_token=.*/server_token=$server_token/" config.cache
