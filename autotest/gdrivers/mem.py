#!/usr/bin/env python
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test MEM format driver.
# Author:   Frank Warmerdam <warmerdam@pobox.com>
#
###############################################################################
# Copyright (c) 2005, Frank Warmerdam <warmerdam@pobox.com>
# Copyright (c) 2008-2012, Even Rouault <even dot rouault at mines-paris dot org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

import sys
import array
from osgeo import gdal


import gdaltest

###############################################################################
# Create a MEM dataset, and set some data, then test it.


def test_mem_1():

    #######################################################
    # Setup dataset
    drv = gdal.GetDriverByName('MEM')
    gdaltest.mem_ds = drv.Create('mem_1.mem', 50, 3)
    ds = gdaltest.mem_ds

    if ds.GetProjection() != '':
        gdaltest.post_reason('projection wrong')
        return 'fail'

    if ds.GetGeoTransform(can_return_null=True) is not None:
        gdaltest.post_reason('geotransform wrong')
        return 'fail'

    raw_data = array.array('f', list(range(150))).tostring()
    ds.WriteRaster(0, 0, 50, 3, raw_data,
                   buf_type=gdal.GDT_Float32,
                   band_list=[1])

    wkt = gdaltest.user_srs_to_wkt('EPSG:26711')
    ds.SetProjection(wkt)

    gt = (440720, 5, 0, 3751320, 0, -5)
    ds.SetGeoTransform(gt)

    band = ds.GetRasterBand(1)
    band.SetNoDataValue(-1.0)

    # Set GCPs()
    wkt_gcp = gdaltest.user_srs_to_wkt('EPSG:4326')
    gcps = [gdal.GCP(0, 1, 2, 3, 4)]
    ds.SetGCPs([], "")
    ds.SetGCPs(gcps, wkt_gcp)
    ds.SetGCPs([], "")
    ds.SetGCPs(gcps, wkt_gcp)
    ds.SetGCPs(gcps, wkt_gcp)

    #######################################################
    # Verify dataset.

    if band.GetNoDataValue() != -1.0:
        gdaltest.post_reason('no data is wrong')
        return 'fail'

    if ds.GetProjection() != wkt:
        gdaltest.post_reason('projection wrong')
        return 'fail'

    if ds.GetGeoTransform() != gt:
        gdaltest.post_reason('geotransform wrong')
        return 'fail'

    if band.Checksum() != 1531:
        gdaltest.post_reason('checksum wrong')
        print(band.Checksum())
        return 'fail'

    if ds.GetGCPCount() != 1:
        gdaltest.post_reason('GetGCPCount wrong')
        return 'fail'

    if len(ds.GetGCPs()) != 1:
        gdaltest.post_reason('GetGCPs wrong')
        return 'fail'

    if ds.GetGCPProjection() != wkt_gcp:
        gdaltest.post_reason('GetGCPProjection wrong')
        return 'fail'

    if band.DeleteNoDataValue() != 0:
        gdaltest.post_reason('wrong return code')
        return 'fail'
    if band.GetNoDataValue() is not None:
        gdaltest.post_reason('got nodata value whereas none was expected')
        return 'fail'

    gdaltest.mem_ds = None

    return 'success'

###############################################################################
# Open an in-memory array.


