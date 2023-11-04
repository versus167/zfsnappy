#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
Created on 10.12.2016

@author: volker.suess

2023.36.37.b1 - 2023-10-31 - Variante um die Snapshots mit Proxmox-Bordmitteln zu erstellen - vs.
2023.36 - 2023-10-08 - alternative Recursion -R [zfs|zfsnappy] eingeführt -> zfs ist Rekursion im ZFS-Style - vs.
2023.35.3 - 2023-08-08 - Kompatibilität mit zfs < 2.0 wieder hergestellt - vs.
2023.35 - 2023-08-06 - nun wird die zpool wait-Funktion (ab zfs 2) verwendet - option wait ist raus - vs.
2022.34 - 2022-01-24 - --without-root - Nur subsysteme werden behandelt - vs.
2021.33 - 2021-09-04 - kleine Änderung in der log-Ausgabe bei keepingdays - vs.
2021.32 - 2021-08-11 - Hold-Snaps werden jetzt unabhängig vom Tag erkannt - vs.
2021.31 - 2021-08-05 - ab jetzt wird UTC für die Benennung der Snapshots verwendet - vs.
2021.30 - 2021-06-13 - abfangen Fehler, wenn Snapshot nicht erstellt werden kann - vs. 
2021.29 - 2021-04-24 - Messages und Fix keepindays - vs.
2021.28.2 - 2021-04-22 - Fix 
2021.28.1 - 2021-04-21 - Soll die Snapshots auf "keep" selbst erkennen und nicht löschen + rewrite - vs.
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
VERSION='2023.36.37.b1 2023-10-31'
LOGNAME=APPNAME

import subprocess, shlex
import datetime, time
import argparse, sys
import logging

def get_zfs_main_version():
    # Get the output of the `zfs version` command
    output = subprocess.check_output(["zfs", "version"])
    
    # Parse the output and get the ZFS version
    temp = output.decode("utf-8").split('.')[0]
    mainversion = temp.split('-')[1]
    return int(mainversion)

def subrun(command,checkretcode=True,**kwargs):
    '''
    Führt die übergebene Kommandozeile aus und gibt das Ergebnis
    zurück
    '''
    log = logging.getLogger(LOGNAME)
    args = shlex.split(command)
    log.debug(' '.join(args))
    ret = subprocess.run(args,**kwargs)
    if checkretcode: ret.check_returncode()
    return ret

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
        
        self.parameters()
        self.log.debug(self.ns)
        self.log.info(f'{APPNAME} {VERSION} ************************** Start')
        
        if self.ns.proxmox == True:
            self.base = proxmox_base(self.ns)
        else:
            self.base = zfs_base(self.ns)
        for filesys in self.base.get_systems():
            filesys.ablauf()
            pass
        
        self.log.info(f'{APPNAME} {VERSION} ************************** Ende')
    def parameters(self):
        parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        defaultintervall = []
        parser.add_argument("--proxmox",dest="proxmox",help="Proxmox-Mode - erstellt snapshots von VMs und Containern",action="store_true",default=False)
        parser.add_argument("-i", "--holdinterval", dest="holds",
                      help="Holdintervall und Dauer - Beispiel -i 1 10 (Intervall = 1 Tag, Anzahl = 10 Intervalle)",
                      nargs=2,type=int,action='append',default=defaultintervall)
        parser.add_argument("-f","--filesystem",dest='zfsfs',
                          help='Übergabe des ZFS-Filesystems auf den die Snapshots ausgeführt werden sollen')
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
        parser.add_argument('-r','--recursion',dest='recursion',action='store_true',required='--without-root' in sys.argv,
                            help='Wendet die Einstellungen auch auf alle Filesysteme unterhalb dem übergebenen an - wenn -R angegeben dann wird -r ignoriert')
        parser.add_argument('-R','--Recursive',dest='recursion_new',choices=['zfsnappy','zfs'],
                            help='bei "zfsnappy" Einstellungen werden auch auf alle Dateisysteme unterhalb des übergeben angewendet. Bei "zfs" wird die Funktionalität von zfs dafür verwendet')
        
        parser.add_argument('-k','--keep',dest='keepsnapshots',type=int,help='Diese Anzahl an Snapshots wird auf jeden Fall innerhalb der NODELETEDAYS behalten',default=0)
        parser.add_argument('-x','--no_snapshot',dest='no_snapshot',action='store_true',help='Erstellt keinen neuen Snapshot - Löscht aber, wenn nötig.')
        parser.add_argument('--dryrun',dest='dryrun',action='store_true',help='Trockentest ohne Veränderung am System')
        parser.add_argument('--without-root',dest='withoutroot',
                            help="zfsnappy wird nicht auf den root des übergebenen Filesystems angewendet",action="store_true")
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
        

    
    

