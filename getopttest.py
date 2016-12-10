'''
Created on 10.12.2016

@author: volker
'''
import sys
from optparse import OptionParser

def main():
    parser = OptionParser()
    parser.add_option("-i", "--holdinterval",
                  action="store", dest="inetrvall"
                  help="don't print status messages to stdout")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hoi:v", ["help", "output=",'--holdinterval='])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(err) # will print something like "option -a not recognized"
        #usage()
        sys.exit(2)
    output = None
    verbose = False
    for o, a in opts:
        print(o,a)
        if o == "-v":
            verbose = True
        elif o in ("-h", "--help"):
            #usage()
            sys.exit()
        elif o in ("-o", "--output"):
            output = a
        elif o in ('-i','--holdinterval'):
            print(a)
            #h,i = a.split(',')
            #print(h,i)
        else:
            assert False, "unhandled option"
    # ...


if __name__ == '__main__':
    main()
    pass