def test_mem_2():

    gdal.PushErrorHandler('CPLQuietErrorHandler')
    ds = gdal.Open('MEM:::')
    gdal.PopErrorHandler()
    if ds is not None:
        gdaltest.post_reason('opening MEM dataset should have failed.')
        return 'fail'

    try:
        import ctypes
    except ImportError:
        return 'skip'

    for libname in ['msvcrt', 'libc.so.6']:
        try:
            crt = ctypes.CDLL(libname)
        except OSError:
            crt = None
        if crt is not None:
            break

    if crt is None:
        return 'skip'

    malloc = crt.malloc
    malloc.argtypes = [ctypes.c_size_t]
    malloc.restype = ctypes.c_void_p

    free = crt.free
    free.argtypes = [ctypes.c_void_p]
    free.restype = None

    # allocate band data array.
    width = 50
    height = 3
    p = malloc(width * height * 4)
    if p is None:
        return 'skip'
    float_p = ctypes.cast(p, ctypes.POINTER(ctypes.c_float))

    # build ds name.
    dsnames = ['MEM:::DATAPOINTER=0x%X,PIXELS=%d,LINES=%d,BANDS=1,DATATYPE=Float32,PIXELOFFSET=4,LINEOFFSET=%d,BANDOFFSET=0' % (p, width, height, width * 4),
               'MEM:::DATAPOINTER=0x%X,PIXELS=%d,LINES=%d,DATATYPE=Float32' % (p, width, height)]

    for dsname in dsnames:

        for i in range(width * height):
            float_p[i] = 5.0

        ds = gdal.Open(dsname)
        if ds is None:
            gdaltest.post_reason('opening MEM dataset failed.')
            free(p)
            return 'fail'

        chksum = ds.GetRasterBand(1).Checksum()
        if chksum != 750:
            gdaltest.post_reason('checksum failed.')
            print(chksum)
            free(p)
            return 'fail'

        ds.GetRasterBand(1).Fill(100.0)
        ds.FlushCache()

        if float_p[0] != 100.0:
            print(float_p[0])
            gdaltest.post_reason('fill seems to have failed.')
            free(p)
            return 'fail'

        ds = None

    free(p)

    return 'success'

###############################################################################
# Test creating a MEM dataset with the "MEM:::" name


def test_mem_3():

    drv = gdal.GetDriverByName('MEM')
    ds = drv.Create('MEM:::', 1, 1, 1)
    if ds is None:
        return 'fail'
    ds = None

    return 'success'

###############################################################################
# Test creating a band interleaved multi-band MEM dataset


def test_mem_4():

    drv = gdal.GetDriverByName('MEM')

    ds = drv.Create('', 100, 100, 3)
    expected_cs = [0, 0, 0]
    for i in range(3):
        cs = ds.GetRasterBand(i + 1).Checksum()
        if cs != expected_cs[i]:
            gdaltest.post_reason('did not get expected checksum for band %d' % (i + 1))
            print(cs)
            return 'fail'

    ds.GetRasterBand(1).Fill(255)
    expected_cs = [57182, 0, 0]
    for i in range(3):
        cs = ds.GetRasterBand(i + 1).Checksum()
        if cs != expected_cs[i]:
            gdaltest.post_reason('did not get expected checksum for band %d after fill' % (i + 1))
            print(cs)
            return 'fail'

    ds = None

    return 'success'

###############################################################################
# Test creating a pixel interleaved multi-band MEM dataset


def test_mem_5():

    drv = gdal.GetDriverByName('MEM')

    ds = drv.Create('', 100, 100, 3, options=['INTERLEAVE=PIXEL'])
    expected_cs = [0, 0, 0]
    for i in range(3):
        cs = ds.GetRasterBand(i + 1).Checksum()
        if cs != expected_cs[i]:
            gdaltest.post_reason('did not get expected checksum for band %d' % (i + 1))
            print(cs)
            return 'fail'

    ds.GetRasterBand(1).Fill(255)
    expected_cs = [57182, 0, 0]
    for i in range(3):
        cs = ds.GetRasterBand(i + 1).Checksum()
        if cs != expected_cs[i]:
            gdaltest.post_reason('did not get expected checksum for band %d after fill' % (i + 1))
            print(cs)
            return 'fail'

    if ds.GetMetadataItem('INTERLEAVE', 'IMAGE_STRUCTURE') != 'PIXEL':
        gdaltest.post_reason('did not get expected INTERLEAVE value')
        return 'fail'

    ds = None

    return 'success'

###############################################################################
# Test out-of-memory situations


