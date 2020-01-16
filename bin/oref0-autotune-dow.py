#!/usr/bin/env python3

from __future__ import print_function
# Python version of oref0-autotune.sh
# Original bash code: scottleibrand, pietergit, beached, danamlewis

# This script sets up an easy autotune environment for autotune, allowing the user to vary parameters 
# like start/end date and number of runs.
#
# Required Inputs: 
#   DIR, (--dir=<OpenAPS Directory>)
#   NIGHTSCOUT_HOST, (--ns-host=<NIGHTSCOUT SITE URL)
#   START_DATE, (--start-date=<YYYY-MM-DD>)
# Optional Inputs:
#   END_DATE, (--end-date=<YYYY-MM-DD>) 
#     if no end date supplied, assume we want a months worth or until day before current day
#   NUMBER_OF_RUNS (--runs=<integer, number of runs desired>)
#     if no number of runs designated, then default to 5
#   EXPORT_EXCEL (--xlsx=<filenameofexcel>)
#     export to excel. Disabled by default
#   TERMINAL_LOGGING (--log <true/false(true)>
#     logs terminal output to autotune.<date stamp>.log in the autotune baseDirectory, default to true
#   DOW, (--days-of-week=<dow>)
#     days of week for which to run the autotune (Monday = 1, Tuesday = 2 .. Sunday = 7)
#     list (e.g. "1,2,3,4,5")

import argparse
import requests
import datetime
import os, errno
import logging
from subprocess import call
import shutil
from pathlib import Path

DIR = ''
NIGHTSCOUT_HOST = ''
START_DATE = datetime.datetime.today() - datetime.timedelta(days=1)
END_DATE = datetime.datetime.today()
NUMBER_OF_RUNS = 1
EXPORT_EXCEL = None
TERMINAL_LOGGING = True
RECOMMENDS_REPORT = True
DOW = '1,2,3,4,5,6,7'
USER_TOKEN = ''

def get_input_arguments():
    parser = argparse.ArgumentParser(description='Autotune')
    
    # Required
    # NOTE: As the code runs right now, this baseDirectory needs to exist and as well as the subfolders: autotune, settings
    parser.add_argument('--dir',
                        '-d',
                        type=str,
                        required=True,
                        help='(--dir=<OpenAPS Directory>)')        
    parser.add_argument('--ns-host',
                        '-n',
                        type=str,
                        required=True,
                        metavar='NIGHTSCOUT_HOST',
                        help='(--ns-host=<NIGHTSCOUT SITE URL)')
    parser.add_argument('--start-date',
                        '-s',
                        type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
                        required=True,
                        help='(--start-date=<YYYY-MM-DD>)')
    parser.add_argument('--user-token',
                        '-u',
                        type=str,
                        metavar='USER_TOKEN',
                        help='(--user-token=<User Authentication Token>)')
    # Optional
    parser.add_argument('--end-date',
                        '-e',
                        type=lambda d: datetime.datetime.strptime(d, '%Y-%m-%d'),
                        help='(--end-date=<YYYY-MM-DD>)')
    parser.add_argument('--runs',
                        '-r',
                        type=int,
                        metavar='NUMBER_OF_RUNS',
                        help='(--runs=<integer, number of runs desired>)')
    parser.add_argument('--xlsx',
                        '-x',
                        type=str,
                        metavar='EXPORT_EXCEL',
                        help='(--xlsx=<filenameofexcel>)')                
    parser.add_argument('--log',
                        '-l',
                        type=str,
                        metavar='TERMINAL_LOGGING',
                        help='(--log <true/false(true)>)')
    parser.add_argument('--days-of-week',
                        '-w',
                        type=str,
                        metavar='DAYS_OF_WEEK',
                        help='(--days-of-week=<comma separated quoted list - Monday = 1, Tuesday = 2 .. Saturday = 6, Sunday = 7("1,2,3,4,5,6,7")>)')
    
    return parser.parse_args()

def assign_args_to_variables(args):
    # TODO: Input checking.

    global DIR, NIGHTSCOUT_HOST, START_DATE, END_DATE, USER_TOKEN, NUMBER_OF_RUNS,\
        EXPORT_EXCEL, TERMINAL_LOGGING, RECOMMENDS_REPORT, daysOfWeek

    # On Unix and Windows, return the argument with an initial component of
    # ~ or ~user replaced by that user's home baseDirectory.
    DIR = os.path.expanduser(args.dir)

    NIGHTSCOUT_HOST = args.ns_host

    START_DATE = args.start_date

    if args.end_date is not None:
        END_DATE = args.end_date
    
    if args.user_token is not None:
        USER_TOKEN = args.user_token
    
    if args.runs is not None:
        NUMBER_OF_RUNS = args.runs
    
    if args.xlsx is not None:
        EXPORT_EXCEL = args.xlsx
    
    if args.log is not None:
        RECOMMENDS_REPORT = args.logs
    
    if args.days_of_week is not None:
        DOW = args.days_of_week

