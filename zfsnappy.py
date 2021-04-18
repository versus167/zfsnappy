#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Created on 10.12.2016

@author: volker.suess

2021.27.1 - 2021-04-17 - Änderung Verhalten von keep/nodeletedays - Innerhalb der nodeletedays wird nur gelöscht,
                       wenn minspace nicht ausreicht und keep nicht unterschritten - vs.
2021.26 - 2021.01.26 - owner auf root - vs.
2020.25 - 2020-02.21 - logging umgestellt - vs.
24 - 2020-01-24 - mit deb-Paket - vs.
23 - 2018-11-02 - Fix Kompatibilität zu Python 3.5 (encoding) - vs.
22 - 2018-10-31 - fix für snaphots mit hold - vs.
21 - 2018-10-27 - neue Option -x (--no_snapshot) - damit wird kein neuer Snapshot erstellt, aber trotzdem gelöscht - vs.
20 - 2018-04-16 - Korrektur der Intervalle bei Recursion - vs.
19 - 2018-04-08 - Rekursion korrigiert - jetzt können auch Volumes behandelt werden - vs.
18 - 2017-12-03 - Diff-Berechnung geändert, damit egal wird zu welcher Uhrzeit das Script aufgerufen wird - vs.
17 - 2017-10-22 - Intervallberechnung geändert, um Probleme bei stark unregelmäßigen Aufrufen zu umgehen + log-Ausgaben angepasst - vs.
16 - 2017-10-18 - os.popen durch subprocess.run ersetzt - vs.
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
3 - 2016-12-28 - Check ob das Filesystem gemountet ist - vs.
2 - 2016-12-24 - Mit Ausgabe der Parameter für das Log - vs.
1 - 2016-12-10 - Erste lauffähige Version - vs.

Hinweis:

Bei Verwendung in der crontab ist diese PFadangabe einzufügen:

PATH=/usr/bin:/bin:/sbin


Todo:


  - Der Code ist zu säubern...
    - 
    die Meldung sind teilweise etwas verwirrend...

