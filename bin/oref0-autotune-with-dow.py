#!/usr/bin/env python3

import argparse
import requests
import datetime
import os, errno
import logging
from subprocess import call
import shutil

DIR = ''
NIGHTSCOUT_HOST = ''
START_DATE = datetime.datetime.today() - datetime.timedelta(days=1)
END_DATE = datetime.datetime.today()
NUMBER_OF_RUNS = 1
EXPORT_EXCEL = None
TERMINAL_LOGGING = True
RECOMMENDS_REPORT = True
DAYS_OF_WEEK = "0,1,2,3,4,5,6"

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
                        help='(--days-of-week=<comma separated list - Sunday = 0, Monday = 1, Tuesday = 2 .. Saturday = 6(0,1,2,3,4,5,6)>)')
    
    return parser.parse_args()

def assign_args_to_variables(args):
    # TODO: Input checking.
    
    global DIR, NIGHTSCOUT_HOST, START_DATE, END_DATE, NUMBER_OF_RUNS, \
           EXPORT_EXCEL, TERMINAL_LOGGING, RECOMMENDS_REPORT, DAYS_OF_WEEK
    
    # On Unix and Windows, return the argument with an initial component of
    # ~ or ~user replaced by that user's home directory.
    DIR = os.path.expanduser(args.dir)
    
    NIGHTSCOUT_HOST = args.ns_host

    START_DATE = args.start_date
    
    if args.end_date is not None:
        END_DATE = args.end_date
        
    if args.runs is not None:
        NUMBER_OF_RUNS = args.runs
        
    if args.xlsx is not None:
        EXPORT_EXCEL = args.xlsx
    
    if args.log is not None:
        RECOMMENDS_REPORT = args.logs
    
    if args.days_of_week is not None:
        DAYS_OF_WEEK = args.days_of_week

def create_date_lists(start_date, end_date, days_of_week, directory):
    date_list = [start_date + datetime.timedelta(days=x) for x in range(0, (end_date - start_date).days)]
    dow_list = days_of_week.split(',')
    for dow in dow_list:
        date_list_filename = 'date-list.' + dow + '.txt'
        date_list_file = os.path.join(directory, 'test', date_list_filename)
        with open(date_list_file, 'w') as d:
            for dateobj in date_list:
                if dateobj.isoweekday() == int(dow):
                    d.write(str(dateobj.date()) + "\n")

if __name__ == "__main__":
    args = get_input_arguments()
    assign_args_to_variables(args)
    create_date_lists(START_DATE, END_DATE, DAYS_OF_WEEK, DIR)
