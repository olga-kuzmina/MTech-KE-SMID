# -*- coding: utf-8 -*-
"""
@author: yuelin
Written for Python version: 3.5.2

require phantomJS in folder:- 
 - can be downloaded from: http://phantomjs.org/download.html
 - and put in path as  below
"""

import json
from lxml import objectify
from selenium import webdriver
from bs4 import BeautifulSoup

import urllib
from urllib.request import urlopen
from urllib.error import HTTPError
from datetime import datetime
from datetime import timedelta
import time
import pandas
import numpy
import re

# Authentication parameters for LTA
headers = { 'AccountKey' : 'LBdfS4+RSEi4witEa6RjjQ==',
            'UniqueUserID' : '812eb03f-f3a1-421c-96de-069c59844bbb',
            'accept' : 'application/json'}
uri = 'http://datamall2.mytransport.sg/'
path_TSB = 'ltaodataservice/TrafficSpeedBands'
path_TI = 'ltaodataservice/TrafficIncidents'
path_FTL = 'ltaodataservice/FaultyTrafficLights'
path_ETT = 'ltaodataservice/EstTravelTimes'
path_RO = 'ltaodataservice/RoadOpenings'
path_RW = 'ltaodataservice/RoadWorks'

#NEA 
key = '781CF461BB6606ADC767F3B357E848ED4A6709A0B39C63D6'
urlNowcast = 'http://api.nea.gov.sg/api/WebAPI/?dataset=2hr_nowcast&keyref=' + key
urlWarning = 'http://api.nea.gov.sg/api/WebAPI/?dataset=heavy_rain_warning&keyref=' + key

# Meteorological Service Singapore Rainfall observations
urlRainfall = 'http://www.weather.gov.sg/weather-currentobservations-rainfall'
driver = webdriver.PhantomJS(executable_path='../bin/phantomjs')

# function to return time difference in seconds
def getTimeDifference(TimeStart, TimeEnd):
    timeDiff = TimeEnd - TimeStart
    return timeDiff.total_seconds() / 60

# function to return differences between two data frames with same indices
def getDataframeDifferenceIndexed(df1, df2):
    neRows = (df1 != df2).any(1)
    ne_stacked = (df1 != df2).stack()
    changed = ne_stacked[ne_stacked]
    changed.index.names = ['id', 'col']
    diff_loc = numpy.where(df1 != df2)
    changed_from = df1.values[diff_loc]
    changed_to = df2.values[diff_loc]
    diff = pandas.DataFrame({'from': changed_from, 'to': changed_to}, index=changed.index)
    return diff

#initialise timewrites to 30 minutes ago
timewrite_30min = datetime.now() - timedelta(minutes=31)
timewrite_5min = timewrite_2min = timewrite_10min = timewrite_30min

initFlag = False