class zfs_dataset(object):
    '''
    Soll das einzelne Dataset entsprechend der Parameter behandeln
    '''
    def __init__(self,fsys,argumente):
        '''
        Führt die Operationen am übergeben Filesystem aus
        '''
        self.log = logging.getLogger(LOGNAME)
        self.ns = argumente        
        self.fsys = fsys
        self.get_rootfs(fsys)
        
    def ablauf(self):
        ''' Hier kommt der einheitliche Ablauf rein '''
        
        if self.ns.dm == 3:
            self.snapcount = 0
            # Hier wird nur gecheckt, ob genug Platz ist und der Snapshot gesetzt
            if self.checkminfree(True):
                self.takesnapshot()
            else:
                self.log.info(f'{self.fsys}: Kein Snapshot erstellt, da nicht genügend Platz auf dem Dataset.')
            return
        self.get_snaplist()
        self.log.debug(self.snaplist)
        self.log.info(f'{self.fsys}: {self.snapcount} Snapshots vor dem Start.')
        self.checkminfree(True)
        self.cleanup_snapshots()
        self.takesnapshot()
        self.log.info(f'{self.fsys}: {self.snapcount} Snapshots nach Ablauf.')
        self.checkminfree(True)
    
    def snapname(self):
        aktuell = datetime.datetime.utcnow()
        snapname = self.ns.prefix+'_'+aktuell.isoformat() 
        snapname = snapname.replace(":",'-').replace('.','-')
        return snapname
    
    def cleanup_snapshots(self):
        ''' Geht durch die Snaps und checkt die Löschbedingung '''
        inters = []
        
        for i in self.ns.holds:
            inter = intervall(i[0],i[1])
            inters.append(inter)
        count = -1
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
                if self.destroysnapshot(snap):
                    count -= 1
                    
        if self.checkminfree():
            self.log.debug(f'{self.fsys}: Abbruch cleanup, da genug Platz')
            return
        # Also noch nicht genug Platz -> Löschen vom ältesten Snapshot Abbruchbedingung
        self.get_snaplist()
        self.log.info(f'{self.fsys}: Jetzt wird versucht auf Grund des Speicherplatzes weitere Snapshots zu löschen.')
        count = -1
        for snap in self.snaplist:
            count += 1
            if self.checkminfree(): 
                # dann ist jetzt genug frei
                return 
            else:
                if self.keepindays(snap,self.snapcount-count):
                    self.log.info(f'{self.fsys}: Abbruch cleanup wegen Anzahl "keep ({self.snapcount-count} <= {self.ns.keepsnapshots}) in nodeletedays ({self.ns.nodeletedays})"')
                    return
            if self.destroysnapshot(snap):
                    count -= 1
        self.log.debug(f'{self.fsys}: Ende Cleanup, mehr können wir nicht löschen...')
    
    
    def get_rootfs(self,fsys):
        # für Proxmox zu ändern
        self.pool = fsys.split('/')[0]
    
    def check_hold(self,snapshot):
       
        cmd = f' zfs list -H -d 1 -t snapshot -o userrefs,name {snapshot}'
        ret = subrun(cmd,stdout=subprocess.PIPE,universal_newlines=True)
        ret.check_returncode()
        if ret.stdout == None:
            return
        for i in ret.stdout.split('\n'):
            if len(i) == 0:
                return False
            j = i.split('\t')
            if int(j[0]) > 0:
                return True
        return False    
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
        heute = datetime.datetime.utcnow()
        vgl = self.fsys+'@'+self.ns.prefix+'_'
        l = len(vgl)
        dstring = snap[l:l+10] # damit wird nun noch mit dem glatten Datum verglichen - ohne Stunde/Minute
        # Damit sollte es keine Rolle mehr spielen, wann das Script an einem Tag aufgerufen wird - Die diff-Tage
        # sind immer gleich
        
        dt = datetime.datetime.strptime(dstring,'%Y-%m-%d')
        tmp = heute - dt
        days = tmp.days
        return days
    
    def get_snaplist(self):
        
        arg = shlex.split('zfs list -H -t snapshot -o name '+self.fsys) # -r entfernt da imho hier nicht zielführend 2023-10-07 
        aus = subprocess.run(arg,stdout=subprocess.PIPE,universal_newlines=True)
        aus.check_returncode()
        # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
        vgl = self.fsys+'@'+self.ns.prefix+'_'
        l = len(vgl)
        listesnaps = []
        for snp in aus.stdout.split('\n'):
            
            if snp[0:l] == vgl:
                if self.check_hold(snp): # Schmeisst die auf Keep auch raus
                    continue
                else:
                    listesnaps.append(snp)
        self.snapcount = len(listesnaps)
        self.snaplist = sorted(listesnaps)
    
    def checkminfree(self,tell=False):
        
        ''' Prüft den freien Space im FS 
        
        true falls ja'''
               
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
        
        if self.ns.recursion_new == "zfs":
            add_r = "-r" 
        else:
            add_r = ''
        cmd = f'zfs destroy {add_r} {snap}'
        args = shlex.split(cmd)
        
        if self.ns.dryrun:
            return False
        else:
            aus = subprocess.run(args,stderr=subprocess.PIPE)
            if aus.returncode > 0:
                self.log.info(f'Problem beim Löschen: {aus.stderr.decode("UTF-8")}')
                return False
            else:
                self.log.info(cmd)
                self.snapcount -= 1 # Jetzt ist wirklich einer weniger
                if get_zfs_main_version() >= 2:
                    args = f"zpool wait -t free {self.pool}"
                    aus = subrun(args,stdout=subprocess.PIPE,universal_newlines=True) 
                else:
                    time.sleep(20) # 20 Sekunden warten damit das Löschen soweit durch ist (nur bei zfs < 2.0)
                
                return True
    
    def takesnapshot(self):
        
        if self.ns.recursion_new == "zfs":
            add_r = "-r" 
        else:
            add_r = ''
        if self.ns.no_snapshot:
            self.log.debug(f'{self.fsys}: Kein Snapshot wegen -x')
            return
        
        if self.checkminfree():
            self.log.info(f'{self.fsys}: Take Snapshot')
            snapname = self.fsys+'@'+ self.snapname()
            cmd = f'zfs snapshot {add_r} {snapname}'
            self.log.info(cmd)
            if self.ns.dryrun:
                pass
            else:
                aus = subprocess.run(shlex.split(cmd))
                try:
                    aus.check_returncode()
                except subprocess.CalledProcessError as grepexc: 
                    self.log.info(f"error code {grepexc.returncode}, {grepexc.output}")
                    self.log.info("Abbruch, da Snapshot nicht erstellt werden konnte!")
                    exit()
                self.snapcount += 1
    