def test_mem_6():

    if gdal.GetConfigOption('SKIP_MEM_INTENSIVE_TEST') is not None:
        return 'skip'

    drv = gdal.GetDriverByName('MEM')

    # Multiplication overflow
    with gdaltest.error_handler():
        ds = drv.Create('', 1, 1, 0x7FFFFFFF, gdal.GDT_Float64)
    if ds is not None:
        gdaltest.post_reason('fail')
        return 'fail'
    ds = None

    # Multiplication overflow
    with gdaltest.error_handler():
        ds = drv.Create('', 0x7FFFFFFF, 0x7FFFFFFF, 16)
    if ds is not None:
        gdaltest.post_reason('fail')
        return 'fail'
    ds = None

    # Multiplication overflow
    with gdaltest.error_handler():
        ds = drv.Create('', 0x7FFFFFFF, 0x7FFFFFFF, 1, gdal.GDT_Float64)
    if ds is not None:
        gdaltest.post_reason('fail')
        return 'fail'
    ds = None

    # Out of memory error
    with gdaltest.error_handler():
        ds = drv.Create('', 0x7FFFFFFF, 0x7FFFFFFF, 1, options=['INTERLEAVE=PIXEL'])
    if ds is not None:
        gdaltest.post_reason('fail')
        return 'fail'
    ds = None

    # Out of memory error
    with gdaltest.error_handler():
        ds = drv.Create('', 0x7FFFFFFF, 0x7FFFFFFF, 1)
    if ds is not None:
        gdaltest.post_reason('fail')
        return 'fail'
    ds = None

    # 32 bit overflow on 32-bit builds, or possible out of memory error
    ds = drv.Create('', 0x7FFFFFFF, 1, 0)
    with gdaltest.error_handler():
        ds.AddBand(gdal.GDT_Float64)

    # Will raise out of memory error in all cases
    ds = drv.Create('', 0x7FFFFFFF, 0x7FFFFFFF, 0)
    with gdaltest.error_handler():
        ret = ds.AddBand(gdal.GDT_Float64)
    if ret == 0:
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'

###############################################################################
# Test AddBand()


def test_mem_7():

    drv = gdal.GetDriverByName('MEM')
    ds = drv.Create('MEM:::', 1, 1, 1)
    ds.AddBand(gdal.GDT_Byte, [])
    if ds.RasterCount != 2:
        return 'fail'
    ds = None

    return 'success'

###############################################################################
# Test SetDefaultHistogram() / GetDefaultHistogram()


def test_mem_8():

    drv = gdal.GetDriverByName('MEM')
    ds = drv.Create('MEM:::', 1, 1, 1)
    ds.GetRasterBand(1).SetDefaultHistogram(0, 255, [])
    ds.GetRasterBand(1).SetDefaultHistogram(1, 2, [5, 6])
    ds.GetRasterBand(1).SetDefaultHistogram(1, 2, [3000000000, 4])
    hist = ds.GetRasterBand(1).GetDefaultHistogram(force=0)
    ds = None

    if hist != (1.0, 2.0, 2, [3000000000, 4]):
        print(hist)
        return 'fail'

    return 'success'

###############################################################################
# Test RasterIO()


