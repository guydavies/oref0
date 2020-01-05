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
#     logs terminal output to autotune.<date stamp>.log in the autotune directory, default to true
#   DAYS_OF_WEEK, (--days-of-week=<dow>)
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
DAYS_OF_WEEK = '1,2,3,4,5,6,7'
USER_TOKEN = ''

def get_input_arguments():
    parser = argparse.ArgumentParser(description='Autotune')
    
    # Required
    # NOTE: As the code runs right now, this directory needs to exist and as well as the subfolders: autotune, settings
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
        EXPORT_EXCEL, TERMINAL_LOGGING, RECOMMENDS_REPORT, DAYS_OF_WEEK

    # On Unix and Windows, return the argument with an initial component of
    # ~ or ~user replaced by that user's home directory.
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
        DAYS_OF_WEEK = args.days_of_week

#def get_nightscout_profile(nightscout_host, directory):
#    autotune_directory = os.path.join(directory, 'autotune')
#    #TODO: Add ability to use API secret for Nightscout.
#    res = requests.get(nightscout_host + '/api/v1/profile.json')
#    with open(os.path.join(autotune_directory, 'nightscout.profile.json'), 'w') as f:  # noqa: F821
#        f.write(res.text)

def create_date_lists(start_date, end_date, days_of_week, directory):
    date_range_list = [start_date + datetime.timedelta(days=x) for x in range(0, (end_date - start_date).days)]
    date_dictionary = {}
    dow_list = days_of_week.split(',')
    date_list_file = os.path.join(directory, 'autotune', 'date-list.txt')
    for dow in dow_list:
        day_date_list = []
        for dateobj in date_range_list:
            if dateobj.isoweekday() == int(dow):
                day_date_list.append(dateobj.date())
        date_dictionary[dow] = day_date_list
    with open(date_list_file, 'w') as d:
        for day, dates in date_dictionary.items():
            daily_date_list_file = 'date-list.' + day + '.txt'
            daily_date_list_path = os.path.join(directory, 'autotune', daily_date_list_file)
            with open(daily_date_list_path, 'w') as dd:
                for date in dates:
                    dd.write(str(date) + '\n')
                    d.write(str(day) + ": " + str(date) + "\n")
    return date_dictionary
    print(date_dictionary)

def get_openaps_profile(directory):
    shutil.copy(os.path.join(directory, 'settings', 'pumpprofile.json'), os.path.join(directory, 'autotune', 'profile.pump.json'))
    
    # If a previous valid settings/autotune.json exists, use that; otherwise start from settings/profile.json
    
    # This allows manual users to be able to run autotune by simply creating a settings/pumpprofile.json file.
    # cp -up settings/pumpprofile.json settings/profile.json
    shutil.copy(os.path.join(directory, 'settings', 'pumpprofile.json'), os.path.join(directory, 'settings', 'profile.json'))
    
    # TODO: Get this to work. For now, just copy from settings/profile.json each time.
    # If a previous valid settings/autotune.json exists, use that; otherwise start from settings/profile.json
    # cp settings/autotune.json autotune/profile.json && cat autotune/profile.json | json | grep -q start || cp autotune/profile.pump.json autotune/profile.json
    # create_autotune_json = "cp {0}settings/autotune.json {0}autotune/profile.json && cat {0}autotune/profile.json | json | grep -q start || cp {0}autotune/profile.pump.json {0}autotune/profile.json".format(directory)
    # print create_autotune_json
    # call(create_autotune_json, shell=True)

    # cp settings/autotune.json autotune/profile.json
    shutil.copy(os.path.join(directory, 'settings', 'profile.json'), os.path.join(directory, 'settings', 'autotune.json'))

def get_openaps_daily_profile(directory, dow):
    # cp settings/autotune.json autotune/profile.json
    profile_day = 'profile-day' + dow + '.json'
    profile_name = os.path.join(directory, 'autotune', profile_day)
    profile_obj = Path(profile_name)
    if profile_obj.is_file():
        shutil.copy(os.path.join(directory, 'autotune', profile_day), os.path.join(directory, 'autotune', 'profile.json'))
    else:
        shutil.copy(os.path.join(directory, 'settings', 'profile.json'), os.path.join(directory, 'autotune', 'profile.json'))

