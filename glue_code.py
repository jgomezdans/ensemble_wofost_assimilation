#!/usr/bin/env python

import datetime

from pathlib import Path

import gdal

import numpy as np

import enwofost

from block_reader import extract_chunks

def get_corners_lat_long(fname):
    """Retrieves the corners of a GDAL file, and returns the 
    corners and centre locations in Longitude/latitude.
    """

    L = gdal.Info(str(fname)).splitlines()[-6:-1]

    locs = []
    for line in L[:-1]:
        # Longitude
        deg = float(line.split()[5].replace("(", "").split("d")[0])
        mins = float(
            line.split()[5].replace("(", "").split("d")[1].split("'")[0]
        )
        secs = float(
            line.split()[5]
            .replace("(", "")
            .split("d")[1]
            .split("'")[1]
            .split('"')[0]
        )
        long = deg + mins / 60.0 + secs / (3600)
        # Latitude
        deg = float(line.split()[6].replace("(", "").split("d")[0])
        mins = float(
            line.split()[6].replace("(", "").split("d")[1].split("'")[0]
        )
        secs = float(
            line.split()[6]
            .replace("(", "")
            .split("d")[1]
            .split("'")[1]
            .split('"')[0]
        )
        lat = deg + mins / 60.0 + secs / (3600)
        locs.append([long, lat])
    # Center point
    # Longitude
    line = L[-1]
    deg = float(line.split()[4].replace("(", "").split("d")[0])
    mins = float(line.split()[4].replace("(", "").split("d")[1].split("'")[0])
    secs = float(
        line.split()[4]
        .replace("(", "")
        .split("d")[1]
        .split("'")[1]
        .split('"')[0]
    )
    long = deg + mins / 60.0 + secs / (3600)
    # Latitude
    deg = float(line.split()[5].replace("(", "").split("d")[0])
    mins = float(line.split()[5].replace("(", "").split("d")[1].split("'")[0])
    secs = float(
        line.split()[5]
        .replace("(", "")
        .split("d")[1]
        .split("'")[1]
        .split('"')[0]
    )
    lat = deg + mins / 60.0 + secs / (3600)
    locs.append([long, lat])
    return locs


def find_lai_files(file_path, tile):
    """Finds LAI files under a given path that belong to a given S2 tile.
    Retrieves the dates, DoY and corner locations."""
    file_path = Path(file_path)

    files = [f for f in file_path.rglob(f"*{tile:s}*/**/lai.tif")]

    files.sort(key=lambda x: x.parents[3].name.split("_")[2])

    dates = [
        datetime.datetime.strptime(
            x.parents[3].name.split("_")[2], "%Y%m%dT%H%M%S"
        )
        for x in files
    ]
    doys = [d.strftime("%Y%j") for d in dates]
    corner_locs = get_corners_lat_long(files[0])
    return files, dates, doys, corner_locs


def run_wofost_ensembles(corner_locs, en_size=20, start_date = datetime.date(2017,10,12)):
    pkg_location = enwofost.__file__.strip("__init__.py") + "data/"
    parameter_priors = pkg_location + "par_prior.csv"
    ensembles = []
    
    for corner in corner_locs:
        lng, lat = corner

        ens_out_fname = f"ens_{lng:6.3f}_{lat:6.3f}.npy"
        enwofost.ensemble_wofost(lon = lng, lat=lat, start = start_date,
                    end = None, en_size = en_size, prior_file = parameter_priors, 
                    weather_type = "ERA", weather_path = "/home/ucfahm0/NC/",
                    out_en_file = ens_out_fname,
                    data_dir=pkg_location)
        ensembles.append(ens_out_fname)


    ens_lai = []
    ens_days = []
    ens_yield = []
    for ens_file in ensembles:
        f = np.load(ens_file)
        this_lai = np.array([ens['LAI'] for ens in f])
        this_time = np.array([list(
            map(lambda x:datetime.date.strftime(x, "%Y%j"), ens['day'])) 
        for ens in f])
        this_yield = np.array([ens['Yield'] for ens in f])
        ens_lai.append(this_lai)
        ens_days.append(this_time)
        ens_yield.append(this_yield)
    ens_lai = np.array(ens_lai).reshape((en_size*5, -1))
    ens_yield = np.array(ens_yield).reshape((en_size*5, -1))
    ens_days = np.array(ens_days).reshape((en_size*5, -1))
    return (ens_days, ens_lai, ens_yield)


def match_ensembles_to_lai(files, dates, doys,
                           ens_days, ens_lai, ens_yield, threshold=3.5):    
    matched_files = []
    matched_ensemble = []
    matched_ens_times = []
    matched_ens_lai = []
    for i, lai_file in enumerate(files):
        curr_date = doys[i]
        try:
            curr_ens_loc = ens_days[0].tolist().index(curr_date)
        except ValueError:
            continue
        matched_ensemble.append(curr_ens_loc)
        matched_ens_times.append(curr_date)
        matched_ens_lai.append(ens_lai[:, curr_ens_loc])
        matched_files.append(lai_file)
        #today_distance = (this_lai[mask])[:, None] - \
        #                ens_lai[:, curr_ens_loc]


    matched_ens_lai = np.array(matched_ens_lai)
    assimilated_yield_mean = []
    assimilated_yield_std = []
    for (i, (file_info, this_X, this_Y, nx_valid, 
         ny_valid, data_chunks)) in enumerate(extract_chunks(
                                [str(f) for f in matched_files])):
        print("Chunk #", i+1)
        data_chunks = np.array(data_chunks)
        mask = np.logical_and(data_chunks >= 0.0,
                              data_chunks <= 10.)
        data_chunks[~mask] = np.nan
        
        D = data_chunks[:, :, :, None] - np.array(matched_ens_lai)[:, None, None, :]
        
        m1 = np.abs(D) < threshold
        m1[~mask] = True
        sel = np.all(m1, axis=0)
        Y=ens_yield.squeeze()[:, None, None] * sel.transpose(2, 0, 1)
        Y[Y==0.0] = np.nan
        assimilated_yield_mean.append(np.nanmean(Y, axis=0))
        assimilated_yield_std.append(np.nanstd(Y, axis=0))
        
    assimilated_yield_mean = np.hstack([
        np.vstack(assimilated_yield_mean[(i*11):((i+1)*11)]) 
               for i in range(11)])
    assimilated_yield_std = np.hstack([
        np.vstack(assimilated_yield_std[(i*11):((i+1)*11)]) 
               for i in range(11)])

    return assimilated_yield_mean, assimilated_yield_std

if __name__ == "__main__":
    files, dates, doys, corner_locs = find_lai_files(
        "/home/ucfahm0/S2_data", "T50SLH"
    )
    
    ens_days, ens_lai, ens_yield = run_wofost_ensembles(
        corner_locs, en_size=10, start_date = datetime.date(2017,10,12))

    assimilated_yield_mean, assimilated_yield_std = match_ensembles_to_lai(files, dates, doys,
                           ens_days, ens_lai, ens_yield)