#def get_nightscout_profile(nightscoutHost, baseDirectory):
#    autotuneDirectory = os.path.join(baseDirectory, 'autotune')
#    #TODO: Add ability to use API secret for Nightscout.
#    res = requests.get(nightscoutHost + '/api/v1/profile.json')
#    with open(os.path.join(autotuneDirectory, 'nightscout.profile.json'), 'w') as f:  # noqa: F821
#        f.write(res.text)

def create_date_lists(start_date, end_date, daysOfWeek, baseDirectory):
    dateRange = [start_date + datetime.timedelta(days=x) for x in range(0, (end_date - start_date).days)]
    dateDictionary = {}
    dayOfWeekList = daysOfWeek.split(',')
    dateListFilename = os.path.join(baseDirectory, 'autotune', 'date-list.txt')
    for dayOfWeek in dayOfWeekList:
        dateListForDayOfWeek = []
        for dateObj in dateRange:
            if dateObj.isoweekday() == int(dayOfWeek):
                dateListForDayOfWeek.append(dateObj.date())
        dateDictionary[dayOfWeek] = dateListForDayOfWeek
    with open(dateListFilename, 'w') as d:
        for dayOfWeek, dateListForDayOfWeek in dateDictionary.items():
            dateListFilename = 'date-list.' + dayOfWeek + '.txt'
            dateListFilePath = os.path.join(baseDirectory, 'autotune', dateListFilename)
            with open(dateListFilePath, 'w') as dd:
                for date in dateListForDayOfWeek:
                    dd.write(str(date) + '\n')
                    d.write(str(dayOfWeek) + ": " + str(date) + "\n")
    return dateDictionary
    print(dateDictionary)

def get_openaps_profile(baseDirectory):
    shutil.copy(os.path.join(baseDirectory, 'settings', 'pumpprofile.json'), os.path.join(baseDirectory, 'autotune', 'profile.pump.json'))
    
    # If a previous valid settings/autotune.json exists, use that; otherwise start from settings/profile.json
    
    # This allows manual users to be able to run autotune by simply creating a settings/pumpprofile.json file.
    # cp -up settings/pumpprofile.json settings/profile.json
    shutil.copy(os.path.join(baseDirectory, 'settings', 'pumpprofile.json'), os.path.join(baseDirectory, 'settings', 'profile.json'))
    
    # TODO: Get this to work. For now, just copy from settings/profile.json each time.
    # If a previous valid settings/autotune.json exists, use that; otherwise start from settings/profile.json
    # cp settings/autotune.json autotune/profile.json && cat autotune/profile.json | json | grep -q start || cp autotune/profile.pump.json autotune/profile.json
    # create_autotune_json = "cp {0}settings/autotune.json {0}autotune/profile.json && cat {0}autotune/profile.json | json | grep -q start || cp {0}autotune/profile.pump.json {0}autotune/profile.json".format(baseDirectory)
    # print create_autotune_json
    # call(create_autotune_json, shell=True)

    # cp settings/autotune.json autotune/profile.json
    shutil.copy(os.path.join(baseDirectory, 'settings', 'profile.json'), os.path.join(baseDirectory, 'settings', 'autotune.json'))

def get_openaps_daily_profile(baseDirectory, dayOfWeek):
    # cp settings/autotune.json autotune/profile.json
    profileDayOfWeek = 'profile-day' + dayOfWeek + '.json'
    profileDayOfWeekPath = os.path.join(baseDirectory, 'autotune', profileDayOfWeek)
    profileObj = Path(profileDayOfWeekPath)
    if profileObj.is_file():
        shutil.copy(os.path.join(baseDirectory, 'autotune', profileDayOfWeek), os.path.join(baseDirectory, 'autotune', 'profile.json'))
    else:
        shutil.copy(os.path.join(baseDirectory, 'settings', 'profile.json'), os.path.join(baseDirectory, 'autotune', 'profile.json'))

