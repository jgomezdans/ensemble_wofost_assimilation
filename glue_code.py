import gdal
import datetime
from pathlib import Path 


def get_corners_lat_long(fname):
    """Retrieves the corners of a GDAL file, and returns the 
    corners and centre locations in Longitude/latitude.
    """

    L = gdal.Info(str(fname)).splitlines()[-6:-1]

    locs = []
    for line in L[:-1]:
        # Longitude
        deg = float(line.split()[5].replace("(", "").split("d")[0] )
        mins = float(line.split()[5].replace("(", "").split("d")[1].split("'")[0] )
        secs = float(line.split()[5].replace("(", "").split("d")[1].split("'")[1].split('"')[0] )
        long = deg + mins/60. + secs/(3600)
        # Latitude
        deg = float(line.split()[6].replace("(", "").split("d")[0] )
        mins = float(line.split()[6].replace("(", "").split("d")[1].split("'")[0] )
        secs = float(line.split()[6].replace("(", "").split("d")[1].split("'")[1].split('"')[0] )
        lat = deg + mins/60. + secs/(3600)
        locs.append([long, lat])
    # Center point
    # Longitude
    line = L[-1]
    deg = float(line.split()[4].replace("(", "").split("d")[0] )
    mins = float(line.split()[4].replace("(", "").split("d")[1].split("'")[0] )
    secs = float(line.split()[4].replace("(", "").split("d")[1].split("'")[1].split('"')[0] )
    long = deg + mins/60. + secs/(3600)
    # Latitude
    deg = float(line.split()[5].replace("(", "").split("d")[0] )
    mins = float(line.split()[5].replace("(", "").split("d")[1].split("'")[0] )
    secs = float(line.split()[5].replace("(", "").split("d")[1].split("'")[1].split('"')[0] )
    lat = deg + mins/60. + secs/(3600)
    locs.append([long, lat])
    return locs


def find_lai_files(file_path, tile):
    """Finds LAI files under a given path that belong to a given S2 tile.
    Retrieves the dates, DoY and corner locations."""
    file_path = Path(file_path)

    files = [f for f in file_path.rglob(f"*{tile:s}*/**/lai.tif")]

    files.sort(key=lambda x:x.parents[3].name.split("_")[2])

    dates = [datetime.datetime.strptime(
            x.parents[3].name.split("_")[2], "%Y%m%dT%H%M%S") 
            for x in files]
    doys = [d.strftime("%Y%j") for d in dates]
    corner_locs = get_corners_lat_long(files[0])
    return files, dates, doys, corner_locs

if __name__ == "__main__":
    files, dates, doys, corner_locs = find_lai_files ("/home/ucfahm0/S2_data",
    "T50SLH")

    


