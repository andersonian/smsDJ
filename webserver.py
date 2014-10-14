''' launch flask app in seperate instance go to command line and launch ngrok on same port with command ngrok ####
'''
from flask import Flask, request, redirect
import twilio.twiml
import datetime
import traceback

app = Flask(__name__)

from gmusicapi import Mobileclient

api = Mobileclient()
musicPass = 'aaaaaaaaaaaaaaaa'
myEmail = 'email_here'
logged_in = api.login(myEmail, musicPass)


def find_track(artist, title):
    '''returns a string of the track ID'''
    artist = artist.title()
    title = title.title()
    band=''
    song=''
    ID = None
    results = api.search_all_access(artist + ' ' + title, max_results=5)
    best = False
    for hit in results['song_hits']:
        if 'best_result' in hit.keys():
            print 'found best'
            found = hit
            ID = found['track']['storeId']
            band = found['track']['artist']
            song = found['track']['title']
            best = True
    if not best:
        winner = 0
        for hit in results['song_hits']:
            if hit['score'] > winner:
                winner = hit['score']
                ID = hit['track']['storeId']
                band = hit['track']['artist']
                song = hit['track']['title']
        print 'highest score is ' + str(winner)
    playdict = {}
    playdict['ID'] = ID
    playdict['artist'] = band
    playdict['title'] = song
    if ID:
        return playdict
    else:
        print 'Failed'
        return None


def check_if_in_playlist(playID, songID):
    if playID and songID:
        alltracks = api.get_all_user_playlist_contents()
        playlistdict = {}
        for i in alltracks:
            if i['id'] == playID:
                playlistdict = i
        allsongs = []
        for track in playlistdict['tracks']:
            allsongs.append(track['trackId'])
        if songID in allsongs:
            print "That song was already in the list"
            inList = True
        else:
            print "Thats a new one"
            inList = False
        return inList
    else:
        return True


def add_to_play(playID, song_title, band=''):
    new_song = find_track(band, song_title)
    if new_song:
        artist = new_song['artist'].encode('ascii', 'ignore').decode('ascii')
        song = new_song['title'].encode('ascii', 'ignore').decode('ascii')
        if artist == 'Rick Astley' and song == 'Never Gonna Give You Up':
            return ('Astley', song, artist)
        else:
            existing = check_if_in_playlist(playID, new_song['ID'])
            if not existing:
                if new_song:
                    api.add_songs_to_playlist(playID, new_song['ID'])
                else:
                    print "Couldn't find that song Try again?"
                return ('Added', song, artist)
            elif existing:
                print 'already in the playlist'
                return ('Duplicate', song, artist)
    else:
        return ('Failed', '', '')


def process_sms(textstr):
    if len(textstr.split(',')) > 1:
        song = textstr.split(',')[1]
        artist = textstr.split(',')[0]
    else:
        song = textstr.split(',')[0]
        artist = ''
    return (artist, song)


playlists = api.get_all_playlists()
dt = datetime.datetime.now()
plname = 'sms_' + str(dt.month) + '_' + str(dt.day) + '_' + str(dt.year)
summerlist = False
for i in playlists:
    if plname in i['name'].lower():
        summerlist = i['id']
if not summerlist:
    api.create_playlist(name=plname)
    api.get_all_playlists()
    for i in playlists:
        if plname in i['name'].lower():
            summerlist = i['id']


@app.route("/", methods=['GET', 'POST'])
def listener():
    """Respond to incoming calls with a simple text message."""
    resp = twilio.twiml.Response()
    from_number = request.values.get('From', None)
    body = request.values.get('Body', None)
    music = process_sms(body)
    print"got a text from: " + str(from_number)
    print "They want to add " + str(music)
    try:
        success = add_to_play(summerlist, song_title=music[1], band=music[0])
        print success
        if success[0] == 'Added':
            print 'Adding'
            your_text = 'I added ' + success[1] + ' by ' + success[2] + ' to the playlist. Thanks!'
            resp.message(your_text)
        elif success[0] == 'Duplicate':
            print 'Already there'
            your_text = 'The song: ' + success[1] + ' by ' + success[2] + ' was already in the playlist. ' \
                                                                          '  Chose something else!'
            resp.message(your_text)
        elif success[0] == 'Astley':
            print 'Astley Alert!'
            your_text = 'You better give it up! ' + success[1] + ' by ' + success[2] + ' is never going on my playlist! ' \
                                                                                       'http://bit.ly/1gB3px0'
            resp.message(your_text)
        elif success[0] == 'Failed':
            print 'couldnt find anything'
            your_text = "Couldn't find a song that matched your search:"+ str(body)+' Check spelling or add specific ' \
                                                                                    'artist in the from artist, title'
            resp.message(your_text)
    except:
        print "failed on add to playlist"
        print traceback.format_exc()
        body = "Sorry something went wrong when I searched for " + body + ' Try Again? For better accuracy try artist, title'
        resp.message(body)
    return str(resp)


if __name__ == "__main__":
    app.run(debug=True)