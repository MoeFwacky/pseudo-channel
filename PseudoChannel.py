#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src import PseudoChannelDatabase
from src import Movie
from src import Commercial
from src import Episode
from src import Music
from src import Video
from src import PseudoDailyScheduleController
from src import GoogleCalendar
from src import PseudoChannelCommercial

from plexapi.server import PlexServer

import sys
import datetime
from datetime import time
import calendar
import itertools
import argparse
import textwrap
from xml.dom import minidom
import xml.etree.ElementTree as ET

from threading import Timer
import signal

from time import sleep

import pseudo_config as config

reload(sys)
sys.setdefaultencoding('utf-8')

class PseudoChannel():

    PLEX = PlexServer(config.baseurl, config.token)
    MEDIA = []
    GKEY = config.gkey

    USING_GOOGLE_CALENDAR = config.useGoogleCalendar

    USING_COMMERCIAL_INJECTION = config.useCommercialInjection

    DAILY_UPDATE_TIME = config.dailyUpdateTime

    APP_TIME_FORMAT_STR = '%I:%M:%S %p'

    DEBUG = config.debug_mode

    def __init__(self):

        self.db = PseudoChannelDatabase("pseudo-channel.db")

        self.controller = PseudoDailyScheduleController(
            config.baseurl, 
            config.token, 
            config.plexClients,
            self.DEBUG
        )

    """Database functions.

        update_db(): Grab the media from the Plex DB and store it in the local pseudo-channel.db.

        drop_db(): Drop the local database. Fresh start. 

        update_schedule(): Update schedule with user defined times.

        drop_schedule(): Drop the user defined schedule table. 

        generate_daily_schedule(): Generates daily schedule based on the "schedule" table.
    """

    # Print iterations progress
    def print_progress(self, iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
        """
        Call in a loop to create terminal progress bar
        @params:
            iteration   - Required  : current iteration (Int)
            total       - Required  : total iterations (Int)
            prefix      - Optional  : prefix string (Str)
            suffix      - Optional  : suffix string (Str)
            decimals    - Optional  : positive number of decimals in percent complete (Int)
            bar_length  - Optional  : character length of bar (Int)
        """
        str_format = "{0:." + str(decimals) + "f}"
        percents = str_format.format(100 * (iteration / float(total)))
        filled_length = int(round(bar_length * iteration / float(total)))
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

        if iteration == total:
            sys.stdout.write('\n')
        sys.stdout.flush()

    def update_db(self):

        print("#### Updating Local Database")

        self.db.create_tables()

        libs_dict = config.plexLibraries

        sections = self.PLEX.library.sections()

        for section in sections:

            for correct_lib_name, user_lib_name in libs_dict.items():

                if section.title.lower() in [x.lower() for x in user_lib_name]:

                    if correct_lib_name == "Movies":

                        sectionMedia = self.PLEX.library.section(section.title).all()

                        for i, media in enumerate(sectionMedia):

                            self.db.add_movies_to_db(1, media.title, media.duration, media.key)

                            self.print_progress(
                                    i + 1, 
                                    len(sectionMedia), 
                                    prefix = 'Progress '+section.title+":     ", 
                                    suffix = 'Complete', 
                                    bar_length = 40
                                )


                    elif correct_lib_name == "TV Shows":

                        sectionMedia = self.PLEX.library.section(section.title).all()

                        for i, media in enumerate(sectionMedia):

                            backgroundImagePath = self.PLEX.library.section(section.title).get(media.title)

                            backgroundImgURL = ''

                            if isinstance(backgroundImagePath.art, str):

                                backgroundImgURL = config.baseurl+backgroundImagePath.art+"?X-Plex-Token="+config.token

                            self.db.add_shows_to_db(2, media.title, media.duration, '', backgroundImgURL, media.key)

                            self.print_progress(
                                    i + 1, 
                                    len(sectionMedia),
                                    prefix = 'Progress '+section.title+":   ", 
                                    suffix = 'Complete', 
                                    bar_length = 40
                                )

                            #add all episodes of each tv show to episodes table
                            episodes = self.PLEX.library.section(section.title).get(media.title).episodes()

                            for episode in episodes:

                                duration = episode.duration

                                if duration:

                                    self.db.add_episodes_to_db(
                                            4, 
                                            episode.title, 
                                            duration, 
                                            episode.index, 
                                            episode.parentIndex, 
                                            media.title,
                                            episode.key
                                        )

                                else:

                                    self.db.add_episodes_to_db(
                                            4, 
                                            episode.title, 
                                            0, 
                                            episode.index, 
                                            episode.parentIndex, 
                                            media.title,
                                            episode.key
                                        )

                    elif correct_lib_name == "Commercials":

                        sectionMedia = self.PLEX.library.section(section.title).all()

                        media_length = len(sectionMedia)

                        for i, media in enumerate(sectionMedia):

                            self.db.add_commercials_to_db(3, media.title, media.duration, media.key)

                            self.print_progress(
                                i + 1, 
                                media_length, 
                                prefix = 'Progress '+section.title+":", 
                                suffix = 'Complete', 
                                bar_length = 40
                            )

    def update_schedule_from_google_calendar(self):

        self.gcal = GoogleCalendar(self.GKEY)

        events = self.gcal.get_entries()

        self.db.create_tables()

        self.db.remove_all_scheduled_items()

        scheduled_days_list = [
            "mondays",
            "tuesdays",
            "wednesdays",
            "thursdays",
            "fridays",
            "saturdays",
            "sundays",
            "weekdays",
            "weekends",
            "everyday"
        ]

        section_dict = {
            "TV Shows" : ["series", "shows", "tv", "episodes", "tv shows", "show"],
            "Movies"   : ["movie", "movies", "films", "film"],
            "Videos"   : ["video", "videos", "vid"],
            "Music"    : ["music", "songs", "song", "tune", "tunes"]
        }

        weekday_dict = {
            "0" : ["mondays", "weekdays", "everyday"],
            "1" : ["tuesdays", "weekdays", "everyday"],
            "2" : ["wednesdays", "weekdays", "everyday"],
            "3" : ["thursdays", "weekdays", "everyday"],
            "4" : ["fridays", "weekdays", "everyday"],
            "5" : ["saturdays", "weekends", "everyday"],
            "6" : ["sundays", "weekends", "everyday"],
        }

        for event in events:

            titlelist = [x.strip() for x in event['summary'].split(',')]

            start = event['start'].get('dateTime', event['start'].get('date'))

            s = datetime.datetime.strptime(start,"%Y-%m-%dT%H:%M:%S-07:00")

            weekno = s.weekday()

            for key, value in section_dict.items():

                if str(titlelist[0]).lower() == key or str(titlelist[0]).lower() in value:

                    print "Adding {} to schedule.".format(titlelist[1])

                    title = titlelist[1]

                    # s.strftime('%I:%M'), event["summary"]
                    natural_start_time = self.translate_time(s.strftime(self.APP_TIME_FORMAT_STR))

                    natural_end_time = 0

                    section = key

                    for dnum, daylist in weekday_dict.items():

                        #print int(weekno), int(dnum)

                        if int(weekno) == int(dnum):

                            day_of_week = daylist[0]

                    strict_time = titlelist[2] if len(titlelist) > 2 else "true"

                    #strict_time = "true"

                    time_shift = "5"

                    overlap_max = ""

                    print natural_start_time

                    start_time_unix = datetime.datetime.strptime(
                            self.translate_time(natural_start_time), 
                            '%I:%M:%S %p').strftime('%Y-%m-%d %H:%M:%S')

                    #print "Adding: ", time.tag, section, time.text, time.attrib['title']

                    self.db.add_schedule_to_db(
                        0, # mediaID
                        title, # title
                        0, # duration
                        natural_start_time, # startTime
                        natural_end_time, # endTime
                        day_of_week, # dayOfWeek
                        start_time_unix, # startTimeUnix
                        section, # section
                        strict_time, # strictTime
                        time_shift, # timeShift
                        overlap_max, # overlapMax
                    )

    def update_schedule(self):

        self.db.create_tables()

        self.db.remove_all_scheduled_items()

        scheduled_days_list = [
            "mondays",
            "tuesdays",
            "wednesdays",
            "thursdays",
            "fridays",
            "saturdays",
            "sundays",
            "weekdays",
            "weekends",
            "everyday"
        ]

        section_dict = {
            "TV Shows" : ["series", "shows", "tv", "episodes", "tv shows", "show"],
            "Movies"   : ["movie", "movies", "films", "film"],
            "Videos"   : ["video", "videos", "vid"],
            "Music"    : ["music", "songs", "song", "tune", "tunes"]
        }

        tree = ET.parse('pseudo_schedule.xml')

        root = tree.getroot()

        for child in root:

            if child.tag in scheduled_days_list:

                for time in child.iter("time"):

                    for key, value in section_dict.items():

                        if time.attrib['type'] == key or time.attrib['type'] in value:

                            title = time.attrib['title']

                            natural_start_time = self.translate_time(time.text)

                            natural_end_time = 0

                            section = key

                            day_of_week = child.tag

                            strict_time = time.attrib['strict-time']

                            time_shift = time.attrib['time-shift']

                            overlap_max = time.attrib['overlap-max']

                            start_time_unix = self.translate_time(time.text)

                            print "Adding: ", time.tag, section, time.text, time.attrib['title']

                            self.db.add_schedule_to_db(
                                0, # mediaID
                                title, # title
                                0, # duration
                                natural_start_time, # startTime
                                natural_end_time, # endTime
                                day_of_week, # dayOfWeek
                                start_time_unix, # startTimeUnix
                                section, # section
                                strict_time, # strictTime
                                time_shift, # timeShift
                                overlap_max, # overlapMax
                            )

    def drop_db(self):

        self.db.drop_db()

    def drop_schedule(self):

        self.db.drop_schedule()

    def remove_all_scheduled_items():

        self.db.remove_all_scheduled_items()



    """App functions.

        generate_daily_schedule(): Generate the daily_schedule table.
    """

    '''
    *
    * Using datetime to figure out when the media item will end based on the scheduled start time or the offset 
    * generated by the previous media item. 

    * Returns time 
    *
    '''
    '''
    *
    * Returns time difference in minutes
    *
    '''

    def translate_time(self, timestr):

        try:

            return datetime.datetime.strptime(timestr, '%I:%M %p').strftime(self.APP_TIME_FORMAT_STR)

        except ValueError as e:

            pass

        try:

            return datetime.datetime.strptime(timestr, '%I:%M:%S %p').strftime(self.APP_TIME_FORMAT_STR)

        except ValueError as e:

            pass

        try:

            return datetime.datetime.strptime(timestr, '%H:%M').strftime(self.APP_TIME_FORMAT_STR)

        except ValueError as e:

            pass

        return timestr

    def time_diff(self, time1,time2):
        '''
        *
        * Getting the offest by comparing both times from the unix epoch time and getting the difference.
        *
        '''
        timeA = datetime.datetime.strptime(time1, '%I:%M:%S %p')
        timeB = datetime.datetime.strptime(time2, '%I:%M:%S %p')
        
        timeAEpoch = calendar.timegm(timeA.timetuple())
        timeBEpoch = calendar.timegm(timeB.timetuple())

        tdelta = abs(timeAEpoch) - abs(timeBEpoch)

        return int(tdelta/60)


    '''
    *
    * Passing in the endtime from the prev episode and desired start time of this episode, calculate the best start time 

    * Returns time - for new start time
    *
    '''
    def calculate_start_time(self, prevEndTime, intendedStartTime, timeGap, overlapMax):

        self.TIME_GAP = timeGap

        self.OVERLAP_GAP = timeGap

        self.OVERLAP_MAX = overlapMax

        time1 = prevEndTime.strftime('%I:%M:%S %p')

        timeB = datetime.datetime.strptime(intendedStartTime, '%I:%M:%S %p').strftime(self.APP_TIME_FORMAT_STR)

        print "++++ Previous End Time: ", time1, "Intended start time: ", timeB

        timeDiff = self.time_diff(time1, timeB)

        """print("timeDiff "+ str(timeDiff))
        print("startTimeUNIX: "+ str(intendedStartTime))"""

        newTimeObj = timeB

        newStartTime = timeB

        '''
        *
        * If time difference is negative, then we know there is overlap
        *
        '''
        if timeDiff < 0:
            '''
            *
            * If there is an overlap, then the overlapGap var in config will determine the next increment. If it is set to "15", then the show will will bump up to the next 15 minute interval past the hour.
            *
            '''
            timeset=[datetime.time(h,m).strftime("%H:%M") for h,m in itertools.product(xrange(0,24),xrange(0,60,int(self.OVERLAP_GAP)))]
            
            #print(timeset)

            timeSetToUse = None

            for time in timeset:

                #print(time)
                theTimeSetInterval = datetime.datetime.strptime(time, '%H:%M')

                # print(theTimeSetInterval)

                # print(prevEndTime)

                if theTimeSetInterval >= prevEndTime:

                    print "++++ There is overlap. Setting new time-interval:", theTimeSetInterval

                    newStartTime = theTimeSetInterval

                    break

                #newStartTime = newTimeObj + datetime.timedelta(minutes=abs(timeDiff + overlapGap))

        elif (timeDiff >= 0) and (self.TIME_GAP != -1):

            '''
            *
            * If there this value is configured, then the timeGap var in config will determine the next increment. 
            * If it is set to "15", then the show will will bump up to the next 15 minute interval past the hour.
            *
            '''
            timeset=[datetime.time(h,m).strftime("%H:%M") for h,m in itertools.product(xrange(0,24),xrange(0,60,int(self.TIME_GAP)))]
            
            # print(timeset)

            for time in timeset:

                theTimeSetInterval = datetime.datetime.strptime(time, '%H:%M')

                tempTimeTwoStr = datetime.datetime.strptime(time1, self.APP_TIME_FORMAT_STR).strftime('%H:%M')

                formatted_time_two = datetime.datetime.strptime(tempTimeTwoStr, '%H:%M')

                if theTimeSetInterval >= formatted_time_two:

                    print "++++ Setting new time-interval:", theTimeSetInterval

                    newStartTime = theTimeSetInterval

                    break

        else:

            print("Not sure what to do here")

        return newStartTime.strftime('%I:%M:%S %p')

    def get_end_time_from_duration(self, startTime, duration):

        time = datetime.datetime.strptime(startTime, '%I:%M:%S %p')

        show_time_plus_duration = time + datetime.timedelta(milliseconds=duration)

        #print(show_time_plus_duration.minute)

        return show_time_plus_duration

    def generate_daily_schedule(self):

        print("#### Generating Daily Schedule")

        if self.USING_COMMERCIAL_INJECTION:
            self.commercials = PseudoChannelCommercial(
                self.db.get_commercials()
            )

        schedule = self.db.get_schedule()

        weekday_dict = {
            "0" : ["mondays", "weekdays", "everyday"],
            "1" : ["tuesdays", "weekdays", "everyday"],
            "2" : ["wednesdays", "weekdays", "everyday"],
            "3" : ["thursdays", "weekdays", "everyday"],
            "4" : ["fridays", "weekdays", "everyday"],
            "5" : ["saturdays", "weekends", "everyday"],
            "6" : ["sundays", "weekends", "everyday"],
        }

        weekno = datetime.datetime.today().weekday()

        schedule_advance_watcher = 0

        for entry in schedule:

            schedule_advance_watcher += 1

            section = entry[9]

            for key, val in weekday_dict.iteritems(): 

                if str(entry[7]) in str(val) and int(weekno) == int(key):

                    if section == "TV Shows":

                        if str(entry[3]).lower() == "random":

                            next_episode = self.db.get_random_episode()

                        else:

                            next_episode = self.db.get_next_episode(entry[3])

                        if next_episode != None:
                        
                            episode = Episode(
                                section, # section_type
                                next_episode[3], # title
                                entry[5], # natural_start_time
                                self.get_end_time_from_duration(self.translate_time(entry[5]), next_episode[4]), # natural_end_time
                                next_episode[4], # duration
                                entry[7], # day_of_week
                                entry[10], # is_strict_time
                                entry[11], # time_shift
                                entry[12], # overlap_max
                                next_episode[8] if len(next_episode) >= 9 else '', # plex id
                                entry[3], # show_series_title
                                next_episode[5], # episode_number
                                next_episode[6] # season_number
                                )

                            self.MEDIA.append(episode)

                        else:

                            print("Cannot find TV Show Episode, {} in the local db".format(entry[3]))

                        #print(episode)

                    elif section == "Movies":

                        if str(entry[3]).lower() == "random":

                            the_movie = self.db.get_random_movie()

                        else:

                            the_movie = self.db.get_movie(entry[3])

                        if the_movie != None:

                            movie = Movie(
                            section, # section_type
                            the_movie[3], # title
                            entry[5], # natural_start_time
                            self.get_end_time_from_duration(entry[5], the_movie[4]), # natural_end_time
                            the_movie[4], # duration
                            entry[7], # day_of_week
                            entry[10], # is_strict_time
                            entry[11], # time_shift
                            entry[12], # overlap_max
                            the_movie[6] # plex id
                            )

                            #print(movie.natural_end_time)

                            self.MEDIA.append(movie)

                        else:

                            print("Cannot find Movie, {} in the local db".format(entry[3]))

                    elif section == "Music":

                        the_music = self.db.get_music(entry[3])

                        if the_music != None:

                            music = Music(
                            section, # section_type
                            the_music[3], # title
                            entry[5], # natural_start_time
                            self.get_end_time_from_duration(entry[5], the_music[4]), # natural_end_time
                            the_music[4], # duration
                            entry[7], # day_of_week
                            entry[10], # is_strict_time
                            entry[11], # time_shift
                            entry[12], # overlap_max
                            the_music[6], # plex id
                            )

                            #print(music.natural_end_time)

                            self.MEDIA.append(music)

                        else:

                            print("Cannot find Music, {} in the local db".format(entry[3]))

                    elif section == "Video":

                        the_video = self.db.get_video(entry[3])

                        if the_music != None:

                            video = Video(
                            section, # section_type
                            the_video[3], # title
                            entry[5], # natural_start_time
                            self.get_end_time_from_duration(entry[5], the_video[4]), # natural_end_time
                            the_video[4], # duration
                            entry[7], # day_of_week
                            entry[10], # is_strict_time
                            entry[11], # time_shift
                            entry[12], # overlap_max
                            the_video[6] # plex id
                            )

                            #print(music.natural_end_time)

                            self.MEDIA.append(video)

                        else:

                            print("Cannot find Video, {} in the local db".format(entry[3]))

                    else:

                        pass

            """If we reached the end of the scheduled items for today, add them to the daily schedule

            """
            if schedule_advance_watcher >= len(schedule):

                print "+++++ Finished processing time entries, recreating daily_schedule"

                previous_episode = None

                self.db.remove_all_daily_scheduled_items()

                for entry in self.MEDIA:

                    #print entry.natural_end_time

                    if previous_episode != None:

                        natural_start_time = datetime.datetime.strptime(entry.natural_start_time, self.APP_TIME_FORMAT_STR)

                        natural_end_time = entry.natural_end_time

                        if entry.is_strict_time.lower() == "true":

                            print "++++ Strict-time: {}".format(str(entry.title))

                            entry.end_time = self.get_end_time_from_duration(
                                    self.translate_time(entry.start_time), 
                                    entry.duration
                                )

                            """Get List of Commercials to inject"""

                            if self.USING_COMMERCIAL_INJECTION:

                                list_of_commercials = self.commercials.get_commercials_to_place_between_media(
                                    previous_episode,
                                    entry
                                )

                                for commercial in list_of_commercials:

                                    self.db.add_media_to_daily_schedule(commercial)

                            self.db.add_media_to_daily_schedule(entry)

                            previous_episode = entry

                        else:

                            print "++++ NOT strict-time: {}".format(str(entry.title).encode(sys.stdout.encoding, errors='replace'))

                            new_starttime = self.calculate_start_time(
                                previous_episode.end_time,
                                entry.natural_start_time,  
                                previous_episode.time_shift, 
                                previous_episode.overlap_max
                            )

                            print "++++ New start time:", new_starttime

                            entry.start_time = datetime.datetime.strptime(new_starttime, self.APP_TIME_FORMAT_STR).strftime('%I:%M:%S %p')

                            entry.end_time = self.get_end_time_from_duration(entry.start_time, entry.duration)

                            """Get List of Commercials to inject"""
                            if self.USING_COMMERCIAL_INJECTION:
                                list_of_commercials = self.commercials.get_commercials_to_place_between_media(
                                    previous_episode,
                                    entry
                                )

                                for commercial in list_of_commercials:

                                    self.db.add_media_to_daily_schedule(commercial)

                            self.db.add_media_to_daily_schedule(entry)

                            previous_episode = entry

                    else:

                        self.db.add_media_to_daily_schedule(entry)

                        previous_episode = entry

    def run_commercial_injection(self):

        print "#### Running commercial injection."

        self.commercials = PseudoChannelCommercial(
            self.db.get_commercials(),
            self.db.get_daily_schedule()
        )

        commercials_to_inject = self.commercials.get_commercials_to_inject()

        print commercials_to_inject

    def run(self):

        """print datetime.datetime.now()
        threading.Timer(1, self.run()).start()"""
        pass

    def make_xml_schedule(self):

        self.controller.make_xml_schedule(self.db.get_daily_schedule())

    def get_daily_schedule_as_media_object_list(self):

        for i, item in enumerate(self.db.get_daily_schedule(), start=0):

            if item[11] == "TV Shows":

                """episode = Episode(

                )"""
                pass

            elif item[11] == "Movies":

                pass

            elif item[11] == "Music":

                pass

            elif item[11] == "Commercials":

                pass

            elif item[11] == "Videos":

                pass

            else:

                pass

    def show_clients(self):

        print "##### Connected Clients:"

        for i, client in enumerate(self.PLEX.clients()):
            
            print "+++++", str(i + 1)+".", "Client:", client.title

    def show_schedule(self):

        print "##### Daily Pseudo Schedule:"

        daily_schedule = self.db.get_daily_schedule()

        for i , entry in enumerate(daily_schedule):

            print "+++++", str(i + 1)+".", entry[8], entry[11], entry[6], " - ", entry[3]

    def exit_app(self):

        print " - Exiting Pseudo TV & cleaning up."

        for i in self.MEDIA:

            del i

        self.MEDIA = None

        self.controller = None

        self.db = None

        sleep(1)

if __name__ == '__main__':

    pseudo_channel = PseudoChannel()

    #pseudo_channel.db.create_tables()

    #pseudo_channel.update_db()

    #pseudo_channel.update_schedule()

    #pseudo_channel.generate_daily_schedule()

    banner = textwrap.dedent('''\
#   __              __                        
#  |__)_ _    _| _ /  |_  _  _  _  _|    _    
#  |  _)(-|_|(_|(_)\__| )(_|| )| )(-|.  |_)\/ 
#                                       |  /  

            A Custom TV Channel for Plex
''')

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description = banner)

    '''
    * 
    * Primary arguments: "python PseudoChannel.py -u -xml -g -r"
    *
    '''

    parser.add_argument('-u', '--update',
                         action='store_true',
                         help='Update the local database with Plex libraries.')
    parser.add_argument('-xml', '--xml',
                         action='store_true', 
                         help='Update the local database with the pseudo_schedule.xml.')
    '''
    * 
    * Update Schedule based on Google Cal: "python PseudoChannel.py -gc"
    *
    '''
    parser.add_argument('-gc', '--google_calendar',
                         action='store_true',
                         help='Update the local database with entries in the google calendar.')

    parser.add_argument('-g', '--generate_schedule',
                         action='store_true', 
                         help='Generate the daily schedule.')
    parser.add_argument('-r', '--run',
                         action='store_true', 
                         help='Run this program.')

    '''
    * 
    * Show connected clients: "python PseudoChannel.py -c"
    *
    '''
    parser.add_argument('-c', '--show_clients',
                         action='store_true',
                         help='Show Plex clients.')

    '''
    * 
    * Show schedule (daily): "python PseudoChannel.py -s"
    *
    '''
    parser.add_argument('-s', '--show_schedule',
                         action='store_true',
                         help='Show scheduled media for today.')

    '''
    * 
    * Make XML / HTML Schedule: "python PseudoChannel.py -m"
    *
    '''
    parser.add_argument('-m', '--make_html',
                         action='store_true',
                         help='Makes the XML / HTML schedule based on the daily_schedule table.')

    '''
    * 
    * Make XML / HTML Schedule: "python PseudoChannel.py -i"
    *
    '''
    parser.add_argument('-i', '--inject_commercials',
                         action='store_true',
                         help='Squeeze commercials in any media gaps if possible.')

    globals().update(vars(parser.parse_args()))

    args = parser.parse_args()

    #print(args)

    if args.update:

        pseudo_channel.update_db()

    if args.xml:

        pseudo_channel.update_schedule()

    if args.google_calendar:

        pseudo_channel.update_schedule_from_google_calendar()

    if args.generate_schedule:

        pseudo_channel.generate_daily_schedule()

    if args.show_clients:

        pseudo_channel.show_clients()

    if args.show_schedule:

        pseudo_channel.show_schedule()

    if args.make_html:

        pseudo_channel.make_xml_schedule()

    if args.inject_commercials:

        pseudo_channel.run_commercial_injection()

    if args.run:

        print banner
        print "+++++ To run this in the background:"
        print "+++++", "screen -d -m bash -c 'python PseudoChannel.py -r; exec sh'"
        
        """Every minute on the minute check the DB startTimes of all media to 
           determine whether or not to play. Also, check the now_time to
           see if it's midnight (or 23.59), if so then generate a new daily_schedule
            
        """

        the_daily_schedule = pseudo_channel.db.get_daily_schedule()

        daily_update_time = datetime.datetime.strptime(
            pseudo_channel.translate_time(
                pseudo_channel.DAILY_UPDATE_TIME
            ),
            pseudo_channel.APP_TIME_FORMAT_STR
        ) 

        try:
        
            def run_task():

                now = datetime.datetime.now()

                now_time = now.time().replace(microsecond=0)

                #print time(11,59,00), now_time

                if now_time == time(
                        daily_update_time.hour,
                        daily_update_time.minute,
                        daily_update_time.second
                ):

                    if pseudo_channel.USING_GOOGLE_CALENDAR:

                        pseudo_channel.update_schedule_from_google_calendar()

                    else:

                         pass
                        
                    pseudo_channel.generate_daily_schedule()

                    pseudo_channel.make_xml_schedule()

                pseudo_channel.controller.tv_controller(the_daily_schedule)

                t = Timer(1, run_task, ())

                t.start()

                #print '{}'.format(datetime.datetime.now(), end="\r")

        except KeyboardInterrupt:

                print('Manual break by user')

        run_task()

   

        """try:

            
            while True:

                now = datetime.datetime.now()

                now_time = now.time().replace(microsecond=0)

                #print time(11,59,00), now_time

                if now_time == time(00,00,00):

                    if pseudo_channel.USING_GOOGLE_CALENDAR:

                        pseudo_channel.update_schedule_from_google_calendar()

                        sleep(.5)

                    else:

                         pass
                        
                    pseudo_channel.generate_daily_schedule()

                    pseudo_channel.make_xml_schedule()

                pseudo_channel.controller.tv_controller(pseudo_channel.db.get_daily_schedule())

                t = datetime.datetime.utcnow()

                #sleeptime = 60 - (t.second + t.microsecond/1000000.0)

                sleep(.5)

        except KeyboardInterrupt, e:

            pseudo_channel.exit_app()

            del pseudo_channel"""
        





