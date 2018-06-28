#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Petra Febrianto
#
# Created:     02/04/2018
# Copyright:   (c) Petra Febrianto 2018
# Licence:     <your licence>

# misal ingin setting ip -->
#if __name__ == "__main__":
#   app.run(host='192.168.0.118')
#-------------------------------------------------------------------------------

from flask import Flask, render_template, request, redirect, send_file
import json
import io
import requests
from requests.auth import HTTPBasicAuth
from subprocess import Popen, PIPE
import time
from werkzeug import secure_filename
import json
import HTMLParser

app = Flask(__name__)

###############################################################################################
#Global Variables

global controllerIPAddress
controllerIPAddress = '10.10.5.101'

global controllerTCPPort
controllerTCPPort = '8181'

global flowXML
global flowURL
global flowJson
global miscFlow

connectedNodeIDList = []
connectedNodeInfoList = []

global savedFlows
savedFlows = []
global savedFlowstoClient
savedFlowstoClient = {}
global savedFlowsCount
savedFlowsCount = 0;
global savedFlowsJSON
savedFlowsJSON = {}

###############################################################################################

def sendFlow(sendflowXML,sendflowURL):
  headers = {'Accept':'application/xml','Content-type':'application/xml'}
  response = requests.put(sendflowURL, data = sendflowXML, headers = headers, auth=HTTPBasicAuth('admin', 'admin'))
  print (response.status_code)

def getResponse(url):
  response = requests.get(url, auth=HTTPBasicAuth('admin', 'admin'))

  if(response.ok):
    return json.loads(response.content)
  else:
    response.raise_for_status()
    return []

def getConnectedIDList():
  global connectedNodeIDList
  global connectedNodeInfoList

  while (len(connectedNodeIDList) > 0):
    connectedNodeIDList.remove(connectedNodeIDList[0])
    connectedNodeInfoList.remove(connectedNodeInfoList[0])

  unparsedResponse = getResponse(str("http://"+str(controllerIPAddress)+":"+str(controllerTCPPort)+"/restconf/operational/opendaylight-inventory:nodes/"))

  if unparsedResponse != []:
    for i in unparsedResponse["nodes"]["node"]:
      try:
        connectedNodeIDList.append(i["id"])
        for j in i["node-connector"]:
          nodeName = 'Unavailable'
          if str(j["id"]) == str(i["id"]+":LOCAL"):
            nodeName = j["flow-node-inventory:name"]
            break
        connectedNodeInfoList.append({"NodeID" : i["id"], "IP" : i["flow-node-inventory:ip-address"], "Name" : nodeName, "OpenflowVersion" : "Openflow 1.3"})
        print ("Openflow 1.3 Switch Detected")
      except KeyError:
        print ("Openflow 1.0 Switch Detected")
        connectedNodeInfoList.append({"NodeID" : i["id"], "IP" : "Unavailable", "Name" : "Unavailable", "OpenflowVersion" : "Openflow 1.0"})



def initProcess():
  getConnectedIDList()
  print (json.dumps(connectedNodeInfoList, indent=4, sort_keys=True))
  print (json.dumps(connectedNodeIDList, indent=4, sort_keys=True))

def checkIfKeyExist(key, JsonList):
  if JsonList != []:
    if key in JsonList:
      print('available')
      return True

  print('not available')
  return False

@app.route('/')
def index():
  try:
    initProcess()
  except:
    print("initProcess tidak berjalan")
  return render_template('index.html', connectedNodeInfoList=connectedNodeInfoList)


@app.route('/push')
def pushFlow():
   return render_template('pushFlow.html',savedFlowsTable=savedFlowstoClient, connectedNodeIDList=connectedNodeIDList, savedFlowsJSON=savedFlowsJSON)

@app.route('/pushAll')
def pushAll():

  global savedFlowstoClient 
  global savedFlows
  global savedFlowsJSON

  i = 0;
  while (i < len(savedFlows)):
    sendFlow(str(savedFlows[i]['XML']),str(savedFlows[i]['URL']))
    i = i+1;

  savedFlowstoClient  = {}
  while (len(savedFlows) > 0):
  	savedFlows.remove(savedFlows[0])

  savedFlowsJSON = {}

  return render_template('pushFlow.html',savedFlowsTable=savedFlowstoClient, connectedNodeIDList=connectedNodeIDList, savedFlowsJSON=savedFlowsJSON)