def test_mem_9():

    # Test IRasterIO(GF_Read,)
    src_ds = gdal.Open('data/rgbsmall.tif')
    drv = gdal.GetDriverByName('MEM')

    for interleave in ['BAND', 'PIXEL']:
        out_ds = drv.CreateCopy('', src_ds, options=['INTERLEAVE=%s' % interleave])
        ref_data = src_ds.GetRasterBand(2).ReadRaster(20, 8, 4, 5)
        got_data = out_ds.GetRasterBand(2).ReadRaster(20, 8, 4, 5)
        if ref_data != got_data:
            print(interleave)
            import struct
            print(struct.unpack('B' * 4 * 5, ref_data))
            print(struct.unpack('B' * 4 * 5, got_data))
            gdaltest.post_reason('fail')
            return 'fail'

        ref_data = src_ds.GetRasterBand(2).ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_line_space=100)
        got_data = out_ds.GetRasterBand(2).ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_line_space=100)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        ref_data = src_ds.ReadRaster(20, 8, 4, 5)
        got_data = out_ds.ReadRaster(20, 8, 4, 5)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        ref_data = src_ds.ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_band_space=1)
        got_data = out_ds.ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_band_space=1)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        out_ds.WriteRaster(20, 8, 4, 5, got_data, buf_pixel_space=3, buf_band_space=1)
        got_data = out_ds.ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_band_space=1)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        ref_data = src_ds.ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_line_space=100, buf_band_space=1)
        got_data = out_ds.ReadRaster(20, 8, 4, 5, buf_pixel_space=3, buf_line_space=100, buf_band_space=1)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        ref_data = src_ds.ReadRaster(20, 20, 4, 5, buf_type=gdal.GDT_Int32, buf_pixel_space=12, buf_band_space=4)
        got_data = out_ds.ReadRaster(20, 20, 4, 5, buf_type=gdal.GDT_Int32, buf_pixel_space=12, buf_band_space=4)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'
        out_ds.WriteRaster(20, 20, 4, 5, got_data, buf_type=gdal.GDT_Int32, buf_pixel_space=12, buf_band_space=4)
        got_data = out_ds.ReadRaster(20, 20, 4, 5, buf_type=gdal.GDT_Int32, buf_pixel_space=12, buf_band_space=4)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        # Test IReadBlock
        ref_data = src_ds.GetRasterBand(1).ReadRaster(0, 10, src_ds.RasterXSize, 1)
        # This is a bit nasty to have to do that. We should fix the core
        # to make that unnecessary
        out_ds.FlushCache()
        got_data = out_ds.GetRasterBand(1).ReadBlock(0, 10)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        # Test IRasterIO(GF_Write,)
        ref_data = src_ds.GetRasterBand(1).ReadRaster(2, 3, 4, 5)
        out_ds.GetRasterBand(1).WriteRaster(6, 7, 4, 5, ref_data)
        got_data = out_ds.GetRasterBand(1).ReadRaster(6, 7, 4, 5)
        if ref_data != got_data:
            gdaltest.post_reason('fail')
            return 'fail'

        # Test IRasterIO(GF_Write, change data type) + IWriteBlock() + IRasterIO(GF_Read, change data type)
        ref_data = src_ds.GetRasterBand(1).ReadRaster(10, 11, 4, 5, buf_type=gdal.GDT_Int32)
        out_ds.GetRasterBand(1).WriteRaster(10, 11, 4, 5, ref_data, buf_type=gdal.GDT_Int32)
        got_data = out_ds.GetRasterBand(1).ReadRaster(10, 11, 4, 5, buf_type=gdal.GDT_Int32)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        ref_data = src_ds.GetRasterBand(1).ReadRaster(10, 11, 4, 5)
        got_data = out_ds.GetRasterBand(1).ReadRaster(10, 11, 4, 5)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        # Test IRasterIO(GF_Write, resampling) + IWriteBlock() + IRasterIO(GF_Read, resampling)
        ref_data = src_ds.GetRasterBand(1).ReadRaster(10, 11, 4, 5)
        ref_data_zoomed = src_ds.GetRasterBand(1).ReadRaster(10, 11, 4, 5, 8, 10)
        out_ds.GetRasterBand(1).WriteRaster(10, 11, 8, 10, ref_data, 4, 5)
        got_data = out_ds.GetRasterBand(1).ReadRaster(10, 11, 8, 10)
        if ref_data_zoomed != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

        got_data = out_ds.GetRasterBand(1).ReadRaster(10, 11, 8, 10, 4, 5)
        if ref_data != got_data:
            print(interleave)
            gdaltest.post_reason('fail')
            return 'fail'

    return 'success'

###############################################################################
# Test BuildOverviews()


