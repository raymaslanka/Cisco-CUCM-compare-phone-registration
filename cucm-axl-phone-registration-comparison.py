# zeep is a SOAP client built on top of lxml and requests
# requests simplifies sending HTTP requests
# lxml simplifies processing XML and HTML data
# urllib3 is a HTTP client

# import the packages we need to communicate with SOAP and HTTP servers
# and process XML and HTML data
from zeep import Client
from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.plugins import HistoryPlugin
from requests import Session
from requests.auth import HTTPBasicAuth
from lxml import etree
import urllib3
import sqlite3

rntm = input('Are you running this PRe or POst upgrade [PR / PO]:')

# Here we are running for the first time or to set a baseline
# so let's eliminate old stuff and create new db if required or just tables
if rntm == 'PR':
    print("========== running pre DB setup ==========")
    SQL_node_id = 'node_id_pre'

    conn = sqlite3.connect('phoneregister.sqlite')
    cur = conn.cursor()

    # Make some fresh tables using executescript()
    cur.executescript('''
    DROP TABLE IF EXISTS node;
    DROP TABLE IF EXISTS phone;

    CREATE TABLE node (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT UNIQUE
    );

    CREATE TABLE phone (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT UNIQUE,
        description TEXT UNIQUE,
        node_id_pre INTEGER,
        node_id_pre_status TEXT,
        node_id_post INTEGER,
        node_id_post_status TEXT
    );
    ''')
# We have the initial db setup so here we just connect
elif rntm == 'PO':
    print("========== using existing DB ==========")
    SQL_node_id = 'node_id_post'

    conn = sqlite3.connect('phoneregister.sqlite')
    cur = conn.cursor()
else:
    print("========== Not sure what you were expecting ==========")


# allow program to continue running without
# warnings about not verifying HTTPS certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# your CUCM AXL user name and password goes here
# as well as the URL ponting to your CUCM Real-Time Service APIs
# this changes over versions
# in version 11.5 likely https://<your CUCM name or IP>:8443/realtimeservice2/services/RISService70?wsdl
username = '<AXL user here>'
password = '<your password here>'
wsdl = 'https://<your CUCM PUB here>:8443/realtimeservice2/services/RISService70?wsdl'

# define how the requests  package will authenticate to CUCM
# CUCM AXL uses Basic authentication
session = Session()
session.verify = False
session.auth = HTTPBasicAuth(username, password)
#define how zeep then uses this requests session to authenicate
transport = Transport(cache=SqliteCache(), session=session, timeout=20)
history = HistoryPlugin()
client = Client(wsdl=wsdl, transport=transport, plugins=[history])
factory = client.type_factory('ns0')

# Here we need to decide what specific devices we are tracking
# if we are indeed tracking specific devices
# macs = ['SEPAC7E8AB6891B', 'CSFRMASLANKA']
# macs = ['*'] for all
macs = ['*']
item=[]
for mac in macs:
    item.append(factory.SelectItem(Item=mac))
Item = factory.ArrayOfSelectItem(item)

stateInfo = ''
criteria = factory.CmSelectionCriteria(
    MaxReturnedDevices = 1000,
    DeviceClass='Phone',
    # Model=537,
    # use model 255 for all
    Model=255,
    #Status='Registered',
    NodeName='',
    SelectBy='Name',
    SelectItems=Item,
    Protocol='Any',
    DownloadStatus='Any'
)

# Here we leverage Zeep as the SOAP client to query CUCM with the selectCmDevice method
result = client.service.selectCmDevice(stateInfo, criteria)

print('========== Printing zeep result ==========')
# uncomment line below to see pretty JSON
# print(result)

print('========== Printing etree result ==========')
# if troubleshooting soap envelope, uncomment lines below
# for hist in [history.last_sent, history.last_received]:
#   print(etree.tostring(hist["envelope"], encoding="unicode", pretty_print=True))

print('========== Printing stuff you might want to see and DB updates ==========')

# loop through CUCM cluster nodes
# and write data about what devices are registered where
for node in result['SelectCmDeviceResult']['CmNodes']['item']:
    # uncomment line below to see nodes
    # print('Node:',node['Name'])
    # write node names to DB
    cur.execute('''INSERT OR IGNORE INTO node (name) VALUES ( ? )''', (node['Name'], ) )
    # get node_id that was just created from DB
    cur.execute('SELECT id FROM node WHERE name = ? ', (node['Name'], ))
    node_id = cur.fetchone()[0]
    # if node_id = None:
    #     node_id = 0
    if node['CmDevices'] != None:
        for device in node['CmDevices']['item']:
            # uncomment line below to see device details
            # print('Device:',device['Name'], "|", device['Description'],"|", device['Status'])
            # write phones to DB with node_id from outer loop
            if rntm == 'PR':
                # if this is PRe upgrade or reboot we really only care about registered devices
                # record the device and what node it's registerd to
                if device['Status'] == 'Registered':
                    cur.execute('''INSERT OR IGNORE INTO phone (name, description, node_id_pre, node_id_pre_status) VALUES ( ?, ?, ?,? )''', (device['Name'], device['Description'], node_id,device['Status'] ) )
            # if this is post upgrade or reboot, we will to update the phone table with where it's registered now
            # or perhaps it's no longer registered
            # we'll use a SQL query later to determine which missing devices to look out for
            elif rntm == 'PO':
                #if device['Status'] == 'Registered':
                    cur.execute('''UPDATE phone SET node_id_post=?, node_id_post_status=? WHERE name=?''', (node_id, device['Status'], device['Name'] ) )

conn.commit()

if rntm == 'PO':
    # find in DB a phone that was registered and now isn't
    # this is likely most important
    print ('========== THESE DEVICES ARE NO LONGER REGISTERED! ==========')
    cur.execute('''select * from phone where phone.node_id_pre_status = ? and phone.node_id_post_status != ?''', ('Registered', 'Registered'))
    result = cur.fetchall()
    for row in result:
        print (row[1],'|',row[2])
    print ('========== THESE DEVICES ARE NOW REGISTERED TO A DIFFERENT SERVER! ==========')
    cur.execute('''select * from phone where phone.node_id_pre is not phone.node_id_post''')
    result = cur.fetchall()
    for row in result:
        print (row[1],'|',row[2])