def get_nightscout_carb_and_insulin_treatments(nightscoutHost, baseDirectory, dayOfWeek, runDate, userToken):
    dateListFilename_name = "date-list." + dayOfWeek + ".txt"
    dateListFilename_path = os.path.join(baseDirectory, 'autotune', dateListFilename_name)
    # TODO: What does 'T20:00-05:00' mean?
    outputFilename = "ns-treatments." + datetime.datetime.strftime(runDate, "%Y-%m-%d") + ".json"
    outputFilePath = os.path.join(baseDirectory, 'autotune', outputFilename)
    tomorrowDate = runDate + datetime.timedelta(days=1)
    #tomorrow = datetime.datetime.strftime(tomorrowDate, "%Y-%m-%d")
    yesterdayDate= runDate - datetime.timedelta(days=1)
    #yesterday = datetime.datetime.strftime(yesterdayDate, "%Y-%m-%d")
    logging.info('Grabbing NIGHTSCOUT treatments.json for date: {0}'.format(runDate))
    url='{0}/api/v1/treatments.json?find[created_at][$gt]={1}&find[created_at][$lt]={2}'
    url = url.format(nightscoutHost, yesterdayDate, tomorrowDate)
    if userToken != "":
        userToken = "&token=" + userToken    #TODO: Add ability to use API secret for Nightscout.
        url=url + userToken
    print("Treatments URL: " + url)
    res = requests.get(url)
    response = str(res.content, 'utf-8')
    with open(outputFilePath, 'w') as f:
        f.write(response)

def get_nightscout_bg_entries(nightscoutHost, baseDirectory, dayOfWeek, runDate, userToken):
    #dateList = [start_date + datetime.timedelta(days=x) for x in range(0, (end_date - start_date).days)]
    dateListFilename_name = "date-list." + dayOfWeek + ".txt"
    dateListFilename_path = os.path.join(baseDirectory, 'autotune', dateListFilename_name)
    tomorrowDate = runDate + datetime.timedelta(days=1)
    tomorrow = datetime.datetime.strftime(tomorrowDate, "%Y-%m-%d")
    yesterdayDate= runDate - datetime.timedelta(days=1)
    yesterday = datetime.datetime.strftime(yesterdayDate, "%Y-%m-%d")
    logging.info('Grabbing NIGHTSCOUT enries/sgv.json for date: {0}'.format(runDate))
    url="{0}/api/v1/entries/sgv.json?find[dateString][$gt]={1}&find[dateString][$lt]={2}&count=1500"
    url = url.format(nightscoutHost, yesterday, tomorrow)
    if userToken != "":
        userToken = "&token=" + userToken
        url = url + userToken
    print("SGV URL: " + url)
    res = requests.get(url)
    response = str(res.content, 'utf-8')
    with open(os.path.join(baseDirectory, "autotune", "ns-entries.{0}.json".format(runDate)), 'w') as f:
        f.write(response)