class pct_dataset(zfs_dataset):
    ''' Hier werden die Proxmox Container behandelt. Auf ein paar Funktionen der zfsdatasets
    kann dabei zurückgegriffen werden '''
    def command(self):
        return "pct"
    
    def checkminfree(self,tell=False):
        ''' Für Proxmox immer true, da nicht direkt geprüft werden kann '''
        return True
    def check_hold(self,snapshot):
        ''' Für Proxmox immer false, da kein hold-tag direkt mit dem snapshot verknüpft '''
        return False
    def get_rootfs(self, fsys):
        self.pool = None
    def takesnapshot(self):
        if self.ns.no_snapshot:
            self.log.debug(f'{self.fsys}: Kein Snapshot wegen -x')
            return
        self.log.info(f'{self.fsys}: Take Snapshot')
        snapname = self.snapname()
        if self.ns.dryrun:
            return
        cmd = f'{self.command()} snapshot {self.fsys} {snapname}'
        self.log.info(cmd)
        subrun(cmd)
        self.snapcount += 1
        
    def destroysnapshot(self,snap):
        cmd = f'{self.command()} delsnapshot {self.fsys} {snap}'
        self.log.info(cmd)
        subrun(cmd)
        self.snapcount -= 1
        time.sleep(5)
    
    def get_snaplist(self):
        
        arg = f'{self.command()} listsnapshot {self.fsys}'
        aus = subrun(arg,stdout=subprocess.PIPE,universal_newlines=True)
        # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
        vgl = self.ns.prefix+'_'
        l = len(vgl)
        listesnaps = []
        for snp in aus.stdout.split('\n')[:-1]:
            self.log.debug(snp)
            snapn = snp.split()[1]
            if snapn[0:l] == vgl:
                if self.check_hold(snp): # Schmeisst die auf Keep auch raus
                    continue
                else:
                    listesnaps.append(snapn)
        self.snapcount = len(listesnaps)
        self.snaplist = sorted(listesnaps)
    def diffdays(self,snap):
        #erstmal die difftage zu heute ermitteln
        newsnap = f'{self.fsys}@{snap}'
        return super().diffdays(newsnap)

