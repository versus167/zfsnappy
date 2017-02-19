#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Created on 10.12.2016

@author: volker

Sammlung der commands:

9 - 2017-02-18 - -v --verbose hinzugefügt - macht zfsnappy etwas gesprächiger - vs.
8 - 2017-02-13 - -n --nodeletedays eingeführt - snapshots die jünger als diese Anzahl Tage sind, werden nicht gelöscht.
                 Es sei denn minfree wird unterschritten... - vs.
7 - 2017-02-09 - deletemode 3 eingeführt -> Da wird überhaupt nichts gelöscht - vs.
6 - 2017-01-30 - default für -i auf 1 1 gesetzt - vs. 
5 - 2017-01-28 - sleep(10) nach destroy eingebaut, damit zfs nachkommt + bugfix - vs.
4 - 2017-01-24 - Jetzt mit Check des freespace in GB - option -s - vs. 
3 - 2016-12-28 - Check ob das Filesystem gemoountet ist - vs.
2 - 2016-12-24 - Mit Ausgabe der Parameter für das Log - vs.
1 - 2016-12-10 - Erste lauffähige Version - vs.

Prinzipiell geht es

Todo:


  - Der Code ist zu säubern...
  - Rekursion könnte noch verbaut werden
  

'''
APPNAME='zfsnappy'
VERSION='9 - 2017-02-18'

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
    def checkfs(fs):
        ''' Soll schauen, ob das Filesystem auf com.sun:auto-snapshot=off gesetzt ist oder ob es nicht gemountet ist
        - Wenn eines von beiden zutrifft -> kein snapshot - return false '''
        mounted = os.popen('zfs get -H mounted '+fs).readlines()
        try:
            if mounted[0].split('\t')[2] == 'yes':
                # dann alles io
                pass
            else:
                if ns.verbose: 
                    print(fs,'ist nicht gemounted!')
                return 1
        except:
            if ns.verbose:
                print(fs,'ist nicht gemounted!')
            return 1
        autosnapshot = os.popen('zfs get -H com.sun:auto-snapshot '+fs).readlines()
        if autosnapshot[0].split('\t')[2] == 'off':
            if ns.verbose:
                print(fs,'com.sun:auto-snapshot = off')
            return 2
        return True
    def checkminfree(tell=False):
        
        
        ''' Erstmal 10 Sekunden warten, damit sich ZFS besinnen kann, wieviel Platz wirklich frei ist -
        falls gerade vorher ein Snapshot gelöscht wurde ''' 
        avai = os.popen('zfs list -Hp -o avail '+ns.zfsfs).readlines()
        used = os.popen('zfs list -Hp -o used '+ns.zfsfs).readlines()
        #print(avai,used)
        a = int(avai[0].strip('\n'))
        u = int(used[0].strip('\n'))
        perc = a/(a+u)
        if tell:
            print('free %.2f%% %.2fGB' % (perc*100,a/(1024*1024*1024)))
        if  perc <= ns.minfree/100:
            print('prozemtual zu wenig frei - %.2ff < ' % (perc*100,),ns.minfree,'%')
            return False
        if a/(1024*1024*1024) <= ns.freespace:
            print('zu wenig GB frei - %.2f < ' % (a/(1024*1024*1024),),ns.freespace,'GB')
            return False
        return True
    def takeSnapshot():
        aktuell = datetime.datetime.now()
        snapname = ns.zfsfs+'@'+ns.prefix+'_'+aktuell.isoformat() 
        cmd = 'zfs snapshot '+snapname
        print(cmd)
        aus = os.popen(cmd)
        for j in aus:
            print(j)
    def destroySnapshot(name):
        if ns.dm == 3:
            # dm ==3 -> nichts wird gelöscht - im Zweifel wird halt dann kein Snapshot erstellt
            return
        cmd = 'zfs destroy '+name
        print(cmd)
        aus = os.popen(cmd)
        for j in aus:
            print(j)
        time.sleep(10) 
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
#         for i in sorted(listesnaps):
#             print(i)
        
        return listesnaps
    print(time.strftime("%Y-%m-%d %H:%M:%S"),APPNAME, VERSION,' ************************** Start')
    print('Aufrufparameter:',' '.join(sys.argv[1:]))
    parser = argparse.ArgumentParser()
    defaultintervall = []
    defaultintervall.append((1,1))
    parser.add_argument("-i", "--holdinterval", dest="holds",
                  help="Holdintervall und Dauer - Beispiel -i 1 10 (Intervall = 1 Tag, Anzahl = 10 Intervalle)",
                  nargs=2,type=int,action='append',default=defaultintervall)
    parser.add_argument("-f","--filesystem",dest='zfsfs',
                      help='Übergabe des ZFS-Filesystems auf den die Snapshots ausgeführt werden sollen',required=True)
    parser.add_argument('-m','--minfree',dest='minfree',
                      help='Mindestens freizuhaltender Space auf dem FS in vollen Prozent - default 20%',type=int, default=20)
    parser.add_argument('-s','--spacefree',dest='freespace',
                        help='Mindestens freier Speicher in GB - default ausgeschalten',type=int,default=0)
    parser.add_argument('-p','--prefix',dest='prefix',help='Der Prefix für die Bezeichnungen der Snapshots',default='zfsnappy')
    parser.add_argument('-d','--deletemode',dest='dm',type=int,help='Deletemodus 1 = mur falls minfree unterschritten, 2 - regulär laut Intervall + minfree, 3- es wird nichts gelöscht',
                        default=1)
    parser.add_argument('-n','--nodeletedays',dest='nodeletedays',type=int,help='Anzahl Tage an denen regulär nichts gelöscht wird - nach freizuhaltendem Space wird trotzdem gelöscht',
                        default=0)
    parser.add_argument('-v','--verbose',dest='verbose',action='store_true',help='Macht das Script etwas gesprächiger',default=False)
    parser.set_defaults(verbose=False)
    ns = parser.parse_args(sys.argv[1:])
    
    inters = []
    for i in ns.holds:
        inter = intervall(i[0],i[1])
        inters.append(inter)
    # 0.1 Cheock ob das FS gemounted ist
    ret =  checkfs(ns.zfsfs)
    if ret != True:
        return ret
    
    # Hier käme dann der Ablauf
    if ns.dm == 3:
        # Dann wird nur gecheckt ob genug Platz ist für einen neuen Snapshot
        if checkminfree(True): # Nur wenn genug frei ist, wird ein Snapshot erstellt
            takeSnapshot()
        return
    # 1. Liste der vorhanden Snapshots
    listesnaps = getsnaplist()
    vgl = ns.zfsfs+'@'+ns.prefix+'_'
    l = len(vgl)
    
    heute = datetime.datetime.now()
    for i in sorted(listesnaps): # Vom ältesten zum neuesten
        
        #erstmal die difftage zu heute ermitteln
        dstring = i[l:]
        
        dt = datetime.datetime.strptime(dstring,'%Y-%m-%dT%H:%M:%S.%f')
        tmp = heute - dt
        chkday = tmp.days 
        if ns.verbose:
            print(i, chkday,'days')
        hold = False
        if chkday <= ns.nodeletedays and ns.nodeletedays>0:
            if ns.verbose:
                print('Hold für ',i,'wegen "nodeletedays"')
            #print(i,'in days',chkday)
            hold = True
        else:
            for x in inters:
                if x.checkday(chkday):
                    if ns.verbose:
                        print('Hold für ',i,' wegen "interval" days:',x.intervalllaenge,'Anzahl:',x.holdversions )
                    hold = True
                    
                    
        
        if hold == False:
            
            if checkminfree() == False or ns.dm == 2:
                if ns.verbose:
                    if ns.dm == 2:
                        print('delete wegen deletemode = 2')
                    else:
                        print('delete wegen freespace')
                destroySnapshot(i)
    # Als letztes: Snapshot erstellen
    if checkminfree(True): # Nur wenn genug frei ist, wird ein Snapshot erstellt
        takeSnapshot()
    else:
        # Dann müssen jetzt noch mehr snaps gelöscht werden - Vom ältesten zum neuesten
        print('Jetzt wird versucht auf Grund des Speicherplatzes weitere Snapshots zu löschen.')
        listesnaps = getsnaplist()
        for i in sorted(listesnaps):
            if ns.verbose:
                print('delete wegen freespace')
            destroySnapshot(i)
            if checkminfree(True):
                takeSnapshot()
                break
    
    print(time.strftime("%Y-%m-%d %H:%M:%S"),APPNAME, VERSION,' ************************** Stop')
if __name__ == '__main__':
    a = main()