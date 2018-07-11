import sys
import argparse
import subprocess
import json
from pprint import pprint


def Main():

    host, warning, critical = GetArguments()

    dfOutput = FetchOutputFromRemoteHost(host)

    listOfExcludedDrives = GetDriveExcludesFromJson(host)

    driveUsages = GetUsedDrivePecentages(dfOutput, listOfExcludedDrives)

    CreateOutput(driveUsages, warning, critical)


def Syntax():
    print(" ")
    print(
        "  Command Syntax: check_solaris_disks.py [-H host] [-c val] [-w val]")
    print(" ")
    sys.exit(3)


def GetArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-H", help="Hostname")
    parser.add_argument("-w", help="Warning threshold")
    parser.add_argument("-c", help="Critical threshold")
    args = parser.parse_args()

    if args.H:
        host = args.H
    else:
        Syntax()

    if args.w:
        waring = args.w
    else:
        Syntax()

    if args.c:
        critical = args.c
    else:
        Syntax()

    return host, waring, critical


def FetchOutputFromRemoteHost(host):
    try:
        output = subprocess.Popen("ssh nagios@" + host + " " + "'/usr/bin/df -hl | /usr/bin/cat '",
                                  stdout=subprocess.PIPE, shell=True, universal_newlines=True)
        stdout, stderr = output.communicate()
    except Exception as e:
        print("SSH Error")
        sys.exit(3)

    return stdout


def GetDriveExcludesFromJson(host):

    try:
        with open('./SolarisDiskCheckConfig/SolarisDiskCheckConfig.json') as f:
            data = json.load(f)
    except Exception as e:
        print("Config file not found")
        sys.exit(3)

    for hostInJson in data:
        if(hostInJson["Name"] == host):
            return hostInJson["ExcludedMounts"]
    return None


def GetUsedDrivePecentages(dfOutput, listOfExcludedDrives):

    mountPointAndUsage = {}
    for line in dfOutput.splitlines():

        if "Mounted on" in line:
            continue

        if listOfExcludedDrives == None:
            try:
                mountPointAndUsage[line.split()[5]] = line.split()[4][:-1]
            except Exception:
                pass
        else:
            if line.split()[5] not in listOfExcludedDrives:
                try:
                    mountPointAndUsage[line.split()[5]] = line.split()[4][:-1]
                except Exception:
                    pass

    return mountPointAndUsage


def CreateOutput(driveUsages, warning, critical):

    sensitiveDriveUsages = {}

    for mountpoint, percentage in driveUsages.items():
        if(int(percentage) >= int(warning) and int(percentage) < int(critical)):
            sensitiveDriveUsages[mountpoint] = ["Warning", str(percentage)]

        elif(int(percentage) >= int(critical)):
            sensitiveDriveUsages[mountpoint] = ["Critical", str(percentage)]

    exitCode = 0
    status = "OK"

    if("Warning" in [x for v in sensitiveDriveUsages.values() for x in v]):
        exitCode = 1
        status = "WARNING"
    if("Critical" in [x for v in sensitiveDriveUsages.values() for x in v]):
        exitCode = 2
        status = "CRITICAL"

    print("DiskStatus " + status + ":: Number of sensitive mounts: " +
          str(len(sensitiveDriveUsages)))
    print("")

    if status != "OK":
        for mountpoint, statusAndPercentage in sensitiveDriveUsages.items():
            print(statusAndPercentage[0].ljust(30) +
                  mountpoint.ljust(30) + statusAndPercentage[1] + "%")

    sys.exit(exitCode)


Main()