@app.route('/saveFlow',methods = ['POST', 'GET'])
def saveFlow():

   global savedFlowstoClient  
   global savedFlows
   global savedFlowsCount

   if request.method == 'POST':
      result_python = request.form

      identityFlow = '<flow-name>'+str(result_python["FlowName"])+'</flow-name><id>'+str(result_python["FlowID"])+'</id><table_id>'+str(result_python["TableID"])+'</table_id><priority>'+str(result_python["Priority"])+'</priority>'
      print(identityFlow)

      #MatchFlow
      matchFlow = '<match>'
      matchDescription = ''

      if result_python["EthernetType"] != "" or result_python["EthernetSource"] != "" or result_python["EthernetDestination"] != "":
        matchFlow = matchFlow + '<ethernet-match>'

        if result_python["EthernetType"] != "":
          matchFlow = matchFlow + '<ethernet-type><type>'+str(result_python["EthernetType"])+'</type></ethernet-type>'
          matchDescription = matchDescription +'Eth Type:' + str(result_python["EthernetType"]) + ', '

        if result_python["EthernetSource"] != "":
          matchFlow = matchFlow + '<ethernet-source><address>'+str(result_python["EthernetSource"])+'</address></ethernet-source>'
          matchDescription = matchDescription +'Eth Source:' + str(result_python["EthernetSource"]) + ', '

        if result_python["EthernetDestination"] != "":
          matchFlow = matchFlow + '<ethernet-destination><address>'+str(result_python["EthernetDestination"])+'</address></ethernet-destination>'
          matchDescription = matchDescription +'Eth Dest:' + str(result_python["EthernetDestination"]) + ', '

        matchFlow = matchFlow + '</ethernet-match>'


      if result_python["IPSource"] != "":
        matchFlow = matchFlow + '<ipv4-source>'+str(result_python["IPSource"])+'</ipv4-source>'
        matchDescription = matchDescription +'IP Source:' + str(result_python["IPSource"]) + ', '

      if result_python["IPDestination"] != "":
        matchFlow = matchFlow + '<ipv4-destination>'+str(result_python["IPDestination"])+'</ipv4-destination>'
        matchDescription = matchDescription +'IP Destination:' + str(result_python["IPDestination"]) + ', '

      if result_python["InPort"] != "":
        matchFlow = matchFlow + '<in-port>'+str(result_python["InPort"])+'</in-port>'
        matchDescription = matchDescription +'In Port:' + str(result_python["InPort"]) + ', '

      if result_python["TCPSource"] != "":
        matchFlow = matchFlow + '<tcp-source-port>'+str(result_python["TCPSource"])+'</tcp-source-port>'
        matchDescription = matchDescription +'TCP Source:' + str(result_python["TCPSource"]) + ', '

      if result_python["TCPDestination"] != "":
        matchFlow = matchFlow + '<tcp-destination-port>'+str(result_python["TCPDestination"])+'</tcp-destination-port>'
        matchDescription = matchDescription +'TCP Destination:' + str(result_python["TCPDestination"]) + ', '

      matchFlow = matchFlow + '</match>'
      print(matchFlow)

      matchDescription=matchDescription[:-2]
      actionDescription = ''

      #Actions Revamp
      actionFlow = '<instructions><instruction><order>0</order>'
      actionOrder = 0

      if str(result_python.getlist("GotoTableAction")) == "[u'on']":
        actionFlow = actionFlow +'<go-to-table><table_id>'+str(result_python["GotoTableNumbers"])+'</table_id></go-to-table>'
        actionDescription = actionDescription +'Go to Table: ' + str(result_python["GotoTableNumbers"]+", ")

      else:
        actionFlow = actionFlow + '<apply-actions>'

        if str(result_python.getlist("DropAction")) == "[u'on']":
          actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><drop-action/></action>'
          actionDescription = actionDescription +'Drop, '
          actionOrder = actionOrder + 1

        if str(result_python.getlist("FloodAction")) == "[u'on']":
          actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>FLOOD</output-node-connector><max-length>60</max-length></output-action></action>'
          actionDescription = actionDescription +'Flood, '
          actionOrder = actionOrder + 1

        if str(result_python.getlist("NormalAction")) == "[u'on']":
          actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>NORMAL</output-node-connector><max-length>60</max-length></output-action></action>'
          actionDescription = actionDescription +'Normal, '
          actionOrder = actionOrder + 1

        if str(result_python.getlist("ControllerAction")) == "[u'on']":
          actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>CONTROLLER</output-node-connector><max-length>60</max-length></output-action></action>'
          actionDescription = actionDescription +'Controller, '
          actionOrder = actionOrder + 1

        if str(result_python.getlist("OutputAction")) == "[u'on']":
          outportList = str(result_python["OutputActionPorts"]).split(",");
          actionDescription = actionDescription +'Out Port: ' + str(result_python["OutputActionPorts"]+", ")

          while (len(outportList) > 0):
            actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>'+outportList[0]+'</output-node-connector><max-length>60</max-length></output-action></action>'
            outportList.remove(outportList[0])
            actionOrder = actionOrder + 1

        actionFlow = actionFlow +'</apply-actions>'

      actionFlow = actionFlow + '</instruction></instructions>'
      actionDescription = actionDescription[:-2]
  
      #MiscFlow
      miscFlow = ""
      if result_python["Cookie"] != "":
        miscFlow = miscFlow + '<cookie>'+str(result_python["Cookie"])+'</cookie>'

      if result_python["CookieMask"] != "":
        miscFlow = miscFlow + '<cookie_mask>'+str(result_python["CookieMask"])+'</cookie_mask>'

      if result_python["HardTimeout"] != "":
        miscFlow = miscFlow + '<hard-timeout>'+str(result_python["HardTimeout"])+'</hard-timeout>'

      if result_python["IdleTimeout"] != "":
        miscFlow = miscFlow + '<idle-timeout>'+str(result_python["IdleTimeout"])+'</idle-timeout>'

      ################################################################################################################
      print(actionFlow)
      print(matchFlow)
      print(miscFlow)

      #Penyusun XML
      flowXML = '<?xml version="1.0" encoding="UTF-8" standalone="no"?><flow xmlns="urn:opendaylight:flow:inventory"><strict>false</strict>'+identityFlow+actionFlow+matchFlow+miscFlow+'</flow>'
      #PenyusunURL
      flowURL = "http://"+str(controllerIPAddress)+":"+str(controllerTCPPort)+"/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(result_python["NodeID"])+"/table/"+str(result_python["TableID"])+"/flow/"+str(result_python["FlowID"])
      
      if checkIfKeyExist(str(result_python["NodeID"]), savedFlowstoClient):
        savedFlowstoClient[str(result_python["NodeID"])].append({'1TableID': str(result_python["TableID"]), '2FlowID': str(result_python["FlowID"]),'3Priority': str(result_python["Priority"]), '4Matches': str(matchDescription), '5Actions': str(actionDescription), '6Count' : str(savedFlowsCount)})
      else: 
        savedFlowstoClient[str(result_python["NodeID"])] = [{'1TableID': str(result_python["TableID"]), '2FlowID': str(result_python["FlowID"]),'3Priority': str(result_python["Priority"]), '4Matches': str(matchDescription), '5Actions': str(actionDescription), '6Count' : str(savedFlowsCount)}]

      savedFlows.append({'XML': flowXML, 'URL' : flowURL, 'Count' : savedFlowsCount})
      savedFlowsJSON[savedFlowsCount] = result_python
      savedFlowsCount = savedFlowsCount + 1;

      print (json.dumps(savedFlowsJSON, indent=4, sort_keys=True))
      print ("##################")
      
      return render_template('pushFlow.html',savedFlowsTable=savedFlowstoClient, connectedNodeIDList=connectedNodeIDList, savedFlowsJSON=savedFlowsJSON)

