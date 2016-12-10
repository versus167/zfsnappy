'''
Created on 01.05.2016

@author: volker

Sammlung der commands:

sudo zfs list -Hp -o avail vs2016/archiv/test - Freier Platz in bytes
sudo zfs list -Hp -o used vs2016/archiv/test - Genutzer Platz in bytes
sudo zfs list -H -r -t snapshot -o name,creation vs2016/archiv/test - Liste der Snapshots mit Name und Erstelldatum
zfs destroy vs2016/archiv/test@hourly_2016-12-10_09.17.01--2d - Snapshot löschen


'''

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
    
    inters = []
    inter = intervall(5,3)
    inters.append(inter)
    inter = intervall(25,3)
    inters.append(inter)
    inter = intervall(1,5)
    inters.append(inter)
    for i in range(100,-1,-1):
        hold = False
        for x in inters:
            if x.checkday(i):
                hold = True
        print(i,hold)
    
    pass