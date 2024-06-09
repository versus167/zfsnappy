# zfsnappy
Kleines Pythonscript, welches unkompliziert die Zauberei mit snapshots in ZFS übernimmt. Imho einfacher und flexibler als die übrigen verfügbaren Tools. Ist aber wohl Geschmackssache ;)

Okay, readme muss noch erstellt werden... zfsnappy -h sollte derweil helfen:

usage: zfsnappy [-h] [--proxmox] [-i HOLDS HOLDS] [-f ZFSFS] [-m MINFREE] [-s FREESPACE] [-p PREFIX] [-d DM] [-n NODELETEDAYS] [-v] [-r] [-R {zfsnappy,zfs}]
                [-k KEEPSNAPSHOTS] [-x] [--dryrun] [--without-root] [-t TOUCHFILE]

options:
  -h, --help            show this help message and exit
  --proxmox             Proxmox-Mode - erstellt snapshots von VMs und Containern (default: False)
  -i HOLDS HOLDS, --holdinterval HOLDS HOLDS
                        Holdintervall und Dauer - Beispiel -i 1 10 (Intervall = 1 Tag, Anzahl = 10 Intervalle) (default: [])
  -f ZFSFS, --filesystem ZFSFS
                        Übergabe des ZFS-Filesystems auf den die Snapshots ausgeführt werden sollen (default: None)
  -m MINFREE, --minfree MINFREE
                        Mindestens freizuhaltender Space auf dem FS in vollen Prozent (default: 20)
  -s FREESPACE, --spacefree FREESPACE
                        Mindestens freier Speicher in GB - default ausgeschalten (default: 0)
  -p PREFIX, --prefix PREFIX
                        Der Prefix für die Bezeichnungen der Snapshots (default: zfsnappy)
  -d DM, --deletemode DM
                        Deletemodus 1 = mur falls minfree unterschritten, 2 - regulär laut Intervall + minfree, 3 - es wird nichts gelöscht (default: 1)
  -n NODELETEDAYS, --nodeletedays NODELETEDAYS
                        Anzahl Tage an dem nichts gelöscht werden soll. Es sei denn der Speicher ist zu knapp und [keep] lässt löschen zu. (default: 10)
  -v, --verbose         Macht das Script etwas gesprächiger (default: False)
  -r, --recursion       Wendet die Einstellungen auch auf alle Filesysteme unterhalb dem übergebenen an - wenn -R angegeben dann wird -r ignoriert (default: False)
  -R {zfsnappy,zfs}, --Recursive {zfsnappy,zfs}
                        bei "zfsnappy" Einstellungen werden auch auf alle Dateisysteme unterhalb des übergeben angewendet. Bei "zfs" wird die Funktionalität von zfs dafür
                        verwendet (default: None)
  -k KEEPSNAPSHOTS, --keep KEEPSNAPSHOTS
                        Diese Anzahl an Snapshots wird auf jeden Fall innerhalb der NODELETEDAYS behalten (default: 0)
  -x, --no_snapshot     Erstellt keinen neuen Snapshot - Löscht aber, wenn nötig. (default: False)
  --dryrun              Trockentest ohne Veränderung am System (default: False)
  --without-root        zfsnappy wird nicht auf den root des übergebenen Filesystems angewendet (default: False)
  -t TOUCHFILE, --touchfile TOUCHFILE
                        Dieses File erhält einen 'Touch', wenn alles ohne Fehler durchging. (default: None)