print(datetime.now())
while ((datetime.now().month == 11) and (datetime.now().day < 13)):
    timeNow = datetime.now()

    ## Get Input Events
    if getTimeDifference(timewrite_5min, timeNow) > 5 :
        # Traffic Speed Band data - updates every 5 minutes
        request = urllib.request.Request(uri + path_TSB, headers=headers)
        try:
            response = urlopen(request).read().decode('utf-8')
        except Exception:
            pass
        else:
            jsonObj = json.loads(response)
            messages = jsonObj.get("value")
            dfTSB = pandas.DataFrame(messages)
            dfTSB = dfTSB.set_index('LinkID')
            dfTSB.index.name = None
            #print(dfTSB.head(2))

        # ESTIMATED TRAVEL TIMES data - updates every 5 minutes
        request = urllib.request.Request(uri + path_ETT, headers=headers)
        try:
            response = urlopen(request).read().decode('utf-8')
        except Exception:
            pass
        else:
            jsonObj = json.loads(response)
            messages = jsonObj.get("value")
            dfETT = pandas.DataFrame(messages)
            #print(dfETT.head(2))
            
        # set time for diff 5 mins
        timewrite_5min = datetime.now()

    if getTimeDifference(timewrite_2min, timeNow) > 2 :
        # collect Traffic Incidents data - updates every 2 minutes
        request = urllib.request.Request(uri + path_TI, headers=headers)
        try:
            response = urlopen(request).read().decode('utf-8')
        except Exception:
            pass
        else:
            jsonObj = json.loads(response)
            messages = jsonObj.get("value")
            dfTI = pandas.DataFrame(messages)
            #print(dfTI.head(2))
        # set time for diff 2 mins
        timewrite_2min = datetime.now()

    if getTimeDifference(timewrite_30min, timeNow) > 30 :
        # collect Nowcast data - updates every 30 mins
        request = urllib.request.Request(urlNowcast)
        try:
            parsed = objectify.parse(urlopen(request))
        except Exception:
            pass
        else:
            parsed = objectify.parse(urlopen(request))
            root = parsed.getroot()
            dfNowcast = pandas.DataFrame(columns=['Forecast', 'Latitude', 'Longitude', 'Name'])
            for area in root.iter('area'):
                dfNowcast = dfNowcast.append({'Forecast':area.get('forecast'),'Latitude':area.get('lat'),'Longtitude':area.get('lon'),'Name':area.get('name')}, ignore_index=True)
            dfNowcast = dfNowcast.set_index('Name')
            dfNowcast.index.name = None
            #print(dfNowcast.head(2))

        # collect Heavy Rain Warning data - updates every hour
        request = urllib.request.Request(urlWarning)
        try:
            parsed = objectify.parse(urlopen(request))
        except Exception:
            pass
        else:
            parsed = objectify.parse(urlopen(request))
            root = parsed.getroot()
            HRWmsg = root.item.warning.text
            HRWmsg = HRWmsg.strip()
            HRWtime = root.item.issue_datentime.text
            HRWtime = HRWtime.strip()
            if not ('NIL' in HRWmsg):
                print(HRWmsg)

        # set time for diff 30 mins
        timewrite_30min = datetime.now()

    if getTimeDifference(timewrite_10min, timeNow) > 10 :
        # collect Rainfall data - updates every 10 mins
        try:
            driver.get(urlRainfall)
        except Exception:
            pass
        else:
            # wait for page load
            time.sleep(3)
            html30mins = driver.page_source
            bsObj = BeautifulSoup(html30mins,"lxml")
            driver.close()
            # Get data timestamp
            element = bsObj.find("img", {"id":"basemap"})
            #pattern = re.compile('[0-9]+:[0-9]+')
            #rainfallTimestamp = pattern.findall(element.attrs['src'])[0]
            # load 30 mins rainfall data
            dataset30mins =  bsObj.findAll("",{"class":"sgr"})
            dfRainfall = pandas.DataFrame(columns=['StationId', 'rain30mins'])
            for data in dataset30mins:
                dfRainfall = dfRainfall.append({'StationId':data.get('id'), 'rain30mins':data.get_text()},ignore_index=True)
            dfRainfall = dfRainfall.set_index('StationId')
            dfRainfall.index.name = None
            #sprint(dfRainfall.head(2))

        # set time for diff 10 mins
        timewrite_10min = datetime.now()

    ## Process Events 
    ## Check for Events trigger
    if not (initFlag):
        # set up initial data for comparison
        dfTSBprev = dfTSB
        dfETTprev = dfETT
        dfTIprev = dfTI
        dfNowcastPrev = dfNowcast
        dfRainfallPrev = dfRainfall
        initFlag = True
    else:
        #compare changes
        if not (dfTSBprev.equals(dfTSB)):
            diffTSB = getDataframeDifferenceIndexed(dfTSBprev, dfTSB)
            print("\n" + datetime.now().strftime("%H:%M") + " TRAFFIC SPEED BAND")
            print(diffTSB)
            dfTSBprev = dfTSB
        if not (dfETTprev.equals(dfETT)):
            diffETT = getDataframeDifferenceIndexed(dfETTprev, dfETT)
            print("\n" + datetime.now().strftime("%H:%M") + " ESTIMATED TRVEL TIME")
            print(diffETT)
            dfETTprev = dfETT
        if not (dfTIprev.equals(dfTI)):
            diffTI = pandas.concat([dfTI, dfTIprev, dfTIprev]).drop_duplicates(keep=False)
            if not (diffTI.empty):
                print("\n" + datetime.now().strftime("%H:%M") + " TRAFFIC INCIDENCE")
                print(diffTI)
            dfTIprev = dfTI.copy()
        if not (dfNowcastPrev.equals(dfNowcast)):
            print("\n" + datetime.now().strftime("%H:%M") + " 2 HOUR FORECAST")
            diffNowcast = getDataframeDifferenceIndexed(dfNowcastPrev, dfNowcast)
            print(diffNowcast)
            dfNowcastPrev = dfNowcast
        if not (dfRainfallPrev.equals(dfRainfall)):
            diffRainfall = getDataframeDifferenceIndexed(dfRainfallPrev, dfRainfall)
            print("\n" + datetime.now().strftime("%H:%M") + " CURRENT RAINFALL")
            print(diffRainfall)
            dfRainfallPrev = dfRainfalls

    # wait 2 minutes
    time.sleep(120)
    
# on exit loop:
print('exit' + datetime.now())