def test_mem_10():

    # Error case: building overview on a 0 band dataset
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1, 0)
    with gdaltest.error_handler():
        ds.BuildOverviews('NEAR', [2])

    # Requesting overviews when they are not
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
    if ds.GetRasterBand(1).GetOverviewCount() != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverview(-1) is not None:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverview(0) is not None:
        gdaltest.post_reason('fail')
        return 'fail'

    # Single band case
    ds = gdal.GetDriverByName('MEM').CreateCopy('', gdal.Open('data/byte.tif'))
    for _ in range(2):
        ret = ds.BuildOverviews('NEAR', [2])
        if ret != 0:
            gdaltest.post_reason('fail')
            return 'fail'
        if ds.GetRasterBand(1).GetOverviewCount() != 1:
            gdaltest.post_reason('fail')
            return 'fail'
        cs = ds.GetRasterBand(1).GetOverview(0).Checksum()
        if cs != 1087:
            gdaltest.post_reason('fail')
            print(cs)
            return 'fail'

    ret = ds.BuildOverviews('NEAR', [4])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverviewCount() != 2:
        gdaltest.post_reason('fail')
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(0).Checksum()
    if cs != 1087:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(1).Checksum()
    if cs != 328:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'

    ret = ds.BuildOverviews('NEAR', [2, 4])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverviewCount() != 2:
        gdaltest.post_reason('fail')
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(0).Checksum()
    if cs != 1087:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(1).Checksum()
    if cs != 328:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'

    # Test that average in one or several steps give the same result
    ds.GetRasterBand(1).GetOverview(0).Fill(0)
    ds.GetRasterBand(1).GetOverview(1).Fill(0)

    ret = ds.BuildOverviews('AVERAGE', [2, 4])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverviewCount() != 2:
        gdaltest.post_reason('fail')
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(0).Checksum()
    if cs != 1152:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(1).Checksum()
    if cs != 240:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'

    ds.GetRasterBand(1).GetOverview(0).Fill(0)
    ds.GetRasterBand(1).GetOverview(1).Fill(0)

    ret = ds.BuildOverviews('AVERAGE', [2])
    ret = ds.BuildOverviews('AVERAGE', [4])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverviewCount() != 2:
        gdaltest.post_reason('fail')
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(0).Checksum()
    if cs != 1152:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(1).Checksum()
    if cs != 240:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'

    ds = None

    # Multiple band case
    ds = gdal.GetDriverByName('MEM').CreateCopy('', gdal.Open('data/rgbsmall.tif'))
    ret = ds.BuildOverviews('NEAR', [2])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    cs = ds.GetRasterBand(1).GetOverview(0).Checksum()
    if cs != 5057:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs = ds.GetRasterBand(2).GetOverview(0).Checksum()
    if cs != 5304:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs = ds.GetRasterBand(3).GetOverview(0).Checksum()
    if cs != 5304:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    ds = None

    # Clean overviews
    ds = gdal.GetDriverByName('MEM').CreateCopy('', gdal.Open('data/byte.tif'))
    ret = ds.BuildOverviews('NEAR', [2])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    ret = ds.BuildOverviews('NONE', [])
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetOverviewCount() != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    ds = None

    return 'success'

###############################################################################
# Test CreateMaskBand()


def test_mem_11():

    # Error case: building overview on a 0 band dataset
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1, 0)
    if ds.CreateMaskBand(gdal.GMF_PER_DATASET) == 0:
        gdaltest.post_reason('fail')
        return 'fail'

    # Per dataset mask on single band dataset
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
    if ds.CreateMaskBand(gdal.GMF_PER_DATASET) != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(1).GetMaskFlags() != gdal.GMF_PER_DATASET:
        gdaltest.post_reason('fail')
        return 'fail'
    mask = ds.GetRasterBand(1).GetMaskBand()
    cs = mask.Checksum()
    if cs != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    mask.Fill(255)
    cs = mask.Checksum()
    if cs != 3:
        gdaltest.post_reason('fail')
        return 'fail'

    # Check that the per dataset mask is shared by all bands
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1, 2)
    if ds.CreateMaskBand(gdal.GMF_PER_DATASET) != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    mask1 = ds.GetRasterBand(1).GetMaskBand()
    mask1.Fill(255)
    mask2 = ds.GetRasterBand(2).GetMaskBand()
    cs = mask2.Checksum()
    if cs != 3:
        gdaltest.post_reason('fail')
        return 'fail'

    # Same but call it on band 2
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1, 2)
    if ds.GetRasterBand(2).CreateMaskBand(gdal.GMF_PER_DATASET) != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    mask2 = ds.GetRasterBand(2).GetMaskBand()
    mask2.Fill(255)
    mask1 = ds.GetRasterBand(1).GetMaskBand()
    cs = mask1.Checksum()
    if cs != 3:
        gdaltest.post_reason('fail')
        return 'fail'

    # Per band masks
    ds = gdal.GetDriverByName('MEM').Create('', 1, 1, 2)
    if ds.GetRasterBand(1).CreateMaskBand(0) != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    if ds.GetRasterBand(2).CreateMaskBand(0) != 0:
        gdaltest.post_reason('fail')
        return 'fail'
    mask1 = ds.GetRasterBand(1).GetMaskBand()
    mask2 = ds.GetRasterBand(2).GetMaskBand()
    mask2.Fill(255)
    cs1 = mask1.Checksum()
    cs2 = mask2.Checksum()
    if cs1 != 0 or cs2 != 3:
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'

