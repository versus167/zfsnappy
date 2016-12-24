#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Created on 10.12.2016

@author: volker

Sammlung der commands:

2 - 2016-12-24 - Mit Ausgabe der Paramater für das Log - vs.
1 - 2016-12-10 - Erste lauffähige Version - vs.

Prinzipiell geht es

Todo:


  - Der Code ist zu säubern...
  - Rekursion könnte noch verbaut werden
  - man könnte noch minfree nach absoluter Größe abprüfen


'''
APPNAME='zfsnappy'
VERSION='2 - 2016-12-24'

import os
import datetime, time
import argparse, sys

class intervall(object):
    '''
    Zum Check ob ein Snapshot nach diesem Intervall gelöscht werden müsste 
    '''
    def __init__(self,intervalllaenge=1, holdversions=1):
        '''
        Länger der Intervalle in Tagen
        '''
        self.intervalllaenge = int(intervalllaenge)
        self.holdversions = holdversions
        self.intervalls = {}
    def checkday(self,day):
        '''
        Hier soll ein Tag übergeben werden.
        
        Dafür wird der Intervall ermittelt. Und wenn wir dort noch nichts haben gibt es ein True (behalten) zurück.
        Sonst false.
        Auch wenn außerhalb der holdversions
        '''
    
        i = int(int(day)/int(self.intervalllaenge))
        if i >= self.holdversions:
            return False
        try:
            if self.intervalls[i] == True:
                return False
        except:
            self.intervalls[i] = True
        return True
    

def main():
    def checkminfree(tell=False):
        avai = os.popen('zfs list -Hp -o avail '+ns.zfsfs).readlines()
        used = os.popen('zfs list -Hp -o used '+ns.zfsfs).readlines()
        #print(avai,used)
        a = int(avai[0].strip('\n'))
        u = int(used[0].strip('\n'))
        perc = a/(a+u)
        if tell:
            print('free %.2f%%' % (perc*100))
        if  perc <= ns.minfree/100:
            
            return False
        else:
            return True
    def getsnaplist():
        aus = os.popen('zfs list -H -r -t snapshot -o name '+ns.zfsfs).readlines()
        # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
        vgl = ns.zfsfs+'@'+ns.prefix+'_'
        l = len(vgl)
        listesnaps = {}
        for i in aus:
            snp = i.strip('\n')
            if snp[0:l] == vgl:
                listesnaps[snp] = False
        #print(listesnaps)
        return listesnaps
    print(time.strftime("%Y-%m-%d %H:%M:%S"),APPNAME, VERSION,'Start')
    print('Aufrufparameter:',sys.argv[1:])
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--holdinterval", dest="holds",
                  help="Holdintervall und Dauer - Beispiel -i 1 10 (Intervall = 1 Tag, Anzahl = 10 Intervalle)",
                  nargs=2,type=int,action='append',required=True)
    parser.add_argument("-f","--filesystem",dest='zfsfs',
                      help='Übergabe des ZFS-Filesystems auf den die Snapshots ausgeführt werden sollen',required=True)
    parser.add_argument('-m','--minfree',dest='minfree',
                      help='Mindestens freizuhaltender Space auf dem FS in vollen Prozent',type=int, default=20)
    parser.add_argument('-p','--prefix',dest='prefix',help='Der Prefix für die Bezeichnungen der Snapshots',default='zfsnappy')
    parser.add_argument('-d','--deletemode',dest='dm',type=int,help='Deletemodus 1 = mur falls minfree unterschritten, 2 - regulär laut Intervall + minfree',
                        default=1)
    ns = parser.parse_args(sys.argv[1:])
#     zfsfs = 'vs2016/archiv/test'
#     snapprefix = 'vs'
#     minfree = 20 # in Prozent
    inters = []
    for i in ns.holds:
        inter = intervall(i[0],i[1])
        inters.append(inter)
    
    
    # Hier käme dann der ABlauf
    # 1. Liste der vorhanden Snapshots
    listesnaps = getsnaplist()
    vgl = ns.zfsfs+'@'+ns.prefix+'_'
    l = len(vgl)
    #print(listesnaps)
    heute = datetime.datetime.now()
    for i in sorted(listesnaps): # Vom ältesten zum neuesten
        #print(i,listesnaps[i])
        #erstmal die difftage zu heute ermitteln
        dstring = i[l:]
        #print(dstring)
        dt = datetime.datetime.strptime(dstring,'%Y-%m-%dT%H:%M:%S.%f')
        tmp = heute - dt
        chkday = tmp.days 
        hold = False
        for x in inters:
            if x.checkday(chkday):
                hold = True
        
        if hold == False:
            #print(i,chkday,' zu löschen')
            if checkminfree() == False or ns.dm == 2:
                cmd = 'zfs destroy '+i
                print(cmd)
                aus = os.popen(cmd)
                for j in aus:
                    print(j)
#         else:
#             print(i,chkday,hold)
    # Als letztes: Snapshot erstellen
    if checkminfree(True): # Nur wenn genug frei ist, wird ein Snapshot erstellt
        aktuell = datetime.datetime.now()
        snapname = ns.zfsfs+'@'+ns.prefix+'_'+aktuell.isoformat() 
        cmd = 'zfs snapshot '+snapname
        print(cmd)
        aus = os.popen(cmd)
        for j in aus:
            print(j)
    else:
        # Dann müssen jetzt noch mehr snaps gelöscht werden - Vom ältesten zum neuesten
        listesnaps = getsnaplist()
        for i in sorted(listesnaps):
            cmd = 'zfs destroy '+i
            print(cmd)
            aus = os.popen(cmd)
            for j in aus:
                print(j)
            if checkminfree(True):
                break
    print(time.strftime("%Y-%m-%d %H:%M:%S"),APPNAME, VERSION,'Stop')
if __name__ == '__main__':
    a = main()