def run_autotune(dow, numberOfRuns, baseDirectory):
    autotuneDirectory = os.path.join(baseDirectory, 'autotune')
    shutil.copy(os.path.join(autotuneDirectory, 'profile.pump.{dow}.json').format(dow=dayOfWeek),
                os.path.join(autotuneDirectory, 'profile.pump.json'))
    for runNumber in range(1, numberOfRuns + 1):
        dateFile = 'date-list.' + dayOfWeek + '.txt'
        dateFilePath = os.path.join(baseDirectory, 'autotune', dateFile)
        with open(dateFilePath, 'r') as d:
            dateList = d.readlines()
        for date in dateList:
            # cp profile.json profile.$run_number.$i.json
            date = date.rstrip('\n')
            shutil.copy(os.path.join(autotuneDirectory, 'profile-day{dow}.json').format(dow=dayOfWeek),
                        os.path.join(autotuneDirectory, 'profile.{run_number}.{date}.json'
                        .format(run_number=runNumber, date=date)))

            # Autotune Prep (required args, <pumphistory.json> <profile.json> <glucose.json>), output prepped glucose 
            # data or <autotune/glucose.json> below
            # oref0-autotune-prep ns-treatments.json profile.json ns-entries.$DATE.json > autotune.$RUN_NUMBER.$DATE.json
            nsTreatments = os.path.join(autotuneDirectory, 'ns-treatments.{date}.json'.format(date=date))
            profile = os.path.join(autotuneDirectory, 'profile.{run_number}.{date}.json'.format(run_number=runNumber, date=date))
            nsEntries = os.path.join(autotuneDirectory, 'ns-entries.{date}.json'.format(date=date))
            pumpProfile = os.path.join(autotuneDirectory, 'profile.pump.json')
            autotunePrep = 'oref0-autotune-prep {ns_treatments} {profile} {ns_entries} {pump_profile}'.format(ns_treatments=nsTreatments, profile=profile, ns_entries=nsEntries, pump_profile=pumpProfile)

            # autotune.$RUN_NUMBER.$DATE.json  
            autotuneRunFilename = os.path.join(autotuneDirectory, 'autotune.{run_number}.{date}.json'
                                                .format(run_number=runNumber, date=date))
            with open(autotuneRunFilename, "w+") as output:
                logging.info('Running {script}'.format(script=autotunePrep))
                call(autotunePrep, stdout=output, shell=True)
                logging.info('Writing output to {filename}'.format(filename=autotuneRunFilename))
        
            # Autotune  (required args, <autotune/glucose.json> <autotune/autotune.json> <settings/profile.json>), 
            # output autotuned profile or what will be used as <autotune/autotune.json> in the next iteration
            # oref0-autotune-core autotune.$RUN_NUMBER.$DATE.json profile.json profile.pump.json > newprofile.$RUN_NUMBER.$DATE.json
        
            # oref0-autotune-core autotune.$run_number.$i.json profile.json profile.pump.json > newprofile.$RUN_NUMBER.$DATE.json
            profilePump = os.path.join(autotuneDirectory, 'profile.pump.json')
            autotuneCore = 'oref0-autotune-core {autotune_run} {profile} {profile_pump}'.format(profile=profile, profile_pump=profilePump, autotune_run=autotuneRunFilename)
            
            # newprofile.$RUN_NUMBER.$DATE.json
            newprofileRunFilename = os.path.join(autotuneDirectory, 'newprofile.{run_number}.{date}.json'
                                                .format(run_number=runNumber, date=date))
            with open(newprofileRunFilename, "w+") as output:
                logging.info('Running {script}'.format(script=autotuneCore))
                call(autotuneCore, stdout=output, shell=True)
                logging.info('Writing output to {filename}'.format(filename=newprofileRunFilename))
        
            # Copy tuned profile produced by autotune to profile.json for use with next day of data
            # cp newprofile.$RUN_NUMBER.$DATE.json profile.json
            shutil.copy(os.path.join(autotuneDirectory, 'newprofile.{run_number}.{date}.json'.format(run_number=runNumber, date=date)),
                        os.path.join(autotuneDirectory, 'profile-day{dow}.json'.format(dow=dayOfWeek)))
    shutil.copy(os.path.join(autotuneDirectory, 'profile.pump.json'),
                os.path.join(autotuneDirectory, 'profile.pump.{dow}.json'.format(dow=dayOfWeek)))

def export_to_excel(outputDirectory, outputExcelFilename):
    autotune_export_to_xlsx = 'oref0-autotune-export-to-xlsx --dir {0} --output {1}'.format(outputDirectory, outputExcelFilename)
    call(autotune_export_to_xlsx, shell=True)

def create_summary_report_and_display_results(outputDirectory):
    print()
    print("Autotune pump profile recommendations:")
    print("---------------------------------------------------------")
    
    reportFile = os.path.join(outputDirectory, 'autotune', 'autotune_recommendations.log')
    autotuneRecommendsReport = 'oref0-autotune-recommends-report {0}'.format(outputDirectory)
    
    call(autotuneRecommendsReport, shell=True)
    print("Recommendations Log File: {0}".format(reportFile))
    
    # Go ahead and echo autotune_recommendations.log to the terminal, minus blank lines
    # cat $report_file | egrep -v "\| *\| *$"
    call(['cat {0} | egrep -v "\| *\| *$"'.format(reportFile)], shell=True)

if __name__ == "__main__":
    # Set log level for this app to DEBUG.
    logging.basicConfig(level=logging.DEBUG)
    # Supress non-essential logs (below WARNING) from requests module.
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    args = get_input_arguments()
    assign_args_to_variables(args)
    
    # TODO: Convert Nightscout profile to OpenAPS profile format.
    #get_nightscout_profile(NIGHTSCOUT_HOST, DIR)
    passedDateDictionary = create_date_lists(START_DATE, END_DATE, DOW, DIR)
    daysOfWeek = DOW
    dayOfWeekList = daysOfWeek.split(',')
    for dayOfWeek in passedDateDictionary.keys():
        get_openaps_daily_profile(DIR, dayOfWeek)
        dateList = passedDateDictionary[dayOfWeek]
        for runDate in dateList:
            get_nightscout_carb_and_insulin_treatments(NIGHTSCOUT_HOST, DIR, dayOfWeek, runDate, USER_TOKEN)
            get_nightscout_bg_entries(NIGHTSCOUT_HOST, DIR, dayOfWeek, runDate, USER_TOKEN)
        run_autotune(dayOfWeek, NUMBER_OF_RUNS, DIR)
    
    if EXPORT_EXCEL:
        export_to_excel(DIR, EXPORT_EXCEL)
    
    if RECOMMENDS_REPORT:
        create_summary_report_and_display_results(DIR)
