'''
Created on 01.05.2016

@author: volker

Sammlung der commands:

1 - 2016-12-10 - Erste lauffähig Version

Prinzipiell geht es - Die Übergabe der Argumente  ist noch umzuschreiben
Der Code ist zu säubern...

sudo zfs list -Hp -o avail vs2016/archiv/test - Freier Platz in bytes
sudo zfs list -Hp -o used vs2016/archiv/test - Genutzer Platz in bytes
sudo zfs list -H -r -t snapshot -o name,creation vs2016/archiv/test - Liste der Snapshots mit Name und Erstelldatum
zfs destroy vs2016/archiv/test@hourly_2016-12-10_09.17.01--2d - Snapshot löschen
zfs snapshot vs2016/archiv/test@vs-2016 - Snapshot erstellen


'''

import os
import datetime

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
        Sonst falls.
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
    

if __name__ == '__main__':
    zfsfs = 'vs2016/archiv/test'
    snapprefix = 'vs'
    
    inters = []
    inter = intervall(5,3)
    inters.append(inter)
    inter = intervall(25,3)
    inters.append(inter)
    inter = intervall(1,5)
    inters.append(inter)
    
    # Hier käme dann der ABlauf
    # 1. Liste der vorhanden Snapshots
    aus = os.popen('zfs list -H -r -t snapshot -o name '+zfsfs).readlines()
    #print(aus) 
    
    # 2. Ausdünnen der Liste um die die nicht den richtigen Prefix haben
    vgl = zfsfs+'@'+snapprefix+'_'
    l = len(vgl)
    listesnaps = {}
    for i in aus:
        snp = i.strip('\n')
        if snp[0:l] == vgl:
            listesnaps[snp] = False
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
            print(i,chkday,hold)
            cmd = 'zfs destroy '+i
            print(cmd)
            aus = os.popen(cmd)
            for j in aus:
                print(j)
        else:
            print(i,chkday,hold)
    # Als letztes: Snapshot erstellen
    aktuell = datetime.datetime.now()
    snapname = zfsfs+'@'+snapprefix+'_'+aktuell.isoformat() 
    cmd = 'zfs snapshot '+snapname
    print(cmd)
    aus = os.popen(cmd)
    for j in aus:
        print(j)
    pass