#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Created on 10.12.2016

@author: volker.suess

15 - 2017-10-08 - sleep nach destroy erhöht auf 20 Sekunden, damit ZFS mehr Zeit hat zu löschen - vs.
14 - 2017-07-28 - bei checkminfree wird jetzt auch der used-und referenced space in GB mit ausgegeben - vs.
13 - 2017-07-06 - Anzahl Snaps werden dargestellt falls nicht deletemode = 3 - vs.
12 - 2017-05-30 - --dry-run - Trockentest ohne löschen und snapshot - vs.
11 - 2017-05-11 - -k --keep Anzahl Snapshots auf keinen Fall löschen - minfree spielt dabei keine Rolle 
10 - 2017-02-19 - -r --recursion hinzugefügt - fs die nicht gemounted sind oder die Eigenschaft sun.com:auto-snapshot=False haben
                werden nicht behandelt
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



Todo:


  - Der Code ist zu säubern...

  

'''
APPNAME='zfsnappy'
VERSION='15 - 2017-10-08'

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
        self.intervallnraktuell = 0
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
        self.intervallnraktuell = i
        return True
    

def main():
    def checkfs(fsys):
        ''' Soll schauen, ob das Filesystem auf com.sun:auto-snapshot=False gesetzt ist oder ob es nicht gemountet ist
        - Wenn eines von beiden zutrifft -> kein snapshot - return false '''
        mounted = os.popen('zfs get -H mounted '+fsys).readlines()
        try:
            if mounted[0].split('\t')[2] == 'yes':
                # dann alles io
                pass
            else:
                if ns.verbose: 
                    print(fsys,'ist nicht gemounted!')
                return 1
        except:
            if ns.verbose:
                print(fsys,'ist nicht gemounted!')
            return 1
        autosnapshot = os.popen('zfs get -H com.sun:auto-snapshot '+fsys).readlines()
        if autosnapshot[0].split('\t')[2].lower() == 'false':
            if ns.verbose:
                print(fsys,'com.sun:auto-snapshot = False')
            return 2
        return 0
    def checkminfree(tell=False):
        ''' Prüft den freien Space im FS '''
               
        avai = os.popen('zfs list -Hp -o avail '+fs).readlines()
        used = os.popen('zfs list -Hp -o used '+fs).readlines()
        refe = os.popen('zfs list -Hp -o referenced '+fs).readlines()
        #print(avai,used)
        a = int(avai[0].strip('\n'))
        u = int(used[0].strip('\n'))
        r = int(refe[0].strip('\n'))
        perc = a/(a+u)
        if tell:
            print('free %.3f%% %.3f GB, used %.3f GB, referenced %.3f GB' % (perc*100,a/(1024*1024*1024),u/(1024*1024*1024),r/(1024*1024*1024)))
        if  perc <= ns.minfree/100:
            print('prozentual zu wenig frei - %.3f%% < ' % (perc*100,),ns.minfree,'%')
            return False
        if a/(1024*1024*1024) <= ns.freespace:
            print('zu wenig GB frei - %.3f < ' % (a/(1024*1024*1024),),ns.freespace,'GB')
            return False
        return True
    def takeSnapshot():
        aktuell = datetime.datetime.now()
        snapname = fs+'@'+ns.prefix+'_'+aktuell.isoformat() 
        cmd = 'zfs snapshot '+snapname
        print(cmd)
        if ns.dryrun:
            pass
        else:
            aus = os.popen(cmd)
            for j in aus:
                print(j)
    def destroySnapshot(name):
        global snapcount # Ausnahmsweise...
        if ns.dm == 3:
            # dm ==3 -> nichts wird gelöscht - im Zweifel wird halt dann kein Snapshot erstellt
            return
        if ns.keepsnapshots >= snapcount:
            if ns.verbose:
                print(name,'wird nicht gelöscht wegen keepsnapshots',ns.keepsnapshots,'>= snapcount',snapcount)
            return
        cmd = 'zfs destroy '+name
        print(cmd)
        snapcount = snapcount -1 # Jetzt ist wirklich einer weniger
        if ns.dryrun:
            pass
        else:
            aus = os.popen(cmd)
            for j in aus:
                print(j)
        time.sleep(20) # sleep auf 20 Sekunden, da manchmal das löschen im zfs doch länger dauert
    def getsnaplist():
        aus = os.popen('zfs list -H -r -t snapshot -o name '+fs).readlines()
        # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
        vgl = fs+'@'+ns.prefix+'_'
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
    parser.add_argument('-v','--verbose',dest='verbose',action='store_true',help='Macht das Script etwas gesprächiger')
    parser.set_defaults(verbose=False)
    parser.add_argument('-r','--recursion',dest='recursion',action='store_true',help='Wendet die Einstellungen auch auf alle Filesysteme unterhalb dem übergebenen an')
    parser.set_defaults(recursion=False)
    parser.add_argument('-k','--keep',dest='keepsnapshots',type=int,help='Diese Anzahl an Snapshots wird auf jeden Fall behalten',default=0)
    parser.add_argument('--dry-run',dest='dryrun',action='store_true',help='Trockentest ohne Veränderung am System')
    global snapcount
    ns = parser.parse_args(sys.argv[1:])
    if ns.holds == []:
        ns.holds.append((1,1))
    inters = []
    for i in ns.holds:
        inter = intervall(i[0],i[1])
        inters.append(inter)
    # 0.1 Cheock ob das FS gemounted ist
    fslist = []
    if ns.recursion:
        # dann sammeln wir mal die Filesysteme
        liste = os.popen('zfs list -H -r '+ns.zfsfs).readlines()
        for i in liste:
            fslist.append(i.split('\t')[0])
        
    else:
        fslist.append(ns.zfsfs)
    
    for fs in fslist:
        print('Aktuelles Filesystem:',fs)
        ret =  checkfs(fs)
        if ret != 0:
            continue
        
        # Hier käme dann der Ablauf
        if ns.dm == 3:
            # Dann wird nur gecheckt ob genug Platz ist für einen neuen Snapshot
            if checkminfree(True): # Nur wenn genug frei ist, wird ein Snapshot erstellt
                takeSnapshot()
            continue
        # 1. Liste der vorhanden Snapshots
        listesnaps = getsnaplist()
        snapcount = len(listesnaps)
        print(fs,'Snapshots vor dem Start:',snapcount)
        vgl = fs+'@'+ns.prefix+'_'
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
                            print('Hold für ',i,' wegen "Intervall" days:',x.intervalllaenge,'Anzahl:',x.holdversions ,'Intervallnummer:',x.intervallnraktuell+1)
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
        
        listesnaps = getsnaplist()
        snapcount = len(listesnaps)
        print(fs,'Snapshots nach Durchlauf:',snapcount)
    print(time.strftime("%Y-%m-%d %H:%M:%S"),APPNAME, VERSION,' ************************** Stop')
if __name__ == '__main__':
    a = main()