"""
Created: Camden Opfer, March 2026

A collection of scripts to do basic aggregation and analysis of CESM output
"""
# Imports for typing
from numpy import ndarray as _ndarray

_componentToDir = {'cam': 'atm', 'clm2': 'lnd', 'mosart': 'rof', 'pop': 'ocn'} # TODO Add more components as needed. Maybe even more options of models that run for the same component (e.g. do pop and mom have differently named output files?)

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
    import os
    import glob
    import re
    import netCDF4 as nc
    from .utils import log

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
        allFiles = glob.glob(os.path.join(outputPath, f'{fileSpec}.nc')) # Assumes outputPath/<fname>.nc structure

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

def getPaths(outputRoot:str, archive:bool = True, component:str = 'cam', fileHVal:str|None = None, year:list[str]|None=None, month:list[str]|None=None, day:list[str]|None=None, second:list[str]|None=None) -> list[str]:
    """
    Gets paths of all output files matching the type of output data and time domain to draw from specified by this functions arguments. By default, will provide the paths of all files in outputRoot/atm/hist.

    :param outputRoot: A directory with CESM output. Often of the form "/scratch/$USER/cesm/output/archive/$CASE" or, occasionally, "/scratch/$USER/cesm/output/$CASE/run".
    :type outputRoot: str
    :param archive: Whether or not outputRoot leads to an archive directory, which things like lnd/hist subdirectories contain the actual data. If True, assumes that directory structure, and looks for output files accordingly. If False, assumes all data is in outputRoot, and does not do any recursive searching.
    :type archive: bool, optional
    :param component: A string representing the model component to retrieve data from. Commonly will be 'cam', 'clm2', or maybe 'mosart' or 'pop'.
    :type component: str, optional
    :param fileHVal: Which of the (at most 10) output files for this component to search for. Typically '0', maybe '1', occasionally '2'-'9'. Default is None, which will grab all data.
    :type fileHVal: str or None, optional
    :param year: A list of strings representing the years from which to get output. Each string must have four numerical characters (e.g. '0001') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type year: list[str] or None, optional
    :param month: A list of strings representing the months from which to get output. Each string must have two numerical characters (e.g. '01') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type month: list[str] or None, optional
    :param day: A list of strings representing the days from which to get output. Each string must have two numerical characters (e.g. '01') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type day: list[str] or None, optional
    :param second: A list of strings representing the seconds from which to get output. Each string must have five numerical characters (e.g. '000000') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type second: list[str] or None, optional

    :return: A list containing all the relevant paths found
    :rtype: list[str]
    """
    import os
    import glob
    from itertools import product
    from .utils import log

    if component not in _componentToDir:
        raise ValueError(f'Invalid argument {component} for component in getPaths. Must be one of {_componentToDir.keys()}')
    if fileHVal not in list(str(i) for i in range(10)) and fileHVal is not None:
        raise ValueError(f'Invalid argument {fileHVal} for fileHVal in getPaths. Must be one of {list(str(i) for i in range(10))} or None')

    if archive:
        dataRoot = os.path.join(outputRoot, _componentToDir[component], 'hist')
    else:
        dataRoot = outputRoot

    if year is None:
        year = ['*'] # Regex that will allow all years to be found
    if month is None:
        month = ['*'] # Regex that will allow all months to be found
    if day is None:
        day = ['*'] # Regex that will allow all days to be found
    if second is None:
        second = ['*'] # Regex that will allow all seconds to be found
    timeOptCount = len(year) * len(month) * len(day) * len(second)

    if fileHVal is None:
        fileHVal = '?' # Regex that will allow any single character. These files can be numbered 0 through 9 so, effectively, this grabs all output files from this component.

    fileSpecs = ['*' + '.' + component + '.' + fileHVal + '.'] * timeOptCount * 2
    for i, (y, m, d, s) in enumerate(product(year, month, day, second)): # product iterates over all combinations of the provided lists
        fileSpecs[2*i] += y + '-' + m + '-' + d + '-' + s # Used by CESM when output frequency is high enough
        fileSpecs[2*i+1] += y + '-' + m # Used by CESM when output frequency is low enough

    allFiles = [] # Can't pre-allocate in case wildcards (*'s) lead to multiple hits
    for fileSpec in fileSpecs:
        allFiles += glob.glob(os.path.join(dataRoot, f'{fileSpec}.nc'))

    allFiles.sort()

    log(f'getPaths found {len(allFiles)} paths in {outputRoot} matching the specifications.')

    return allFiles

