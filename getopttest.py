'''
Created on 10.12.2016

@author: volker
'''
import sys
from optparse import OptionParser

def main():
    parser = OptionParser()
    parser.add_option("-i", "--holdinterval", dest="holds",
                  help="Holdintervall und Dauer",nargs=2,type='int',action='append')
    (options,args) = parser.parse_args(sys.argv[1:])
    print(options)



if __name__ == '__main__':
    main()
    pass