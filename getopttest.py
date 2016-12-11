'''
Created on 10.12.2016

@author: volker
'''
import sys
import argparse

def main():
    parser = OptionParser()
    parser.add_option("-i", "--holdinterval", dest="holds",
                  help="Holdintervall und Dauer - Beispiel -i 1 10 (Intervall = 1 Tag, Anzahl = 10 Intervalle)",nargs=2,type='int',action='append')
    parser.add_option("-f","--filesystem",dest='zfsfs',
                      help='Übergabe des ZFS-Filesystems auf den die Snapshots ausgeführt werden sollen',action='store',
                      type='string')
    parser.add_option('-m','--minfree',dest='minfree',
                      help='Mindestens freizuhaltender Space auf dem FS in vollen Prozent',action='store',
                      type='int', default=20)
    (options,args) = parser.parse_args(sys.argv[1:])
    print(options)



if __name__ == '__main__':
    main()
    pass