@app.route('/upload')
def uploadFlow():
   return render_template('uploadFlow.html')

@app.route('/uploadResult', methods = ['GET', 'POST'])
def uploadResult():
   if request.method == 'POST':
      flowJson = json.load(request.files['file'])

      global savedFlowstoClient 
      global savedFlows
      global savedFlowsJSON
      global savedFlowsCount


      savedFlowstoClient  = {}
      while (len(savedFlows) > 0):
        savedFlows.remove(savedFlows[0])
      savedFlowsJSON = {}

      for i in flowJson:
        result_python = flowJson[i]

        identityFlow = '<flow-name>'+str(result_python["FlowName"])+'</flow-name><id>'+str(result_python["FlowID"])+'</id><table_id>'+str(result_python["TableID"])+'</table_id><priority>'+str(result_python["Priority"])+'</priority>'
        print(identityFlow)

        #MatchFlow
        matchFlow = '<match>'
        matchDescription = ''

        if result_python["EthernetType"] != "" or result_python["EthernetSource"] != "" or result_python["EthernetDestination"] != "":
          matchFlow = matchFlow + '<ethernet-match>'

          if result_python["EthernetType"] != "":
            matchFlow = matchFlow + '<ethernet-type><type>'+str(result_python["EthernetType"])+'</type></ethernet-type>'
            matchDescription = matchDescription +'Eth Type:' + str(result_python["EthernetType"]) + ', '

          if result_python["EthernetSource"] != "":
            matchFlow = matchFlow + '<ethernet-source><address>'+str(result_python["EthernetSource"])+'</address></ethernet-source>'
            matchDescription = matchDescription +'Eth Source:' + str(result_python["EthernetSource"]) + ', '

          if result_python["EthernetDestination"] != "":
            matchFlow = matchFlow + '<ethernet-destination><address>'+str(result_python["EthernetDestination"])+'</address></ethernet-destination>'
            matchDescription = matchDescription +'Eth Dest:' + str(result_python["EthernetDestination"]) + ', '

          matchFlow = matchFlow + '</ethernet-match>'

        if result_python["IPSource"] != "":
          matchFlow = matchFlow + '<ipv4-source>'+str(result_python["IPSource"])+'</ipv4-source>'
          matchDescription = matchDescription +'IP Source:' + str(result_python["IPSource"]) + ', '

        if result_python["IPDestination"] != "":
          matchFlow = matchFlow + '<ipv4-destination>'+str(result_python["IPDestination"])+'</ipv4-destination>'
          matchDescription = matchDescription +'IP Destination:' + str(result_python["IPDestination"]) + ', '

        if result_python["InPort"] != "":
          matchFlow = matchFlow + '<in-port>'+str(result_python["InPort"])+'</in-port>'
          matchDescription = matchDescription +'In Port:' + str(result_python["InPort"]) + ', '

        if result_python["TCPSource"] != "":
          matchFlow = matchFlow + '<tcp-source-port>'+str(result_python["TCPSource"])+'</tcp-source-port>'
          matchDescription = matchDescription +'TCP Source:' + str(result_python["TCPSource"]) + ', '

        if result_python["TCPDestination"] != "":
          matchFlow = matchFlow + '<tcp-destination-port>'+str(result_python["TCPDestination"])+'</tcp-destination-port>'
          matchDescription = matchDescription +'TCP Destination:' + str(result_python["TCPDestination"]) + ', '


        matchFlow = matchFlow + '</match>'
        print(matchFlow)

        matchDescription=matchDescription[:-2]
        actionDescription = ''

        #Actions Revamp
        actionFlow = '<instructions><instruction><order>0</order>'
        actionOrder = 0

        if checkIfKeyExist('GotoTableAction',result_python):
          actionDescription = actionDescription +'Go to Table: ' + str(result_python["GotoTableNumbers"]+", ")
          actionFlow = actionFlow +'<go-to-table><table_id>'+str(result_python["GotoTableNumbers"])+'</table_id></go-to-table>'

        else:

          actionFlow = actionFlow + '<apply-actions>'

          if checkIfKeyExist('DropAction',result_python):
            actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><drop-action/></action>'
            actionDescription = actionDescription +'Drop, '
            actionOrder = actionOrder + 1

          if checkIfKeyExist('FloodAction',result_python):
            actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>FLOOD</output-node-connector><max-length>60</max-length></output-action></action>'
            actionDescription = actionDescription +'Flood, '
            actionOrder = actionOrder + 1

          if checkIfKeyExist('NormalAction',result_python):
            actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>NORMAL</output-node-connector><max-length>60</max-length></output-action></action>'
            actionDescription = actionDescription +'Normal, '
            actionOrder = actionOrder + 1

          if checkIfKeyExist('ControllerAction',result_python):
            actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>CONTROLLER</output-node-connector><max-length>60</max-length></output-action></action>'
            actionDescription = actionDescription +'Controller, '
            actionOrder = actionOrder + 1

          if checkIfKeyExist('OutputAction',result_python):
            outportList = str(result_python["OutputActionPorts"]).split(",");
            actionDescription = actionDescription +'Out Port: ' + str(result_python["OutputActionPorts"]+", ")

            while (len(outportList) > 0):
              actionFlow = actionFlow +'<action><order>'+str(actionOrder)+'</order><output-action><output-node-connector>'+outportList[0]+'</output-node-connector><max-length>60</max-length></output-action></action>'
              outportList.remove(outportList[0])
              actionOrder = actionOrder + 1

          actionFlow = actionFlow +'</apply-actions>'

        actionFlow = actionFlow + '</instruction></instructions>'
        actionDescription = actionDescription[:-2]
    
        #MiscFlow
        miscFlow = ""
        if result_python["Cookie"] != "":
          miscFlow = miscFlow + '<cookie>'+str(result_python["Cookie"])+'</cookie>'

        if result_python["CookieMask"] != "":
          miscFlow = miscFlow + '<cookie_mask>'+str(result_python["CookieMask"])+'</cookie_mask>'

        if result_python["HardTimeout"] != "":
          miscFlow = miscFlow + '<hard-timeout>'+str(result_python["HardTimeout"])+'</hard-timeout>'

        if result_python["IdleTimeout"] != "":
          miscFlow = miscFlow + '<idle-timeout>'+str(result_python["IdleTimeout"])+'</idle-timeout>'

        ################################################################################################################
        print(actionFlow)
        print(matchFlow)
        print(miscFlow)

        #Penyusun XML
        flowXML = '<?xml version="1.0" encoding="UTF-8" standalone="no"?><flow xmlns="urn:opendaylight:flow:inventory"><strict>false</strict>'+identityFlow+actionFlow+matchFlow+miscFlow+'</flow>'
        #PenyusunURL
        flowURL = "http://"+str(controllerIPAddress)+":"+str(controllerTCPPort)+"/restconf/config/opendaylight-inventory:nodes/node/openflow:"+str(result_python["NodeID"])+"/table/"+str(result_python["TableID"])+"/flow/"+str(result_python["FlowID"])
        


        if checkIfKeyExist(str(result_python["NodeID"]), savedFlowstoClient):
          savedFlowstoClient[str(result_python["NodeID"])].append({'1TableID': str(result_python["TableID"]), '2FlowID': str(result_python["FlowID"]),'3Priority': str(result_python["Priority"]), '4Matches': str(matchDescription), '5Actions': str(actionDescription), '6Count' : str(savedFlowsCount)})
        else: 
          savedFlowstoClient[str(result_python["NodeID"])] = [{'1TableID': str(result_python["TableID"]), '2FlowID': str(result_python["FlowID"]),'3Priority': str(result_python["Priority"]), '4Matches': str(matchDescription), '5Actions': str(actionDescription), '6Count' : str(savedFlowsCount)}]
        
        savedFlows.append({'XML': flowXML, 'URL' : flowURL, 'Count' : savedFlowsCount})

        savedFlowsJSON[savedFlowsCount] = result_python

        print (json.dumps(savedFlows, indent=4, sort_keys=True))
        print ("##################")
        savedFlowsCount = savedFlowsCount + 1
        
      return render_template('pushFlow.html',savedFlowsTable=savedFlowstoClient, connectedNodeIDList=connectedNodeIDList, savedFlowsJSON=savedFlowsJSON)


