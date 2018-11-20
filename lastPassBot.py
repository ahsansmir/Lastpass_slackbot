'''
Created on Feb 2, 2018
@author: Ahsan Mir
@note: lastpass bot scrubby!
'''

import slackclient
import time
import requests
import re
import yaml
import sys
import logging
import argparse
import traceback

# Adding a mode argument to switch between dev and prod
argparser = argparse.ArgumentParser(description='Slack Bot to provision Lastpass account, aka Scrubby')
argparser.add_argument("--mode", help="Start as either 'development' or 'production', default development")
args = argparser.parse_args()
if not args.mode:
    mode = 'dev'
else:
    mode = args.mode
if mode == 'development':
    mode = 'dev'
if mode == 'production':
    mode = 'prd'
if mode not in ['dev', 'prd']:
    logging.critical('Invalid mode')
    sys.exit()

# Logging level
logging.basicConfig(level=logging.DEBUG)

# Read parameters from files
config = 'config.yaml'
try:
    stream = open(config)
except:
    logging.critical('config file does not exist')
    sys.exit()
try:
    docs = yaml.load_all(stream)
    doc = docs.next()
except:
    logging.critical("config file is not well-formed")
    sys.exit()

# Extract tokens
yaml = doc
try:
    botid = yaml['botid_' + mode].lower()
    cid = yaml['lastpass']['cid']
    provhash = yaml['lastpass']['provhash_' + mode]
    slack_token = yaml['slack_token_' + mode]
    adminEmails = yaml['adminEmails']
except:
    logging.critical("Missing parameters in config file, check syntax")
    sys.exit()

# Regex for botid and email
bot__REGEX = "^<@(|[WU].+)>(.*)"
e_REGEX = "[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])"
emailReg = re.compile("(?i)^" + e_REGEX + "$")

# Lastpass api call to provision account, check whether an account already exists
def lpapicaller(email):
    payload0 = "cmd=getuserdata&username="+email+"&createaction=1&cid=" + cid + "&provhash=" + provhash
    url = 'https://lastpass.com/enterpriseapi.php'
    conn = requests.post(url, data=payload0)
    logging.debug(conn.status_code)
    if 'No users found' in conn.text:
        text1 = "No user was found, will procced on creating the user"
        logging.debug(text1)
        #return text1
        payload = "cmd=adduser&username="+email+"&createaction=1&cid=" + cid + "&provhash=" + provhash
        url = 'https://lastpass.com/enterpriseapi.php'
        conn = requests.post(url, data=payload)
        #logging.debug(conn.status_code
        if 'OK' in conn.text:
            text3 = email + " was successfully provisioned, you should have an email invite. If you havent received an invite please ping the channel for help, thanks."
            return text3
        else:
            text4 = "Opps, I did something wrong " + email + " was not provisioned, alerting Lastpass Enterprise Admins"
            return text4
    else:
        text2 = "The email already is provisioned in Lastpass Enteprise, alerting Lastpass Admins"
        logging.debug(text2)
        return text2

link = '<https://cdn.meme.am/instances/400x/33568413.jpg|That would be great>'

# Slack client wrapper for session timeout retry
class Slack:
    def __init__(self, slack_token):
        self.slack_token = slack_token
        self.sc = slackclient.SlackClient(slack_token)
        while not self.sc.rtm_connect():
            logging.critical('Connection to slack failed, retrying in 5 minutes')
            time.sleep(300)
            self.sc = slackclient.SlackClient(slack_token)
    
    def readEvents(self):
        while True:
            try:
                events = self.sc.rtm_read()
                return events
            except:
                self.__init__(self.slack_token)
    
    def postMessage(self, mes, thread_ts=None):
        while True:
            try:
                kwargs = {
                    'channel':"#tech-lastpass-support",
                    'link_names':1,
                    'text':mes,
                    'as_user':'true:'
                }
                if thread_ts:
                    kwargs['thread_ts'] = thread_ts
                self.sc.api_call(
                    'chat.postMessage',
                    **kwargs
                )
                return
            except:
                self.__init__(self.slack_token)
    
    def getUserProfile(self, user_id):
        while True:
            try:
                response = self.sc.api_call('users.info', user=user_id)
                return response
            except:
                self.__init__(self.slack_token)

sc = Slack(slack_token)
while True:
    try:
        events = sc.readEvents()
        for event in events:
            # Filter for message events
            if 'channel' in event and 'text' in event and event.get('type') == 'message':
                channel = event['channel']
                text = event['text']
                user_id = event['user']
                text = text.lower()
                ts = event['ts']
            else:
                continue
            
            keyword = 'provision a lastpass account'
            index = text.find(keyword)
            
            if index < 0 or link in text:
                continue
            
            index_next = index + len(keyword)
            # Provision account for another user, admin only
            if text[index_next: index_next+5] == ' for ' and text[index_next: index_next+7] != ' for me':
                try:
                    response = sc.getUserProfile(user_id)
                    name = response['user']
                    profile = name['profile']
                    nameR = profile['real_name']
                    profile_email = profile['email']    
                    logging.debug(nameR + ' <' + profile_email + '>')
                except:
                    # Handle the case when user profile is not found
                    logging.error('User profile is not found: ' + user_id)
                    continue
                
                #<mailto:a@b.com|a@b.com>
                emailtext = text[index_next+5:]
                sepIndex = emailtext.find('|')
                if sepIndex < 0:
                    email = ''
                else:
                    email = emailtext[sepIndex + 1: -1]
                match = emailReg.match(email)
                if not match:
                    logging.debug("Bad email address: " + email)
                    sc.postMessage('I can not identify the email address', ts)
                else:
                    if profile_email not in adminEmails and profile_email != email:
                        sc.postMessage('Sorry, this action is only for Lastpass admins ' + "<@"+user_id+">", ts)
                        continue
                    sc.postMessage("All right! <@"+user_id+">, confirming the user's email address "+email, ts)
                    response  = lpapicaller(email)
                    mes = "<@"+user_id+">, "+response
                    sc.postMessage(mes, ts)
            
            # Provision account for this user
            elif len(text) == index_next or text[index_next:].startswith(' for me'):
                try:
                    response = sc.getUserProfile(user_id)
                    name = response['user']
                    profile = name['profile']
                    nameR = profile['real_name']
                    email = profile['email']    
                    logging.debug(nameR + ' <' + email + '>')
                except:
                    # Handle the case when user profile is not found
                    logging.error('User profile is not found: ' + user_id)
                    mes = "I can't seem to find your user profile and email address."
                    sc.postMessage(mes, ts)
                    continue
                
                mes = "let me check and get back to you <@"+user_id+">, confirming your email address "+email
                sc.postMessage(mes, ts)
                response  = lpapicaller(email)
                mes = "<@"+user_id+">, "+response
                sc.postMessage(mes, ts)
            
            else:
                continue
                
    except:
        # Unknown error occurred, printing stack trace
        logging.error('Unknown error occurred')
        logging.error(traceback.format_exc())
    time.sleep(1)
