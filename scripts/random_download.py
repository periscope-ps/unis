import requests
import subprocess
import concurrent.futures
import sys

UNIS_HOST = "dev.crest.iu.edu"
UNIS_PORT = "8888"
VIS_HREF  = "http://dlt.crest.iu.edu:42424"
DAYS = [ "280", "281", "282" ]



def download_day(day):
    search_url = "http://{host}:{port}/exnodes?name=reg={day1}LGN00.tar.gz|{day2}LGN00.zip".format(host = UNIS_HOST, port = UNIS_PORT, day1 = day, day2 = day)
    exnode_url = "http://{host}:{port}/exnodes/{eid}"
    try:
        response = requests.get(search_url)
        response = response.json()
    except requests.exceptions.RequestException as exp:
        print("Failed to connect to UNIS - {exp}".format(exp = exp))
        exit(-1)
    except ValueError as exp:
        print("Error while decoding json - {exp}".format(exp = exp))
        exit(-1)
    except Exception as exp:
        print("Unknown error while contacting UNIS - {exp}".format(exp = exp))
        exit(-1)

    tars = []
    zips = []
    
    for exnode in response:
        if exnode["name"].endswith(".tar.gz"):
            tars.append(exnode["id"])
        else:
            zips.append(exnode["id"])

    while True:
        for (tmpTar, tmpZip) in zip(tars, zips):
            call = subprocess.Popen(
                [
                    'lors_download',
                    '-t', '10',
                    '-b', '5m',
                    '-X', VIS_HREF,
                    '-o', "{eid}.tar.gz".format(eid = tmpTar),
                    exnode_url.format(host = UNIS_HOST, port = UNIS_PORT, eid = tmpTar)
                ]
            )
            call.communicate()
            result = call.returncode

            call = subprocess.Popen(
                [
                    'lors_download',
                    '-o', "{eid}.zip".format(eid = tmpZip),
                    '-t', '10',
                    '-b', '5m',
                    '-X', VIS_HREF,
                    exnode_url.format(host = UNIS_HOST, port = UNIS_PORT, eid = tmpZip)
                ]
            )

            call.communicate()
            result = call.returncode
    

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers = 3) as executor:
        for result in executor.map(download_day, DAYS):
            pass

if __name__ == "__main__":
    main()