@app.route('/settings')
def openSettings():
  return render_template('settings.html', controllerIPAddress = controllerIPAddress, controllerTCPPort = controllerTCPPort)

@app.route('/saveSettings',methods = ['POST', 'GET'])
def saveSettings():
  global controllerIPAddress
  global controllerTCPPort
  if request.method == 'POST':
      newSettings = request.form
      controllerIPAddress = str(newSettings["NewControllerIP"])
      controllerTCPPort = str(newSettings["NewControllerPort"])
      initProcess()
  return render_template('settings.html', controllerIPAddress = controllerIPAddress, controllerTCPPort = controllerTCPPort)

@app.route('/deleteFlow/<int:ref_number>',methods = ['POST', 'GET'])
def deleteFlow(ref_number):

  global savedFlowstoClient
  global savedFlows
  global savedFlowsJSON

  refNumber = ref_number
  if request.method == 'GET':
    for key in savedFlowstoClient:
      indeks = 0
      while (indeks < len(savedFlowstoClient[key])):
        if(savedFlowstoClient[key][indeks]['6Count'] == str(refNumber)):
          savedFlowstoClient[key].remove(savedFlowstoClient[key][indeks])
        indeks = indeks + 1
    #----------
    indeksY = 0
    while (indeksY < len(savedFlows)):
      if(savedFlows[indeksY]['Count'] == refNumber):
        savedFlows.remove(savedFlows[indeksY])
      indeksY = indeksY+1

    del savedFlowsJSON[refNumber]
  return redirect("/push")