'''

APPNAME='zfsnappy'
VERSION='2021.27.1'
LOGNAME=APPNAME

import subprocess, shlex
import datetime, time
import argparse, sys
import logging

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
        self.intervallnraktuell = -1
        
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
        if self.intervallnraktuell == -1:
            self.intervallnraktuell = i
            self.laststrike = day
            return True
        if (self.laststrike - day)>= self.intervalllaenge:
            self.intervallnraktuell -=1
            self.laststrike = day
            return True
        else:
            return False


def main():
    def checkfs(fsys):
        ''' Soll schauen, ob das Filesystem auf com.sun:auto-snapshot=False gesetzt ist oder ob es nicht gemountet ist
        - Wenn eines von beiden zutrifft -> kein snapshot - return false '''
        ret = subprocess.run(['zfs','get','-H','type',fsys],stdout=subprocess.PIPE,universal_newlines=True)
        if ret.returncode > 0:
            return 1
        out = ret.stdout.split('\t')
        if out[2] == 'filesystem' or out[2] == 'volume':
            pass
        else: 
            log.info(f'{fsys} ist nicht geeignet für Snapshots!')
            return 1
        ret = subprocess.run(['zfs','get','-H','com.sun:auto-snapshot',fsys],stdout=subprocess.PIPE,universal_newlines=True)
        if ret.returncode > 0:
            return 2
        autosnapshot = ret.stdout.split('\t')
        if autosnapshot[2].lower() == 'false':
            log.debug(f'{fsys} com.sun:auto-snapshot = False')
            return 2
        return 0
    def checkminfree(tell=False):
        ''' Prüft den freien Space im FS '''
               
        avai = subprocess.run(['zfs','list','-Hp','-o','avail',fs],stdout=subprocess.PIPE,universal_newlines=True)
        used = subprocess.run(['zfs','list','-Hp','-o','used',fs],stdout=subprocess.PIPE,universal_newlines=True)
        refe = subprocess.run(['zfs','list','-Hp','-o','referenced',fs],stdout=subprocess.PIPE,universal_newlines=True)

        a = int(avai.stdout.strip('\n'))
        u = int(used.stdout.strip('\n'))
        r = int(refe.stdout.strip('\n'))
        perc = a/(a+u)
        if tell:
            log.info(f'free {perc*100:.3f}% {a/(1024*1024*1024):.3f} GB, used {u/(1024*1024*1024):.3f} GB, referenced {r/(1024*1024*1024):.3f} GB')
        if  perc <= ns.minfree/100:
            log.info(f'prozentual zu wenig frei - {perc*100:.3f}% < {ns.minfree}%')
            return False
        if a/(1024*1024*1024) <= ns.freespace:
            log.info(f'zu wenig GB frei - {a/(1024*1024*1024):.3f} < {ns.freespace} GB')
            return False
        return True
    def takeSnapshot():
        if ns.no_snapshot:
            return
        aktuell = datetime.datetime.now()
        snapname = fs+'@'+ns.prefix+'_'+aktuell.isoformat() 
        cmd = 'zfs snapshot '+snapname
        log.info(cmd)
        if ns.dryrun:
            pass
        else:
            aus = subprocess.run(shlex.split(cmd))
            aus.check_returncode()
    def destroySnapshot(name,chkday):
        global snapcount # Ausnahmsweise...
        if ns.dm == 3:
            # dm ==3 -> nichts wird gelöscht - im Zweifel wird halt dann kein Snapshot erstellt
            return
        if ns.nodeletedays >= chkday:
            # Wir sind also in dem Bereich, wo die Snapshots erhalten bleiben sollen
            if checkminfree(): # true = genug frei
                log.debug(f'{name} wird nicht gelöscht, da noch genug Speicher frei und wir sind in nodeletedays')
                return
                if ns.keepsnapshots >= snapcount:
                    log.debug(f'{name} wird nicht gelöscht wegen keepsnapshots {ns.keepsnapshots} >= snapcount {snapcount} innerhalb der nodeletedays {ns.nodeletedays}')
                    return
        cmd = 'zfs destroy '+name
        args = shlex.split(cmd)
        
        if ns.dryrun:
            pass
        else:
            aus = subprocess.run(args,stderr=subprocess.PIPE)
            if aus.returncode > 0:
                log.info(f'Problem beim Löschen: {aus.stderr.decode("UTF-8")}')
            else:
                log.info(cmd)
                snapcount = snapcount -1 # Jetzt ist wirklich einer weniger
                time.sleep(ns.waittime) # sleep auf 20 Sekunden (Standard), da manchmal das löschen im zfs doch länger dauert
    def getsnaplist():
        arg = shlex.split('zfs list -H -r -t snapshot -o name '+fs)
        aus = subprocess.run(arg,stdout=subprocess.PIPE,universal_newlines=True)
        aus.check_returncode()
        # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
        vgl = fs+'@'+ns.prefix+'_'
        l = len(vgl)
        listesnaps = {}
        for i in aus.stdout.split('\n'):
            snp = i
            if snp[0:l] == vgl:
                listesnaps[snp] = False
        
        return listesnaps
    
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    defaultintervall = []
    
    parser.add_argument("-i", "--holdinterval", dest="holds",
                  help="Holdintervall und Dauer - Beispiel -i 1 10 (Intervall = 1 Tag, Anzahl = 10 Intervalle)",
                  nargs=2,type=int,action='append',default=defaultintervall)
    parser.add_argument("-f","--filesystem",dest='zfsfs',
                      help='Übergabe des ZFS-Filesystems auf den die Snapshots ausgeführt werden sollen',required=True)
    parser.add_argument('-m','--minfree',dest='minfree',
                      help='Mindestens freizuhaltender Space auf dem FS in vollen Prozent',type=int, default=20)
    parser.add_argument('-s','--spacefree',dest='freespace',
                        help='Mindestens freier Speicher in GB - default ausgeschalten',type=int,default=0)
    parser.add_argument('-p','--prefix',dest='prefix',help='Der Prefix für die Bezeichnungen der Snapshots',default='zfsnappy')
    parser.add_argument('-d','--deletemode',dest='dm',type=int,help='Deletemodus 1 = mur falls minfree unterschritten, 2 - regulär laut Intervall + minfree, 3 - es wird nichts gelöscht',
                        default=1)
    parser.add_argument('-n','--nodeletedays',dest='nodeletedays',type=int,help='Anzahl Tage an dem nichts gelöscht werden soll. Es sei denn der Speicher ist zu knapp und [keep] lässt löschen zu.',
                        default=10)
    parser.add_argument('-v','--verbose',dest='verbose',action='store_true',help='Macht das Script etwas gesprächiger')
    parser.set_defaults(verbose=False)
    parser.add_argument('-r','--recursion',dest='recursion',action='store_true',help='Wendet die Einstellungen auch auf alle Filesysteme unterhalb dem übergebenen an')
    parser.set_defaults(recursion=False)
    parser.add_argument('-k','--keep',dest='keepsnapshots',type=int,help='Diese Anzahl an Snapshots wird auf jeden Fall innerhalb der NODELETEDAYS behalten',default=0)
    parser.add_argument('-x','--no_snapshot',dest='no_snapshot',action='store_true',help='Erstellt keinen neuen Snapshot - Löscht aber, wenn nötig.')
    parser.add_argument('--dry-run',dest='dryrun',action='store_true',help='Trockentest ohne Veränderung am System')
    parser.add_argument('--wait-time',dest='waittime',help='Wieviel Sekunden soll nach dem Löschen eines Snapshot gewartet werden? Wenn Löschen nach freiem Speicherplatz, dann ist es besser diesen Wert auf 20 Sekunden (Standard) oder mehr zu lassen, da ZFS asynchron löscht.',
                        type=int,default=20)
    global snapcount
    ns = parser.parse_args(sys.argv[1:])
    log = logging.getLogger(LOGNAME)
    if ns.verbose:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.StreamHandler()
    fh.setFormatter(formatter)
    log.addHandler(fh)
    log.info(f'{APPNAME} {VERSION} ************************** Start')
    log.debug(ns)
    # 0.1 Check ob das FS gemounted ist
    fslist = []
    if ns.recursion:
        # dann sammeln wir mal die Filesysteme
        arg = shlex.split('zfs list -H -r '+ns.zfsfs)
        liste = subprocess.run(arg,stdout=subprocess.PIPE,universal_newlines=True)
        liste.check_returncode()
        for i in liste.stdout.split('\n')[:-1]:
            fslist.append(i.split('\t')[0])
        
    else:
        fslist.append(ns.zfsfs)
    if ns.holds == []: # falls keine Intervalle übergeben wurden -> 1 1 als minimum
        ns.holds.append((1,1))
    for fs in fslist:
        
        log.info(f'Aktuelles Filesystem: {fs}')
       
        inters = []
        for i in ns.holds:
            inter = intervall(i[0],i[1])
            inters.append(inter)
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
        log.info(f'{fs} Snapshots vor dem Start: {snapcount}')
        vgl = fs+'@'+ns.prefix+'_'
        l = len(vgl)
        
        heute = datetime.datetime.now()
        for i in sorted(listesnaps): # Vom ältesten zum neuesten
            
            #erstmal die difftage zu heute ermitteln
            dstring = i[l:l+10] # damit wird nun noch mit dem glatten Datum verglichen - ohne Stunde/Minute
            # Damit sollte es keine Rolle mehr spielen, wann das Script an einem Tag aufgerufen wird - Die diff-Tage
            # sind immer gleich
            
            dt = datetime.datetime.strptime(dstring,'%Y-%m-%d')
            tmp = heute - dt
            chkday = tmp.days
            if ns.verbose:
                log.info(f'{i} {chkday} days')
            hold = False
#             if chkday <= ns.nodeletedays and ns.nodeletedays>0:
#                 if ns.verbose:
#                     log.info(f'Hold für {i} wegen "nodeletedays"')
#                 hold = True
#            else:
            for x in inters:
                if x.checkday(chkday):
                    log.debug(f'Hold für {i} wegen "Intervall" days: {x.intervalllaenge} Anzahl: {x.holdversions} , Intervallnummer: {x.intervallnraktuell+1}')
                    hold = True
                        
                        
            
            if hold == False:
                
                if checkminfree() == False or ns.dm == 2:
                    
                    if ns.dm == 2:
                        log.debug('delete wegen deletemode = 2')
                    else:
                        log.debug('delete wegen freespace')
                    destroySnapshot(i,chkday)
        # Als letztes: Snapshot erstellen
        if checkminfree(True): # Nur wenn genug frei ist, wird ein Snapshot erstellt
            takeSnapshot()
        else:
            # Dann müssen jetzt noch mehr snaps gelöscht werden - Vom ältesten zum neuesten
            log.info('Jetzt wird versucht auf Grund des Speicherplatzes weitere Snapshots zu löschen.')
            listesnaps = getsnaplist()
            for i in sorted(listesnaps):
                log.debug('delete wegen freespace')
                destroySnapshot(i,chkday)
                if checkminfree(True):
                    takeSnapshot()
                    break
        
        listesnaps = getsnaplist()
        snapcount = len(listesnaps)
        log.info(f'{fs} Snapshots nach Durchlauf: {snapcount}')
    log.info(f'{APPNAME} {VERSION} ************************** Stop')
if __name__ == '__main__':
    a = main()