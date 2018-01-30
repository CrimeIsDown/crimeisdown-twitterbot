#!/usr/bin/env python

from dotenv import load_dotenv
from os import getenv
from os.path import join, dirname
import sys
import json
import re
import tweepy
import googlemaps
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import auth

def end(exception, message):
    if error:
        print(error, file=sys.stderr)
    sys.exit(1)


def initTwit():
    try:
        auth = tweepy.OAuthHandler(getenv('CONSUMER_KEY'), getenv('CONSUMER_SECRET'))
        auth.set_access_token(getenv('ACCESS_TOKEN'), getenv('ACCESS_TOKEN_SECRET'))
        api = tweepy.API(auth)
    except Exception as e:
        end(e, 'Config cound not be loaded, startup cannot continue. Exiting...')
    return api


def buildLocationRegex():
    global_prefix = '(^|\s)'
    direction = '( [nswe](\.?))'
    street_suffix = '(court|ct|street|st|drive|dr|lane|ln|road|rd|blvd|parkway|pkwy|place|pl)'
    alphanumeric_street_name = '[a-z0-9]{2,15}'
    alpha_street_name = '[a-z]{2,15}'
    intersection_separator = ' ?(and|\/|&) ?'

    full_street_name = '{}( {})?( {})?'.format(alphanumeric_street_name, alpha_street_name, street_suffix)

    digit_single = '\d'
    digits_2to5 = digit_single + '{2,5}'
    address = '({}{}?|{}{}) {}'.format(digits_2to5, direction, digit_single, direction, full_street_name)
    intersection = '({}){}({})'.format(full_street_name, intersection_separator, full_street_name)
    full_regex = '{}(({})|({}))'.format(global_prefix, address, intersection)
    return re.compile(full_regex, re.IGNORECASE)


class ZoneStreamListener(tweepy.StreamListener):

    def on_status(self, status):
        #self.checkForHashtag(status)
        #self.checkForZone(status)
        self.checkForLocation(status)

    def on_error(self, status_code):
        if status_code == 420:
            #returning False in on_data disconnects the stream
            return False

    def checkForHashtag(self, status):
        matches = re.search(r'#crimeisdown', status.text.lower())
        if matches and 'spotnewsonig' not in status.text.lower() and status.user.screen_name.lower() is not 'spotnewsonig':
            status.retweet()

    def checkForLocation(self, status):
        if type(status) is str:
            tweet_text = status
        else:
            tweet_text = status.text
        lines = re.split('\n|\|', tweet_text.lower())
        for line in lines:
            matches = re.findall(location_regex, line.strip())
            if len(matches):
                for match in matches:
                    location = match[1].strip()
                    if 'http' in location:
                        pass
                    print('INPUT: ' + line + '\nOUTPUT: ' + location)
                    geocode_result = gmaps.geocode(location, bounds=chicagoland_bounds)
                    if len(geocode_result) and re.search(r', IL [\d-]+, USA', geocode_result[0]['formatted_address']):
                        destination = geocode_result[0]['geometry']['location']
                        print(geocode_result[0]['formatted_address'])
                        mode = 'transit'
                        for uid, origins in alerts.items():
                            user = auth.get_user(uid)
                            alert_message = ''
                            for origin, distance in origins.items():
                                latlng = origin.replace('_', '.').split(',')
                                origin = {'lat': latlng[0], 'lng': latlng[1]}
                                distance_result = gmaps.distance_matrix(origin, destination, mode=mode)
                                if distance_result['rows'][0]['elements'][0]['status'] == 'OK':
                                    if 'km' in distance:
                                        max_dist_meters = float(distance.replace('km', '')) * 1000
                                        if distance_result['rows'][0]['elements'][0]['distance']['value'] <= max_dist_meters:
                                                alert_message += '{}: {},{} is {} away from {} via {}\n'.format(user.email, origin['lat'], origin['lng'], distance_result['rows'][0]['elements'][0]['distance']['text'], geocode_result[0]['formatted_address'], mode)
                                    if 'min' in distance:
                                        max_duration_seconds = float(distance.replace('min', '')) * 60
                                        if distance_result['rows'][0]['elements'][0]['duration']['value'] <= max_duration_seconds:
                                                alert_message += '{}: {},{} is {} away from {} via {}\n'.format(user.email, origin['lat'], origin['lng'], distance_result['rows'][0]['elements'][0]['duration']['text'], geocode_result[0]['formatted_address'], mode)
                            if len(alert_message):
                                print('We would be sending the following message:')
                                print(alert_message[:-1])
                                print('-------------')
                        # we were able to parse the first address, don't go any further
                        break


    def checkForZone(self, status):
        matches = re.search(r'(((citywide |cw)[1,6])|((zone |z)(1[0-3]|[1-9])))|(^((main)|(englewood))$)', status.text.lower())
        if matches:
            for value in status.text.lower().split(' '):
                if value.find(matches.group(0))>0 and (value.find('://')>0 or value.find('@')==0):
                    return False
            self.retweetWithStream(status, matches)

    def retweetWithStream(self, status, matches):
        rt = '\nhttps://twitter.com/' + status.user.screen_name + '/status/' + status.id_str
        if len(status.text) < 31 and 'spotnewsonig' not in status.text.lower():
            channel = livestreams[matches.group(0).upper()
                                                .replace('ZONE ', 'Z')
                                                .replace('CITYWIDE ', 'CW')
                                                .replace('MAIN', 'CFD-Fire')
                                                .replace('ENGLEWOOD', 'CFD-Fire')]
            if channel:
                statusupdate = 'LISTEN LIVE to ' + channel['shortname'] + ' at ' + channel['feedUrl'] + '/web' + rt
                self.api.update_status(status=statusupdate, in_reply_to_status_id=status.id_str)


print('Initializing bot...')

load_dotenv(join(dirname(__file__), '.env'))



cred = credentials.Certificate(join(dirname(__file__), getenv('FIREBASE_CREDENTIAL_FILE')))

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://crimeisdown.firebaseio.com'
})

alerts = db.reference('alerts').get()

try:
    with open('onlinestreams.json') as fileContents:
        livestreams = json.load(fileContents)
except Exception as e:
    end(e, 'Cannot find online streams data, startup cannot continue. Exiting...')

location_regex = buildLocationRegex()

api = initTwit()

gmaps = googlemaps.Client(key=getenv('GOOGLE_MAPS_API_KEY'))
chicagoland_bounds = {
    'southwest': '41.60218817897012,-87.9728821400663',
    'northeast': '42.05134582102988,-87.37011785993366'
}

print('Bot initialized successfully. Now starting streaming.')
streamListener = ZoneStreamListener(api=api)
#streamListener.checkForLocation("""Chicago
#Wells St & Congress Pkwy
#Ems plan 2 now for the accident with injuries.""")
#streamListener.checkForLocation('Chicago | WRKF | 3910 W Congress Pkwy | Fire in the rear. 699,317')
#streamListener.checkForLocation('Burbank | Still Alarm | 8200 blk of Lockwood Ave. | Fire in a residence. Pd extinguished the fire. Light smoke showing on arrival. 099')
#streamListener.checkForLocation('rt @po_potatoes: z10 person shot at pulaski and 26th #chicagoscanner #pewpew @w_h_thompson @crimeisdown #crimeisdown')
for status in tweepy.Cursor(api.home_timeline).items(50):
    streamListener.checkForLocation(status)

#stream = tweepy.Stream(auth=api.auth, listener=streamListener)
#stream.userstream()
