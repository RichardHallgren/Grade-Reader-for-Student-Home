import pandas as pd
import numpy as np
import re
import datetime
import os
import sys

# print name of file to be decoded
print(sys.argv[1])

# Import Tika PDF parser
from tika import parser

# input-file
path = sys.argv[1]

# Read pdf-file
try:
    rawText = parser.from_file(path)

    rawList = rawText['content'].splitlines()
except:
    print('Ingen PDF-fil')

# Define approved grades
approved_grades = ['A', 'B', 'C', 'D', 'E', 'G', 'VG', 'MVG', 'AB', 'BA', '3', '4', '5', 'P']

# Set required hp
points_req = 15

# Set date interval
# 1 september -> 1 februari
start_date = '2019-09-1'
end_date = '2020-02-01'

def decode_ladok_extract(rawList):
    # Decode extracts from Ladok (containing all of the students records from all universites)
    completed_courses = []
    prev_line = 'None'
    prev2_line = 'None'

    for line in rawList:
        if line != '': # skip empty lines
            if bool(re.search(r'20',  line)): # check for lines containing 20, indicating a date
                splitted = line.split()
                try:
                    if splitted[-2] in approved_grades: # check if line contains a grade in the correct position
                        course_name = ' '.join(splitted[0:-4])
                        if len(course_name) < 1:
                            course_name = prev2_line + ' ' + prev_line
                        course_points = splitted[-3].strip('()')
                        course_complete_date = splitted[-1]
                        completed_courses.append([course_name, course_points, course_complete_date])
                    if splitted[-3] in approved_grades and ')' in splitted[-4]: # check if line contains a grade in the correct position
                        course_name = ' '.join(splitted[0:-5])
                        if len(course_name) < 1:
                            course_name = prev2_line + ' ' + prev_line
                        course_points = splitted[-4].strip('()')
                        course_complete_date = splitted[-2]
                        completed_courses.append([course_name, course_points, course_complete_date])
                except:
                    continue
            prev2_line = prev_line.strip()
            prev_line = line.strip()

    df = pd.DataFrame(completed_courses, columns=['Object', 'HP', 'Date'])
    df['HP'] = pd.to_numeric(df['HP'])
    df['Date'] = pd.to_datetime(df['Date'])

    approval = calculate_approval(df)

    return approval

def decode_uni_extract(rawList):
    # Decode extract from students university
    completed_courses = []
    avklarade = 0
    ej_avklarade = 0
    prev_line = 'None' # keep track of previous
    prev2_line = 'None' # keep track of the line before the previous line

    rawList_reduced = rawList[rawList.index('Resultatintyg'):]

    for line in rawList_reduced:
        if bool(re.search('Avklarade',  line)):
            avklarade = 1
            ej_avklarade = 0
        if bool(re.search('slutrapporterade', line)):
            avklarade = 0
            ej_avklarade = 1
        # check for completed hp in completed courses
        if line != '' and avklarade == 1 and ej_avklarade == 0:
            if bool(re.search(r'20',  line)):
                splitted = line.split()
                if splitted[-3] in approved_grades and '(' in splitted[-5]:
                    course_name = ' '.join(splitted[1:-5])
                    if len(course_name) < 1:
                        course_name = prev2_line + ' ' + prev_line
                    course_points = splitted[-5].strip('()').replace(',','.')
                    course_complete_date = splitted[-2].replace('\xad', '-')
                    completed_courses.append([course_name, course_points, course_complete_date])
            prev2_line = prev_line.strip()
            prev_line = line.strip()

        # check for completed hp in NON-completed courses
        if line != '' and avklarade == 0 and ej_avklarade ==1:
            if bool(re.search(r'20',  line)):
                splitted = line.split()
                if splitted[-3] in approved_grades:
                    course_name = ' '.join(splitted[1:-5])
                    if len(course_name) < 1:
                        course_name = prev2_line + ' ' + prev_line
                    course_points = splitted[-5].strip('()').replace(',','.')
                    course_complete_date = splitted[-2].replace('\xad', '-')
                    completed_courses.append([course_name, course_points, course_complete_date])
            prev2_line = prev_line.strip()
            prev_line = line.strip()

    # create dataframe of completed courses
    df = pd.DataFrame(completed_courses, columns=['Object', 'HP', 'Date'])
    df['HP'] = pd.to_numeric(df['HP'])
    df['Date'] = pd.to_datetime(df['Date'])

    approval = calculate_approval(df)

    return approval

def calculate_approval(df):
    df = df[(df['Date'] > start_date) & (df['Date'] < end_date)]

    if df.HP.sum() > points_req:
        approval = 'Yes'
    else:
        approval = 'No'

    print(df)
    print('Total HP during period:', df.HP.sum())

    print('Approved?', approval)

    return approval

# Check what type of student record to process
if 'Nationellt studieintyg' in rawList and 'Sveriges högskolor och universitet' in rawList:
    print('Ladok extract')
    decode_ladok_extract(rawList)
elif 'Registreringsintyg' in rawList:
    print('Endast nationella studieintyg eller resultatintyg godkänns, '
          'du har skickat in ett registreringsintyg.')
elif 'Resultatintyg' in rawList:
    print('Uni extract')
    decode_uni_extract(rawList)
else:
    print('Ogiltig fil')