@app.route('/nodeInfoList/<string:nodeID>')
def giveNodeInfo(nodeID):
  deviceNodeId = nodeID
  getFlowsURL = "http://"+str(controllerIPAddress)+":"+str(controllerTCPPort)+"/restconf/operational/opendaylight-inventory:nodes/node/"+deviceNodeId
  getFlowsResponse = getResponse(getFlowsURL)
  #print (json.dumps(getFlowsResponse, indent=4, sort_keys=True))

  getTableFlowsParsed = {}

  for i in getFlowsResponse["node"][0]["flow-node-inventory:table"]:
    getFlowsParsed = []
    if checkIfKeyExist('flow',i):
      for j in i["flow"]:
        getActionDescription = ''
        try:
          for k in j["instructions"]["instruction"][0]["apply-actions"]["action"]:
            if checkIfKeyExist('output-action', k):
              getActionDescription = getActionDescription + 'Output: ' + k['output-action']['output-node-connector']+', '
        except KeyError:
          getActionDescription = getActionDescription +'Drop, '

        getActionDescription = getActionDescription[:-2]


        getMatchDescription = ''
        try:
          if checkIfKeyExist('in-port',j['match']):
            getMatchDescription = getMatchDescription + 'InPort: ' + j['match']['in-port'] + ', '

          if checkIfKeyExist('ipv4-source',j['match']):
            getMatchDescription = getMatchDescription + 'IP Source: ' + j['match']['ipv4-source'] + ', '

          if checkIfKeyExist('ipv4-destination',j['match']):
            getMatchDescription = getMatchDescription + 'IP Destination: ' + j['match']['ipv4-destination'] + ', '

          if checkIfKeyExist('ethernet-match',j['match']):

            if checkIfKeyExist('ethernet-source',j['match']['ethernet-match']):
              getMatchDescription = getMatchDescription + 'Ethernet Source: ' + j['match']['ethernet-match']['ethernet-source']['address'] + ', '

            if checkIfKeyExist('ethernet-destination',j['match']['ethernet-match']):
              getMatchDescription = getMatchDescription + 'Ethernet Destination: ' + j['match']['ethernet-match']['ethernet-destination']['address'] + ', '

            if checkIfKeyExist('ethernet-type',j['match']['ethernet-match']):
              getMatchDescription = getMatchDescription + 'Ethernet Type: ' + str(j['match']['ethernet-match']['ethernet-type']['type']) + ', '

          if checkIfKeyExist('tcp-source-port',j['match']):
            getMatchDescription = getMatchDescription + 'TCP Source: ' + str(j['match']['tcp-source-port']) + ', '

          if checkIfKeyExist('tcp-destination-port', j['match']):
            getMatchDescription = getMatchDescription + 'TCP Destination: ' + str(j['match']['tcp-destination-port']) + ', '

        except KeyError:
          print('Something Wrong with the Match')

        getMatchDescription = getMatchDescription[:-2]

        getFlowsParsed.append({"1Flow ID" : j["id"],"2Priority" : j["priority"],"3Match" : getMatchDescription , "4Actions" : getActionDescription})

      getTableFlowsParsed['Table' + str(i['id']) ] = getFlowsParsed

  print (json.dumps(getTableFlowsParsed, indent=4, sort_keys=True))
  return render_template('flowInfo.html',getTableFlowsParsed = getTableFlowsParsed, deviceNodeId = deviceNodeId)

@app.route('/nodeInfoList/deleteDeviceFlow/<string:deviceNumber>/<string:tableNumber>/<string:flowNumber>',methods = ['POST', 'GET'])
def deleteDeviceFlow(deviceNumber, tableNumber, flowNumber):
  print('CobaDelete!')
  headers = {'Accept':'application/xml','Content-type':'application/xml'}
  deleteDeviceFlowURL = "http://"+str(controllerIPAddress)+":"+str(controllerTCPPort)+"/restconf/config/opendaylight-inventory:nodes/node/"+deviceNumber+"/table/"+str(tableNumber)+"/flow/"+str(flowNumber)
  response = requests.delete(deleteDeviceFlowURL, headers = headers, auth=HTTPBasicAuth('admin', 'admin'))

  print (response.status_code)
  time.sleep(3)
  return redirect(str("/nodeInfoList/"+deviceNumber))

@app.route('/about',methods = ['GET','POST'])
def aboutUs():
  return render_template('about.html')

if __name__ == "__main__":
   app.run(host='10.10.5.101',debug = True)

'''
if __name__ == '__main__':
   app.run(debug = True)
'''