###############################################################################
# Test CreateMaskBand() and overviews.


def test_mem_12():

    # Test on per-band mask
    ds = gdal.GetDriverByName('MEM').Create('', 10, 10, 2)
    ds.GetRasterBand(1).CreateMaskBand(0)
    ds.GetRasterBand(1).GetMaskBand().Fill(127)
    ds.BuildOverviews('NEAR', [2])
    cs = ds.GetRasterBand(1).GetOverview(0).GetMaskBand().Checksum()
    if cs != 267:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'

    # Default mask
    cs = ds.GetRasterBand(2).GetOverview(0).GetMaskBand().Checksum()
    if cs != 283:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'

    # Test on per-dataset mask
    ds = gdal.GetDriverByName('MEM').Create('', 10, 10, 2)
    ds.CreateMaskBand(gdal.GMF_PER_DATASET)
    ds.GetRasterBand(1).GetMaskBand().Fill(127)
    ds.BuildOverviews('NEAR', [2])
    cs = ds.GetRasterBand(1).GetOverview(0).GetMaskBand().Checksum()
    if cs != 267:
        gdaltest.post_reason('fail')
        print(cs)
        return 'fail'
    cs2 = ds.GetRasterBand(2).GetOverview(0).GetMaskBand().Checksum()
    if cs2 != cs:
        gdaltest.post_reason('fail')
        print(cs2)
        return 'fail'

    return 'success'

###############################################################################
# Check RAT support


def test_mem_rat():

    ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
    ds.GetRasterBand(1).SetDefaultRAT(gdal.RasterAttributeTable())
    if ds.GetRasterBand(1).GetDefaultRAT() is None:
        gdaltest.post_reason('fail')
        return 'fail'
    ds.GetRasterBand(1).SetDefaultRAT(None)
    if ds.GetRasterBand(1).GetDefaultRAT() is not None:
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'

###############################################################################
# Check CategoryNames support


def test_mem_categorynames():

    ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
    ds.GetRasterBand(1).SetCategoryNames(['foo'])
    if ds.GetRasterBand(1).GetCategoryNames() != ['foo']:
        gdaltest.post_reason('fail')
        return 'fail'
    ds.GetRasterBand(1).SetCategoryNames([])
    if ds.GetRasterBand(1).GetCategoryNames() is not None:
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'


###############################################################################
# Check ColorTable support

def test_mem_colortable():

    ds = gdal.GetDriverByName('MEM').Create('', 1, 1)
    ct = gdal.ColorTable()
    ct.SetColorEntry(0, (255, 255, 255, 255))
    ds.GetRasterBand(1).SetColorTable(ct)
    if ds.GetRasterBand(1).GetColorTable().GetCount() != 1:
        gdaltest.post_reason('fail')
        return 'fail'
    ds.GetRasterBand(1).SetColorTable(None)
    if ds.GetRasterBand(1).GetColorTable() is not None:
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'


###############################################################################
# cleanup

def test_mem_cleanup():
    gdaltest.mem_ds = None
    return 'success'


gdaltest_list = [
    test_mem_1,
    test_mem_2,
    test_mem_3,
    test_mem_4,
    test_mem_5,
    test_mem_6,
    test_mem_7,
    test_mem_8,
    test_mem_9,
    test_mem_10,
    test_mem_11,
    test_mem_12,
    test_mem_rat,
    test_mem_categorynames,
    test_mem_colortable,
    test_mem_cleanup]

if __name__ == '__main__':

    gdaltest.setup_run('mem')

    gdaltest.run_tests(gdaltest_list)

    sys.exit(gdaltest.summarize())