def get_nightscout_carb_and_insulin_treatments(nightscout_host, directory, dow, run_date, user_token):
    date_list_file_name = "date-list." + dow + ".txt"
    date_list_file_path = os.path.join(directory, 'autotune', date_list_file_name)
    # TODO: What does 'T20:00-05:00' mean?
    output_file_name = "ns-treatments." + datetime.datetime.strftime(run_date, "%Y-%m-%d") + ".json"
    output_file_path = os.path.join(directory, 'autotune', output_file_name)
    tomorrow_date = run_date + datetime.timedelta(days=1)
    tomorrow = datetime.datetime.strftime(tomorrow_date, "%Y-%m-%d")
    yesterday_date = run_date - datetime.timedelta(days=1)
    yesterday = datetime.datetime.strftime(yesterday_date, "%Y-%m-%d")
    logging.info('Grabbing NIGHTSCOUT treatments.json for date: {0}'.format(run_date))
    url='{0}/api/v1/treatments.json?find[created_at][$gt]={1}&find[created_at][$lt]={2}'
    url = url.format(nightscout_host, yesterday_date, tomorrow_date)
    if user_token != "":
        user_token = "&token=" + user_token    #TODO: Add ability to use API secret for Nightscout.
        url=url + user_token
    print("Treatments URL: " + url)
    res = requests.get(url)
    response = str(res.content, 'utf-8')
    with open(output_file_path, 'w') as f:
        f.write(response)

def get_nightscout_bg_entries(nightscout_host, directory, dow, run_date, user_token):
    #date_list = [start_date + datetime.timedelta(days=x) for x in range(0, (end_date - start_date).days)]
    date_list_file_name = "date-list." + dow + ".txt"
    date_list_file_path = os.path.join(directory, 'autotune', date_list_file_name)
    tomorrow_date = run_date + datetime.timedelta(days=1)
    tomorrow = datetime.datetime.strftime(tomorrow_date, "%Y-%m-%d")
    yesterday_date = run_date - datetime.timedelta(days=1)
    yesterday = datetime.datetime.strftime(yesterday_date, "%Y-%m-%d")
    logging.info('Grabbing NIGHTSCOUT enries/sgv.json for date: {0}'.format(run_date))
    url="{0}/api/v1/entries/sgv.json?find[dateString][$gt]={1}&find[dateString][$lt]={2}&count=1500"
    url = url.format(nightscout_host, yesterday, tomorrow)
    if user_token != "":
        user_token = "&token=" + user_token
        url = url + user_token
    print("SGV URL: " + url)
    res = requests.get(url)
    response = str(res.content, 'utf-8')
    with open(os.path.join(directory, "autotune", "ns-entries.{0}.json".format(run_date)), 'w') as f:
        f.write(response)