class qm_dataset(pct_dataset):
    ''' Ein Vm-Dataset in Proxmox - also sehr ähnlich zum CT-Dataset '''
    def command(self):
        return "qm"
        
class proxmox_base(object):
    '''
    Zuständig für Proxmox-Server
    '''
    def __init__(self,argumente):
        self.ns = argumente
        self.log = logging.getLogger(LOGNAME)
        self.vms = self.collect_vms()
        self.cts = self.collect_cts()
        self.log.debug(f"VMs: {self.vms}")
        self.log.debug(f'CTs: {self.cts}')
        pass
    def collect_vms(self):
        ''' Sammelt alle VMs
        '''
        vms = []
        erg = subrun("qm list",stdout=subprocess.PIPE,universal_newlines=True)
        for i in erg.stdout.split('\n')[1:-1]:
            vm = i.split()
            vms.append(vm[0])
        return vms
    
    def collect_cts(self):
        ''' Sammelt alle Container '''
        cts = []
        erg = subrun("pct list",stdout=subprocess.PIPE,universal_newlines=True)
        
        for i in erg.stdout.split('\n')[1:-1]:
            ct = i.split()
            cts.append(ct[0])
        return cts
    
    def get_systems(self):
        ''' Übergibt die Systeme zur weiteren Behandlung'''
        for i in self.vms:
            ret = qm_dataset(i,self.ns)
            yield ret    
        for i in self.cts:
            ret = pct_dataset(i,self.ns)
            yield ret
class zfs_base(object):
    '''
    Zuständig für zfs-datasets
    '''
    def __init__(self,argumente):
        ''' Sammelte die zu behandelnden datasets
        '''
        self.log = logging.getLogger(LOGNAME)
        self.ns = argumente
        
        
        if self.collect_sets() == False:
            self.log.info('Kein korrektes Filesystem übergeben!')
            return
        self.log.debug(self.fslist)
        if self.ns.recursion_new == "zfs" and self.ns.withoutroot:
            self.log.info('Option --without-root ist nicht kompatibel mit --R zfs!')
            return
        if self.ns.withoutroot:
            self.startlist = 1
        else:
            self.startlist = 0
    
    def collect_sets(self):
        ''' Sammelt jetzt tatsächlich -> im zfs-mode
        '''
        self.fslist = []
        if (self.ns.recursion_new == None and self.ns.recursion) or self.ns.recursion_new == "zfsnappy": 
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
        ''' Soll schauen, ob das Filesystem auf com.sun:auto-snapshot=False gesetzt 
        Wenn das zutrifft -> kein snapshot - return false '''
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
    
    def get_systems(self):
        ''' Übergibt die Systeme zur weiteren Behandlung'''
        for i in self.fslist[self.startlist:]:
            ret = zfs_dataset(i,self.ns)
            yield ret
    
    
if __name__ == '__main__':
    a = zfsnappy()