"""
Created: Camden Opfer, March 2026

A collection of scripts to do basic analysis of CESM output
"""
import os
import numpy as np
import netCDF4 as nc

def cam_annual_mean(camRoot:str, variable:str = 'lev', year:str = '0001', subset:slice|None = None) -> np.ndarray:
    """
    Retrieves the average value of a variable across one year of CAM output from the h0 (monthly mean) files. Can be fooled if there are weird files in your output directory, as this function searches through all available files for those containing "h0.YYYY".

    Note that the output array will match the shape of those contained in the CAM h0 file. These, in turn, often have a time dimension, but with shape 1 along that dimension. This may lead to some confusion/awkwardness when handling the output from here where arr[0] looks very similar to arr, but has flattened the time dimension away.

    :param camRoot: A directory with a year's worth of CAM output. Often of the form "/scratch/$USER/cesm/output/archive/$CASE/atm/hist".
    :type camRoot: str
    :param variable: The variable contained within the netCDF file which you would like to average over. Default is elevation, since that was the first use case. ncdump an h0 file if you're looking for other options.
    :type cariable: str, optional
    :param year: The year of output data to consider. Default is the first year, "0001". Must match the "YYYY" format since that's what's used in CAM's file naming conventions.
    :type year: str, optional
    :param subset: The subset of data to take the mean of. A likely use case would be getting temperature at a certain level/height. Default is to take the entire dataset.
    :type subset: slice or None, optional

    :return: The mean value of the chosen variable. Matches the type of the variable within the netCDF file, but that's usually a numpy array or masked array.
    :rtype: np.ndarray
    """
    allFiles = os.listdir(camRoot)
    usedFiles = [''] * 12

    for file in allFiles:
        if f'h0.{year}' in file:
            endFileName = file.split(f'h0.{year}')[-1]
            month = int(endFileName[1:3]) - 1
            usedFiles[month] = os.path.join(camRoot, file)

    for usedFile in usedFiles:
        with nc.Dataset(usedFile, 'r') as monthData:
            monthVar = monthData.variables[variable][:]
            if subset is not None:
                monthVar = monthVar[subset]

            try:
                meanVar += monthVar
            except NameError: # Need to initialize meanVar
                meanVar = monthVar[:]

    meanVar /= 12

    return meanVar

if __name__ == '__main__':
    camDir = '/home/cmopfer/scratch/cesm/output/archive/NdgParams_Ctrl/atm/hist'
    cam_annual_mean(camDir)
