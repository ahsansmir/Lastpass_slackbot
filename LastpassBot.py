import slackclient
import os
import sys
import time
import string
import requests

def lpapicaller(email):
                payload0 = "cmd=getuserdata&username="+email+"&createaction=1&cid=<insert---CID---->&provhash=<----------Insert Lastpass Hash----------->"
                                url = 'https://lastpass.com/enterpriseapi.php'
                conn = requests.post(url, data=payload0) #headers=headers)
                print conn.status_code
                
                if 'No users found' in conn.text:
                                text1 = "No user was found, will procced on creating the user"
                                payload = "cmd=adduser&username="+email+"&createaction=1&cid=<insert---CID---->&provhash=<----------Insert Lastpass Hash----------->"
                                url = 'https://lastpass.com/enterpriseapi.php'
                                conn = requests.post(url, data=payload) #headers=headers)
                                #print conn.status_code
                                if 'OK' in conn.text:
                                        text3 = email + " was successfully provisioned, you should have an email invite. If you havent received an invite please ping the channel for help, thanks."
                                        return text3
                                else:
                                        text4 = "Opps, I did something wrong " + email + " was not provisioned, alerting Lastpass Enterprise Admins"
                                        return text4
                else:
                        text2 = "The email is already provisioned in Lastpass Enteprise, alerting Lastpass Admins"
                        print text2
                        return text2


slack_token = "<-----------Insert Slack Token------------>"

sc = slackclient.SlackClient(slack_token)

link = '<https://cdn.meme.am/instances/400x/33568413.jpg|That would be great>'

if sc.rtm_connect():
    while True:
        events = sc.rtm_read()
        for event in events:
            if (
                'channel' in event and
                'text' in event and
                event.get('type') == 'message'
            ):
                channel = event['channel']
                text = event['text']
                user_id = event['user']
                if "provision a lastpass account" in text.lower() and link not in text:
                    name = sc.api_call('users.info', user=user_id)
                    #print name
                    print user_id
                    name = name['user']
                    name = name['profile']
                    #print  name
                    nameR = name['real_name']
                    email = name['email']
                    print nameR
                    print email
                    sc.api_call(
                        'chat.postMessage',
                        channel="#tech-lastpass-support",
                        link_names=1,
                        text="let me check and get back to you <@"+user_id+">, confirming your email address "+email,
                        as_user='true:'
                    )
                    response  = lpapicaller(email)
                    print response
                    sc.api_call(
                      'chat.postMessage',
                      channel="#tech-lastpass-support",
                      link_names=1,
                      text="<@"+user_id+">, "+response,
                      as_user='true:'
                    )

        time.sleep(1)
else:
    print('Connection failed, invalid token?')
