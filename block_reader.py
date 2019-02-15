import numpy as np
import gdal
# Needs to
# 1. Record angles
GDAL2NUMPY = {gdal.GDT_Byte:   np.uint8,
              gdal.GDT_UInt16:   np.uint16,
              gdal.GDT_Int16:   np.int16,
              gdal.GDT_UInt32:   np.uint32,
              gdal.GDT_Int32:   np.int32,
              gdal.GDT_Float32:   np.float32,
              gdal.GDT_Float64:   np.float64,
              gdal.GDT_CInt16:   np.complex64,
              gdal.GDT_CInt32:   np.complex64,
              gdal.GDT_CFloat32:   np.complex64,
              gdal.GDT_CFloat64:   np.complex128
              }


def extract_chunks(the_files, the_bands=None):
    """A function that extracts chunks from datafiles"""
    ds_config = {}
    gdal_ptrs = []
    datatypes = []
    for the_file in the_files:
        g = gdal.Open(the_file)
        gdal_ptrs.append(gdal.Open(the_file))
        datatypes.append(GDAL2NUMPY[g.GetRasterBand(1).DataType])

    block_size = g.GetRasterBand(1).GetBlockSize()
    nx = g.RasterXSize
    ny = g.RasterYSize
    if the_bands is None:
        the_bands = np.arange(g.RasterCount) + 1
    proj = g.GetProjectionRef()
    geoT = g.GetGeoTransform()
    ds_config['nx'] = nx
    ds_config['ny'] = ny
    ds_config['nb'] = g.RasterCount
    ds_config['geoT'] = geoT
    ds_config['proj'] = proj
    block_size = [block_size[0]*2, block_size[1]*2]
    print("Blocksize is (%d,%d)" % (block_size[0], block_size[1]))
    #  block_size = [ 256, 256 ]
    #  store these numbers in variables that may change later
    nx_valid = block_size[0]
    ny_valid = block_size[1]
    # find total x and y blocks to be read
    nx_blocks = (int)((nx + block_size[0] - 1) / block_size[0])
    ny_blocks = (int)((ny + block_size[1] - 1) / block_size[1])
    buf_size = block_size[0] * block_size[1]
    ################################################################
    # start looping through blocks of data
    ################################################################
    # loop through X-lines
    for X in range(nx_blocks):
        # change the block size of the final piece
        if X == nx_blocks - 1:
            nx_valid = nx - X * block_size[0]
            buf_size = nx_valid * ny_valid

        # find X offset
        this_X = X * block_size[0]

        # reset buffer size for start of Y loop
        ny_valid = block_size[1]
        buf_size = nx_valid * ny_valid

        # loop through Y lines
        for Y in range(ny_blocks):
            # change the block size of the final piece
            if Y == ny_blocks - 1:
                ny_valid = ny - Y * block_size[1]
                buf_size = nx_valid * ny_valid

            # find Y offset
            this_Y = Y * block_size[1]
            data_in = []
            for ig, ptr in enumerate(gdal_ptrs):
                buf = ptr.ReadRaster(this_X, this_Y, nx_valid, ny_valid,
                                     buf_xsize=nx_valid, buf_ysize=ny_valid,
                                     band_list=the_bands)
                a = np.frombuffer(buf, dtype=datatypes[ig])
                data_in.append(a.reshape((
                    len(the_bands), ny_valid, nx_valid)).squeeze())

            yield (ds_config, this_X, this_Y, nx_valid, ny_valid,
                   data_in)