def run_autotune(dow, number_of_runs, directory):
    autotune_directory = os.path.join(directory, 'autotune')
    shutil.copy(os.path.join(autotune_directory, 'profile.pump.{dow}.json').format(dow=dow),
                os.path.join(autotune_directory, 'profile.pump.json'))
    for run_number in range(1, number_of_runs + 1):
        daily_date_file = 'date-list.' + dow + '.txt'
        daily_date_path = os.path.join(directory, 'autotune', daily_date_file)
        with open(daily_date_path, 'r') as d:
            date_list = d.readlines()
        for date in date_list:
            # cp profile.json profile.$run_number.$i.json
            date = date.rstrip('\n')
            shutil.copy(os.path.join(autotune_directory, 'profile-day{dow}.json').format(dow=dow),
                        os.path.join(autotune_directory, 'profile.{run_number}.{date}.json'
                        .format(run_number=run_number, date=date)))

            # Autotune Prep (required args, <pumphistory.json> <profile.json> <glucose.json>), output prepped glucose 
            # data or <autotune/glucose.json> below
            # oref0-autotune-prep ns-treatments.json profile.json ns-entries.$DATE.json > autotune.$RUN_NUMBER.$DATE.json
            ns_treatments = os.path.join(autotune_directory, 'ns-treatments.{date}.json'.format(date=date))
            profile = os.path.join(autotune_directory, 'profile.{run_number}.{date}.json'.format(run_number=run_number, date=date))
            ns_entries = os.path.join(autotune_directory, 'ns-entries.{date}.json'.format(date=date))
            pump_profile = os.path.join(autotune_directory, 'profile.pump.json')
            autotune_prep = 'oref0-autotune-prep {ns_treatments} {profile} {ns_entries} {pump_profile}'.format(ns_treatments=ns_treatments, profile=profile, ns_entries=ns_entries, pump_profile=pump_profile)

            # autotune.$RUN_NUMBER.$DATE.json  
            autotune_run_filename = os.path.join(autotune_directory, 'autotune.{run_number}.{date}.json'
                                                .format(run_number=run_number, date=date))
            with open(autotune_run_filename, "w+") as output:
                logging.info('Running {script}'.format(script=autotune_prep))
                call(autotune_prep, stdout=output, shell=True)
                logging.info('Writing output to {filename}'.format(filename=autotune_run_filename))
        
            # Autotune  (required args, <autotune/glucose.json> <autotune/autotune.json> <settings/profile.json>), 
            # output autotuned profile or what will be used as <autotune/autotune.json> in the next iteration
            # oref0-autotune-core autotune.$RUN_NUMBER.$DATE.json profile.json profile.pump.json > newprofile.$RUN_NUMBER.$DATE.json
        
            # oref0-autotune-core autotune.$run_number.$i.json profile.json profile.pump.json > newprofile.$RUN_NUMBER.$DATE.json
            profile_pump = os.path.join(autotune_directory, 'profile.pump.json')
            autotune_core = 'oref0-autotune-core {autotune_run} {profile} {profile_pump}'.format(profile=profile, profile_pump=profile_pump, autotune_run=autotune_run_filename)
            
            # newprofile.$RUN_NUMBER.$DATE.json
            newprofile_run_filename = os.path.join(autotune_directory, 'newprofile.{run_number}.{date}.json'
                                                    .format(run_number=run_number, date=date))
            with open(newprofile_run_filename, "w+") as output:
                logging.info('Running {script}'.format(script=autotune_core))
                call(autotune_core, stdout=output, shell=True)
                logging.info('Writing output to {filename}'.format(filename=autotune_run_filename))
        
            # Copy tuned profile produced by autotune to profile.json for use with next day of data
            # cp newprofile.$RUN_NUMBER.$DATE.json profile.json
            shutil.copy(os.path.join(autotune_directory, 'newprofile.{run_number}.{date}.json'.format(run_number=run_number, date=date)),
                        os.path.join(autotune_directory, 'profile-day{dow}.json'.format(dow=dow)))
    shutil.copy(os.path.join(autotune_directory, 'profile.pump.json'),
                os.path.join(autotune_directory, 'profile.pump.{dow}.json'.format(dow=dow)))

def export_to_excel(output_directory, output_excel_filename):
    autotune_export_to_xlsx = 'oref0-autotune-export-to-xlsx --dir {0} --output {1}'.format(output_directory, output_excel_filename)
    call(autotune_export_to_xlsx, shell=True)

def create_summary_report_and_display_results(output_directory):
    print()
    print("Autotune pump profile recommendations:")
    print("---------------------------------------------------------")
    
    report_file = os.path.join(output_directory, 'autotune', 'autotune_recommendations.log')
    autotune_recommends_report = 'oref0-autotune-recommends-report {0}'.format(output_directory)
    
    call(autotune_recommends_report, shell=True)
    print("Recommendations Log File: {0}".format(report_file))
    
    # Go ahead and echo autotune_recommendations.log to the terminal, minus blank lines
    # cat $report_file | egrep -v "\| *\| *$"
    call(['cat {0} | egrep -v "\| *\| *$"'.format(report_file)], shell=True)

if __name__ == "__main__":
    # Set log level for this app to DEBUG.
    logging.basicConfig(level=logging.DEBUG)
    # Supress non-essential logs (below WARNING) from requests module.
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    args = get_input_arguments()
    assign_args_to_variables(args)
    
    # TODO: Convert Nightscout profile to OpenAPS profile format.
    #get_nightscout_profile(NIGHTSCOUT_HOST, DIR)
    passed_date_dictionary = create_date_lists(START_DATE, END_DATE, DAYS_OF_WEEK, DIR)
    days_of_week = DAYS_OF_WEEK
    dow_list = days_of_week.split(',')
    for dow in passed_date_dictionary.keys():
        get_openaps_daily_profile(DIR, dow)
        date_list = passed_date_dictionary[dow]
        for run_date in date_list:
            get_nightscout_carb_and_insulin_treatments(NIGHTSCOUT_HOST, DIR, dow, run_date, USER_TOKEN)
            get_nightscout_bg_entries(NIGHTSCOUT_HOST, DIR, dow, run_date, USER_TOKEN)
#                get_openaps_profile(DIR)
        for run_date in date_list:
            run_autotune(dow, NUMBER_OF_RUNS, DIR)
    
    if EXPORT_EXCEL:
        export_to_excel(DIR, EXPORT_EXCEL)
    
    if RECOMMENDS_REPORT:
        create_summary_report_and_display_results(DIR)
