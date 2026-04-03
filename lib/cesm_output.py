"""
Created: Camden Opfer, March 2026

A collection of scripts to do basic analysis of CESM output
"""
import os
import glob
import re
import numpy as np
import netCDF4 as nc
from .utils import log

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
        if 'cam' in file and f'h0.{year}' in file:
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

def query(outputPath:str, archive:bool = True, searchTerm:str|None = None, returnPath:str|None = None):
    """
    Identifies the different types of netCDF files (e.g. <run-name>.cam.h1 or <run-name>.clm2.h0) within the output path, searching through <component>/hist subdirectories if this is the path to an archive directory. If a search term is provided, will return a list of files/variables containing that term (if any exist). If return path is specified, the output of this function is saved to a text file.

    :param outputPath: The root directory for the CESM run's output.
    :type outputPath: str
    :param archive: Whether this is an archive directory (query will search for outputPath/<component>/hist/*.nc files) or not (query will search for outputPath/*.nc files)
    :type archive: bool, optional
    :param searchTerm: A string (can be a regex string) which the variable names and descriptions of all relevant output files will be searched for. Default is None, so all files/variables are returned. Still helpful because they are neatly organized.
    :type searchTerm: str or None, optional
    :param returnPath: Path to a text file to which the output of this function will be written. Default is None, in which case cccs.utils.log will either print or log the output.
    :type returnPath: str or None, optional
    """
    def queryOutput(output, returnFile = returnPath):
        """
        Either logs the output of query() or saves it to the specified path.
        """
        if returnFile is None:
            log(output)
        else:
            try:
                os.makedirs(returnPath, exist_ok=True)
                with open(returnFile, 'a', encoding='UTF-8') as f:
                    f.write('\n' + output)
            except Exception as e:
                log(f'Saving queryOutput to file had error: {e}\nWill log output instead.')
                log(output)

    # Get list of all the potentially relevant files
    if archive:
        allFiles = glob.glob(os.path.join(outputPath, '*', 'hist', '*.nc'), recursive=True) # Assumes outputPath/<component>/hist/<fname>.nc structure
    else:
        allFiles = glob.glob('*.nc', root_dir=outputPath) # Assumes outputPath/<fname>.nc structure

    allFiles.sort()

    # Find files with unique forms. E.g. <run-name>.cam.h0.stuff and <run-name>.cam.h1.things are different kinds of file, but not <run-name>.cam.h0.stuff and <run-name>.cam.h0.blah
    fileTypes = {}
    for file in allFiles:
        fname = os.path.basename(file) # Get the bit after the last / (or \ if on Windows for some reason)
        ftype = '.'.join(fname.split('.')[-4:-2])
        try:
            fileTypes[ftype].append(file)
        except KeyError:
            fileTypes[ftype] = [file]

    queryOutput(f'Found {len(fileTypes)} distinct file types.')

    if searchTerm:
        hits = []
        for files in fileTypes.values():
            ds = nc.Dataset(files[0], 'r')
            varsDict = ds.variables

            for varName, varDescription in varsDict.items():
                varName, varDescription = str(varName), str(varDescription)
                if re.search(searchTerm, varName, flags=re.IGNORECASE) or re.search(searchTerm, varDescription, flags=re.IGNORECASE):
                    hits.append([files, varName, varDescription])

        if hits:
            queryOutput(f'Found {len(hits)} types of files satisfying the search term. They are...')
            for hit in hits:
                reportedFiles = hit[0]
                if len(reportedFiles) > 5:
                    reportedFiles = reportedFiles[:3] + ['...'] + [reportedFiles[-1]]
                queryOutput(f'\n\tFiles:\n{reportedFiles}\n\tVariable name: {hit[1]}\n\tVariable details:\n{hit[2]}')
        else:
            queryOutput(f'No output files matching search term {searchTerm} found in {outputPath}.')

    else:
        for files in fileTypes.values():
            ds = nc.Dataset(files[0], 'r')
            varsDict = ds.variables

            queryOutput(f'\nThe files:\n{files}\nContain the variables:\n{varsDict}\n')

if __name__ == '__main__':
    camDir = '/home/cmopfer/scratch/cesm/output/archive/NdgParams_Ctrl/atm/hist'
    cam_annual_mean(camDir)
