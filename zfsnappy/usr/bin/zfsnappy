#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Created on 10.12.2016

@author: volker.suess

2021.28.1 - 2021-04-21 - Soll die Snapshots auf "keep" selbst erkennen und nicht löschen + rewritw - vs.
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

Bei Verwendung in der crontab ist diese Pfadangabe einzufügen:

PATH=/usr/bin:/bin:/sbin


'''

APPNAME='zfsnappy'
VERSION='2021.28.1'
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

class zfsnappy(object):
    '''
    Der Einstieg
    '''
    def __init__(self,):
        
        self.paramters()
        self.log.debug(self.ns)
        self.log.info(f'{APPNAME} {VERSION} ************************** Start')
        if self.collectdatasets() == False:
            self.log.info('Kein korrektes Filesystem übergeben!')
            return
        self.log.debug(self.fslist)
        for fsys in self.fslist:
            zfsdataset(fsys,self.ns)
        self.log.info(f'{APPNAME} {VERSION} ************************** Ende')
    def paramters(self):
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
        self.ns = parser.parse_args(sys.argv[1:])
        if self.ns.holds == []: # falls keine Intervalle übergeben wurden -> 1 1 als minimum
            self.ns.holds.append((1,1))
        self.log = logging.getLogger(LOGNAME)
        if self.ns.verbose:
            self.log.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh = logging.StreamHandler()
        fh.setFormatter(formatter)
        self.log.addHandler(fh)
        
    def collectdatasets(self):
        '''
        Schaut mal was für Filesysteme zu behandeln sind
        '''
        self.fslist = []
        if self.ns.recursion:
            # dann sammeln wir mal die Filesysteme
            arg = shlex.split('zfs list -H -r '+self.ns.zfsfs)
            liste = subprocess.run(arg,stdout=subprocess.PIPE,universal_newlines=True)
            liste.check_returncode()
            for i in liste.stdout.split('\n')[:-1]:
                temp_fs = i.split('\t')[0]
                if self.checkfs(temp_fs):
                    self.fslist.append(temp_fs)
        
        else:
            if self.checkfs(self.ns.zfsfs):
                self.fslist.append(self.ns.zfsfs)
        if len(self.fslist) > 0:
            return True
        else:
            return False
    
    def checkfs(self,fsys):
        ''' Soll schauen, ob das Filesystem auf com.sun:auto-snapshot=False gesetzt ist oder ob es nicht gemountet ist
        - Wenn eines von beiden zutrifft -> kein snapshot - return false '''
        ret = subprocess.run(['zfs','get','-H','type',fsys],stdout=subprocess.PIPE,universal_newlines=True)
        if ret.returncode > 0:
            return False
        out = ret.stdout.split('\t')
        if out[2] == 'filesystem' or out[2] == 'volume':
            pass
        else: 
            self.log.info(f'{fsys} ist nicht geeignet für Snapshots!')
            return False
        ret = subprocess.run(['zfs','get','-H','com.sun:auto-snapshot',fsys],stdout=subprocess.PIPE,universal_newlines=True)
        if ret.returncode > 0:
            return False
        autosnapshot = ret.stdout.split('\t')
        if autosnapshot[2].lower() == 'false':
            self.log.debug(f'{fsys} com.sun:auto-snapshot = False')
            return False
        return True

class zfsdataset(object):
    '''
    Soll das einzelne Dataset entsprechend der Parameter behandeln
    '''
    def __init__(self,fsys,argumente):
        '''
        Führt die Operationen am übergeben Filesystem aus
        '''
        

        self.log = logging.getLogger(LOGNAME)
        self.fsys = fsys
        self.ns = argumente
        if self.ns.dm == 3:
            self.snapcount = 0
            # Hier wird nur gecheckt, ob genug Platz ist und der Snapshot gesetzt
            if self.checkminfree(True):
                self.takesnapshot()
            else:
                self.log.info(f'{self.fsys}: Kein Snapshot erstellt, da nicht genügend Platz auf dem Dataset.')
            return
        self.snaplist = self.getsnaplist()
        self.log.debug(self.snaplist)
        self.log.info(f'{self.fsys}: {self.snapcount} Snapshots vor dem Start.')
        self.checkminfree(True)
        self.cleanup_snapshots()
        self.takesnapshot()
        self.log.info(f'{self.fsys}: {self.snapcount} Snapshots nach Ablauf.')
        self.checkminfree(True)
        pass
    
    
    def cleanup_snapshots(self):
        ''' Geht durch die Snaps und checkt die Löschbedingung '''
        inters = []
        
        for i in self.ns.holds:
            inter = intervall(i[0],i[1])
            inters.append(inter)
        count = 0
        for snap in self.snaplist:
            count += 1
            if self.ns.dm == 1 and self.checkminfree():
                # Abbruchbedingung - nichts wird mehr gelöscht
                self.log.debug(f'{self.fsys}: Abbruch cleanup wegen genug Platz und dm = 1')
                return
            chkday = self.diffdays(snap)
            self.log.debug(f'{i} {chkday} days')
            if self.ns.nodeletedays >= chkday:
                # Innerhalb dieser Tage darf regulär nichts gelöscht werden
                break
            hold = False
            for x in inters:
                if x.checkday(chkday):
                    self.log.debug(f'Hold für {i} wegen "Intervall" days: {x.intervalllaenge} Anzahl: {x.holdversions} , Intervallnummer: {x.intervallnraktuell+1}')
                    hold = True
            if hold == False:
                self.destroysnapshot(snap)
        if self.checkminfree():
            self.log.debug(f'{self.fsys}: Abbruch cleanup, da genug Platz')
            return
        # Also noch nicht genug Platz -> Löschen vom ältesten Snapshot Abbruchbedingung
        self.snaplist = self.getsnaplist()
        self.log.info(f'{self.fsys}: Jetzt wird versucht auf Grund des Speicherplatzes weitere Snapshots zu löschen.')
        count = 0
        for snap in self.snaplist:
            count += 1
            if self.checkminfree() or self.keepindays(snap,self.snapcount-count):
                self.log.debug(f'{self.fsys}: Abbruch cleanup in der Zusatzrunde')
                return
            self.destroysnapshot(snap)
        self.log.debug(f'{self.fsys}: Ende Cleanup, mehr können wir nicht löschen...')    
    def keepindays(self,snap,snapnumber):
        ''' Checkt ob eine Löschsperre für diesen Snapshot besteht 
        
        true wenn snap behalten werden soll
        '''
        days = self.diffdays(snap)
        if days <= self.ns.nodeletedays:
            if snapnumber <= self.ns.keepsnapshots:
                return True
        return False
    
    def diffdays(self,snap):
        #erstmal die difftage zu heute ermitteln
        heute = datetime.datetime.now()
        vgl = self.fsys+'@'+self.ns.prefix+'_'
        l = len(vgl)
        dstring = snap[l:l+10] # damit wird nun noch mit dem glatten Datum verglichen - ohne Stunde/Minute
        # Damit sollte es keine Rolle mehr spielen, wann das Script an einem Tag aufgerufen wird - Die diff-Tage
        # sind immer gleich
        
        dt = datetime.datetime.strptime(dstring,'%Y-%m-%d')
        tmp = heute - dt
        days = tmp.days
        return days
    
    def checkminfree(self,tell=False):
        ''' Prüft den freien Space im FS 
        
        true fals ja'''
               
        avai = subprocess.run(['zfs','list','-Hp','-o','avail',self.fsys],stdout=subprocess.PIPE,universal_newlines=True)
        used = subprocess.run(['zfs','list','-Hp','-o','used',self.fsys],stdout=subprocess.PIPE,universal_newlines=True)
        refe = subprocess.run(['zfs','list','-Hp','-o','referenced',self.fsys],stdout=subprocess.PIPE,universal_newlines=True)

        a = int(avai.stdout.strip('\n'))
        u = int(used.stdout.strip('\n'))
        r = int(refe.stdout.strip('\n'))
        perc = a/(a+u)
        if tell:
            self.log.info(f'{self.fsys}: free {perc*100:.3f}% {a/(1024*1024*1024):.3f} GB, used {u/(1024*1024*1024):.3f} GB, referenced {r/(1024*1024*1024):.3f} GB')
        if  perc <= self.ns.minfree/100:
            if tell:
                self.log.info(f'{self.fsys}: prozentual zu wenig frei - {perc*100:.3f}% < {self.ns.minfree}%')
            return False
        if a/(1024*1024*1024) <= self.ns.freespace:
            if tell:
                self.log.info(f'{self.fsys}: zu wenig GB frei - {a/(1024*1024*1024):.3f} < {self.ns.freespace} GB')
            return False
        return True

    
    def destroysnapshot(self,snap):
        cmd = 'zfs destroy '+snap
        args = shlex.split(cmd)
        
        if self.ns.dryrun:
            pass
        else:
            aus = subprocess.run(args,stderr=subprocess.PIPE)
            if aus.returncode > 0:
                self.log.info(f'Problem beim Löschen: {aus.stderr.decode("UTF-8")}')
            else:
                self.log.info(cmd)
                self.snapcount = self.snapcount -1 # Jetzt ist wirklich einer weniger
                time.sleep(self.ns.waittime)
        pass
    
    def check_keep(self,snapshot):
        # Checkt ob auf dem Snapshot ein keep sitzt - true falls ja
        ret = subprocess.run(['zfs','holds','-H',snapshot],stdout=subprocess.PIPE,universal_newlines=True)
        if ret.returncode > 0:
            return False
        keep = ret.stdout.split('\t')
        try:
            if keep[1].lower() == 'keep':
                self.log.debug(f'{snapshot} steht auf keep')
                return True
        except:
            return False
        return False
    
    def getsnaplist(self):
        arg = shlex.split('zfs list -H -r -t snapshot -o name '+self.fsys)
        aus = subprocess.run(arg,stdout=subprocess.PIPE,universal_newlines=True)
        aus.check_returncode()
        # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
        vgl = self.fsys+'@'+self.ns.prefix+'_'
        l = len(vgl)
        listesnaps = []
        for snp in aus.stdout.split('\n'):
            
            if snp[0:l] == vgl:
                if self.check_keep(snp): # Schmeisst die auf Keep auch raus
                    continue
                else:
                    listesnaps.append(snp)
        self.snapcount = len(listesnaps)
        return sorted(listesnaps)
        
    
    def takesnapshot(self):
        if self.ns.no_snapshot:
            self.log.debug(f'{self.fsys}: Kein Snapshot wegen -x')
            return
        
        if self.checkminfree():
            self.log.info(f'{self.fsys}: Take Snapshot')
            aktuell = datetime.datetime.now()
            snapname = self.fsys+'@'+self.ns.prefix+'_'+aktuell.isoformat() 
            cmd = 'zfs snapshot '+snapname
            self.log.info(cmd)
            if self.ns.dryrun:
                pass
            else:
                aus = subprocess.run(shlex.split(cmd))
                aus.check_returncode()
                self.snapcount += 1
        
if __name__ == '__main__':
    a = zfsnappy()