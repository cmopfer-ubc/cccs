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

def cam_annual_mean(camRoot:str, variable:str = 'lev', years:list[str]|None = None, subset:slice|None = None, landWeight:bool = False) -> np.ndarray:
    """
    Retrieves the average value of a variable across one year of CAM output from the h0 (monthly mean) files. Can be fooled if there are weird files in your output directory, as this function searches through all available files for those containing "h0.YYYY". The mean will always be weighted by grid cell size, and can optionally be weighted by how much land is in the grid cell (essentially masking the mean to land).

    Note that the output array will match the shape of those contained in the CAM h0 file. These, in turn, often have a time dimension, but with shape 1 along that dimension. This may lead to some confusion/awkwardness when handling the output from here where arr[0] looks very similar to arr, but has flattened the time dimension away. This can be resolved by passing subset=(0,).

    :param camRoot: A directory with a year's worth of CAM output. Often of the form "/scratch/$USER/cesm/output/archive/$CASE/atm/hist".
    :type camRoot: str
    :param variable: The variable contained within the netCDF file which you would like to average over. Default is elevation, since that was the first use case. ncdump an h0 file if you're looking for other options.
    :type cariable: str, optional
    :param years: A list years of output data to consider. Default is the first year, "0001", only. List elements match the "YYYY" format since that's what's used in CAM's file naming conventions.
    :type years: list[str], optional
    :param subset: The subset of data to take the mean of. A likely use case would be getting temperature at a certain level/height. Default is to take the entire dataset.
    :type subset: slice or None, optional
    :param landWeight: A trigger for weighting the mean by the fraction of the grid cell covered by land, as determined by the cam.h0 landfrac variable. Helpful when something only the land model was perturbed. Default is False, meaning the average is unweighted.
    :type landWeight: bool, optional

    :return: The mean value of the chosen variable. Matches the type of the variable within the netCDF file, but that's usually a numpy array or masked array.
    :rtype: np.ndarray
    """
    def getGridArea(camRoot):
        try:
            # Tries for lnd output is in same directory, typical of output/$CASE/run/ directories
            run = glob.glob('*.clm2.h0.*.nc', root_dir=camRoot)
            if run:
                clmRunFile = os.path.join(camRoot, run[0])
                with nc.Dataset(clmRunFile, 'r') as clmDummy:
                    area = clmDummy.variables['area'][:]
                log(f'Retrieved grid cell area form land data in {clmRunFile}', 'debug')
                return area

            # Tries for lnd output is in a relative path typical of an archive directory, like output/archive/$CASE/atm/hist/
            clmArchiveRoot = os.path.join(camRoot, '..', '..', 'lnd', 'hist')
            archive = glob.glob('*.clm2.h0.*.nc', root_dir=clmArchiveRoot)
            if archive:
                clmArchiveFile = os.path.join(clmArchiveRoot, archive[0])
                with nc.Dataset(clmArchiveFile, 'r') as clmDummy:
                    area = clmDummy.variables['area'][:]
                log(f'Retrieved grid cell area form land data in {clmArchiveFile}', 'debug')
                return area
        except Exception as _:
            pass
        raise FileNotFoundError(f'Unable to locate land output for grid area in directories {camRoot} or {os.path.join(camRoot, '..', '..', 'lnd', 'hist')}')

    if years is None:
        years = ['0001']

    paths = [''] * 12 * len(years)
    for yInd, year in enumerate(years):
        files = glob.glob(f'*cam.h0.{year}*', root_dir=camRoot)
        for file in files:
            monthInd = int(file[-5:-3]) - 1
            paths[yInd * 12 + monthInd] = os.path.join(camRoot, file)

    for tInd, monthPath in enumerate(paths):
        if not monthPath:
            tMonth = tInd % len(years)
            tYear = tInd - tMonth
            raise FileNotFoundError(f'No file found for year {years[tYear]}, month {tMonth+1}')
        with nc.Dataset(monthPath, 'r') as monthData:
            monthVar = monthData.variables[variable][:]
            if subset is not None:
                monthVar = monthVar[subset]

            if landWeight:
                monthVar
            # For land masking:
            # CAM h0 files have variable LANDFRAC, which is fraction of cell covered by land. 0=ocea, 1=land
            # CLM h0 files have varibale area, whcih is in km^2. Really would like the volume of cam grid cells, but this is a decent proxy. Also avoids putting big weight on what happens in stratosphere, which nobody cares about

            try:
                meanVar += monthVar
            except NameError: # Need to initialize meanVar
                meanVar = monthVar[:]

    try:
        area = getGridArea(camRoot)
        area = area[subset] # If this line raises an index error because of different shapes, make sure the land file used corresponds with the atmosphere output
    except FileNotFoundError as e:
        log(e, 'warning')
        log('Since no area data found, will')
        area = 1 # Will do nothing when array is multiplied/divided

    meanVar *= area/np.sum(area)

    if landWeight:
        with nc.Dataset(monthPath, 'r') as camDummy:
            landFrac = camDummy.variables['LANDFRAC'][:]
        meanVar *= landFrac

    meanVar /= (12 * len(years))

    return meanVar

def query(outputPath:str, archive:bool = True, searchTerm:str|None = None, fileSpec:str|None = None,  returnPath:str|None = None):
    """
    Identifies the different types of netCDF files (e.g. <run-name>.cam.h1 or <run-name>.clm2.h0) within the output path, searching through <component>/hist subdirectories if this is the path to an archive directory. If a search term is provided, will return a list of files/variables containing that term (if any exist). If return path is specified, the output of this function is saved to a text file.

    :param outputPath: The root directory for the CESM run's output.
    :type outputPath: str
    :param archive: Whether this is an archive directory (query will search for outputPath/<component>/hist/*.nc files) or not (query will search for outputPath/*.nc files)
    :type archive: bool, optional
    :param searchTerm: A string (can be a regex string) which the variable names and descriptions of all relevant output files will be searched for. Default is None, so all files/variables are returned. Still helpful because they are neatly organized.
    :type searchTerm: str or None, optional
    :param fileSpec: A string which must be contained in the file names returned. Common use case is fileSpec='.clm2.' or '.h1.' or '.cam.h0.'. Default is None, which uses *.
    :type fileSpec: str or None, optional
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
                returnDir = os.path.dirname(returnFile)
                if returnDir: # Meaning return dir is not ''
                    os.makedirs(returnDir, exist_ok=True)
                
                with open(returnFile, 'a', encoding='UTF-8') as f:
                    f.write('\n' + output)
            except Exception as e:
                log(f'Saving queryOutput to file had error: {e}\nWill log output instead.')
                log(output)

    if fileSpec is None:
        fileSpec = '*'
    else:
        fileSpec = '*' + fileSpec + '*'

    # Get list of all the potentially relevant files
    if archive:
        allFiles = glob.glob(os.path.join(outputPath, '*', 'hist', f'{fileSpec}.nc'), recursive=True) # Assumes outputPath/<component>/hist/<fname>.nc structure
    else:
        allFiles = glob.glob(f'{fileSpec}.nc', root_dir=outputPath) # Assumes outputPath/<fname>.nc structure

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

            if len(files) > 5:
                reportedFiles = files[:3] + ['...'] + [files[-1]]
            else:
                reportedFiles = files

            queryOutput(f'\nThe files:\n{reportedFiles}\nContain the variables:\n{varsDict}\n')

if __name__ == '__main__':
    camDir = '/home/cmopfer/scratch/cesm/output/archive/NdgParams_Ctrl/atm/hist'
    cam_annual_mean(camDir)