def avgOverDims(dataFile:str, varName:str, dimNames:list[str]|None=None, landWeight=True) -> tuple[_ndarray, int]:
    """
    Identifies if provided dimNames correspond to dimensions of the provided data and, if so, takes an average along those dimensions. By default, takes the average in all dimensions. More useful cases for this function would be avgOverDims(x, ['time']), avgOverDims(y, ['lat', 'lon']), or avgOverDims(z, ['lev']).

    This function does NOT modify the NetCDF file from which ncVar is derived, even if write mode is on. That would require something like myNcVar[:] = avgOverDim(myNcVar), though you'd also want to delete the metadata for the removed dimensions.

    :param fPath: Path to the file from which data will be derived.
    :type fPath: str
    :param varName: The variable to be averaged. Must be included as a variable in fPath.
    :type varName: str
    :param dimNames: A list of strings. If any of the strings matches the name of a dimension of ncVar, that dimension will be averaged across. If an element of dimNames is not a dimension of ncVar, it will be silently skipped. By default, averages over all dimensions.
    :type dimNames: list[str] or None, optional
    :param landWeight: A boolean determining whether or not to weight the average by the amount of land in each grid cell. Default is True, so the average will be weighted.
    :type landWeight: bool, optional

    :return: Numpy array with data averaged and flattened across the specified dimension(s)
    :rtype: np.ndarray
    """
    import os
    import glob
    import numpy as np
    import netCDF4 as nc
    from .utils import log

    outputBase = os.path.basename(dataFile)

    def findCamDummy():
        """"
        I found the Cam dummy! He's writing this code.

        Get it? Because my name is Camden! Hahaha
        """
        # Assume archive-style directory structure
        camPattern = os.path.join(outputBase, '..', '..', 'atm', 'hist', '*.cam.h0.*.nc')
        camFiles = glob.glob(camPattern)

        if not camFiles: # Archive-style search was unsuccessful
            # Assume all data in the same directory
            camFiles = glob.glob(os.path.join(outputBase, '*.cam.h0.*.nc'))

        if not camFiles:
            # Everything failed. Expect the function calling this to catch it and raise a warning
            return

        return camFiles[0]

    def getWeightVar(ds, name):
        """
        Applies relevant functions to variables so they can be used to weight data.
        """
        if name == 'lev':
            # Weight by (Delta P)/g
            ilev = ds.variables['ilev'][:] # Has one more element than lev, making difference easier
            out = ilev[1:] - ilev[:-1] # TODO Confirm that this is indexed corretly to result in an all-positive out

        elif name == 'lev':
            # Weight by (Delta P)/g
            lev = ds.variables['lev'][:] # Has one less element than ilev, but still useful since it's spatially the half-way points
            diff = lev[1:] - lev[:-1]
            out = np.array([diff[0] + diff.tolist(), diff[-1]])

        else:
            out = ds.variables[name]

        if name == 'lat':
            out = np.cos(np.deg2rad(out))

        out /= np.nanmean(out)
        return out

    def getFromCamDummy(outShape:tuple[int], varDimsToNames:dict[int:str]):
        """
        Gets the variable given by varNames (or all the elements of the list varNames) from a cam output file for use in weighting. Could fail if h0 files don't have this variable, or if avgOverDims was pointed towards an outputBase without cam output in a typical relative location.
        """
        if not varDimsToNames:
            # Factor to mutliply is 1 since no weighting is being done
            return 1

        camPath = findCamDummy()

        if camPath is None:
            log(f'Unable to find CAM data in {outputBase} or {os.path.join(outputBase, '..', '..', 'atm', 'hist')}. Will not do any weighting by {varDimsToNames.values()}', 'warning')
            return 1

        weightFactor = np.ones(outShape)
        with nc.Dataset(camPath, 'r') as camDummy:
            for varDim, varName in varDimsToNames.items():
                var = getWeightVar(camDummy, varName) # Will be 1D array with shape (outShape[i], )
                inds = (..., ) + (None, ) * (len(outShape) - varDim - 1) # Indexing by inds will empty axes extending to last dim of weightFactor. So shape will be (outShape[i], 1, 1, ..., 1). See Numpy docs on broadcasting: https://numpy.org/doc/stable/reference/arrays.nditer.html#broadcasting-array-iteration
                weightFactor *= var[inds]

        log(f'Retrieved {varDimsToNames.values()} from atmospheric data in {camPath}', 'debug')
        return weightFactor/np.sum(weightFactor)

    if dimNames is None:
        dimNames = [] # TODO Differentiate between differentiating over everything and nothing

    with nc.Dataset(dataFile, 'r') as data:
        ncVar = data.variables[varName]
        raw = ncVar[:]
        actualDimNames = [dim.name for dim in ncVar.get_dims()]

    possibleFactorVars = ['lat', 'lev', 'ilev'] # TODO Allow for CLM and other input, where lat is named differently
    factorVars = {}
    matchingDims = []

    for dimName in dimNames:
        try:
            dimInd = actualDimNames.index(dimName)
        except ValueError: # This variable does not have dimension dimName
            continue # Skip to next dimName
        matchingDims += [dimName]
        dimsToAvgOver = dimsToAvgOver + (dimInd,)

        if dimName in possibleFactorVars:
            factorVars[dimInd] = dimName

    if landWeight:
        try:
            latDim = actualDimNames.index('lat') # TODO Allow for CLM and other input, where lat/lon are named differently
            lonDim = actualDimNames.index('lon')
        except ValueError:
            log('Unable to apply land weighting because one of lat and lon are not dimensions of the provided variable', 'warning')
        lastDim = max(latDim, lonDim) # So that empty dims are added after the LANDFRAC mask
        factorVars[lastDim] = 'LANDFRAC'

    log(f'avgOverDims found the following dimensions to average over: {matchingDims}', 'debug')
    log(f'A weighted average will be taken over {factorVars}', 'debug')

    weights = getFromCamDummy(raw.shape, factorVars)
    raw *= weights

    averagedArr = np.nanmean(raw[:], axis=dimsToAvgOver)

    averagedArr = np.squeeze(averagedArr)

    return averagedArr
