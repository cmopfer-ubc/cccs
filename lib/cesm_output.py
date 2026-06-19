"""
Created: Camden Opfer, March 2026

A collection of scripts to do basic aggregation and analysis of CESM output
"""
# TODO Make function that ensures y, m, d, s inputs are strings of the required length
# TODO See task in avg()

# Imports for typing
from os import environ as _environ
from numpy import ndarray as _ndarray

_ncoOutputRoot = f'/scratch/{_environ['USER']}/nco'
_componentToDir = {'cam': 'atm', 'clm2': 'lnd', 'mosart': 'rof', 'pop': 'ocn'} # TODO Add more components as needed. Maybe even more options of models that run for the same component (e.g. do pop and mom have differently named output files?)
_latNames = ['lat', 'TLAT', 'ULAT', 'doma_lat', 'slat']

def fileSpec(case:str|None=None, component:str|None = None, ftype:str|None = None, years:list[str]|None=None, months:list[str]|None=None, days:list[str]|None=None, seconds:list[str]|None=None) -> tuple[str]:
    """
    TODO
    """
    from itertools import product

    ## Handle basic inputs
    if case is None:
        case = '*'

    if component is None:
        component = '*'

    if ftype is None:
        ftypes = ['i.', 'h?.']
    else:
        ftypes = [ftype]

    ## Handle time
    if years is None:
        years = ['????'] # Regex that will allow all years to be found
    else:
        for year in years:
            if not isinstance(year, str) or len(year) != 4:
                raise ValueError(f'Year value {year} is invalid. Must be string with length 4')
    if months is None:
        months = ['??'] # Regex that will allow all months to be found
    else:
        for month in months:
            if not isinstance(month, str) or len(month) != 2:
                raise ValueError(f'Year value {month} is invalid. Must be string with length 2')
    if days is None:
        days = ['??'] # Regex that will allow all days to be found
    else:
        for day in days:
            if not isinstance(day, str) or len(day) != 2:
                raise ValueError(f'Year value {day} is invalid. Must be string with length 2')
    if seconds is None:
        seconds = ['?????']
    else:
        for second in seconds:
            if not isinstance(second, str) or len(second) != 5:
                raise ValueError(f'Year value {second} is invalid. Must be string with length 5')

    monthOpts = len(years) * len(months)
    dayOpts = len(years) * len(months) * len(days)
    secondOpts = len(years) * len(months) * len(days) * len(seconds)

    times = [''] * (monthOpts + dayOpts + secondOpts)
    i = 0
    for y, m, d, s in product(years, months, days, seconds):
        for y in years:
            times += y
            i += 1

        for y, m in product(years, months):
            times += f'{y}-{m}'
            i += 1

        for y, m, d in product(years, months, days):
            times += f'{y}-{m}-{d}'
            i += 1

        for y, m, d, s in product(years, months, days, seconds):
            times += f'{y}-{m}-{d}-{s}'
            i += 1

    ## Combine into filespecs
    fileSpecs = []
    for _ftype, time in product(ftypes, times):
        fileSpecs.append(f'{case}.{component}.{_ftype}.{time}.nc')

    return fileSpecs

def pathSpec(outputPath:str, archive:bool = True, **kwargs):
    """
    TODO
    """
    import os
    from glob import glob

    fSpecs = fileSpec(kwargs)

    if archive:
        # Assumes outputPath/<component>/hist/<fname>.nc structure
        try:
            component = kwargs['component']
        except KeyError: # component not specified in kwargs, so use '*' wildcard
            componentDir = '*'
        else: # This is executed when kwargs['component'] did NOT throw a KeyError, meaning it is specified. In this case, use that component to specify the search directory
            componentDir = _componentToDir[component]

        allFiles = []
        for fSpec in fSpecs:
            allFiles += glob(os.path.join(outputPath, componentDir, 'hist', fSpec))
    else:
        # Assumes outputPath/<fname>.nc structure
        allFiles = []
        for fSpec in fSpecs:
            allFiles += glob(os.path.join(outputPath, fSpec))

    allFiles.sort()

    return allFiles

def query(outputPath:str, archive:bool = True, searchTerm:str|None = None, returnPath:str|None = None, **kwargs):
    """
    Identifies the different types of netCDF files (e.g. <run-name>.cam.h1.<time>.nc or <run-name>.clm2.h0.<time>.nc) within the output path, searching through <component>/hist subdirectories if this is the path to an archive directory. If a search term is provided, will return a list of files/variables containing that term (if any exist). If return path is specified, the output of this function is saved to a text file.

    Keyword arguments are passed to fileSpec(), and are used to determine what subset of output files are allowable (e.g. which component they must come from, or whether they are "*.h1.*" history files). See fileSpec() for more details.

    :param outputPath: The root directory for the CESM run's output.
    :type outputPath: str
    :param archive: Whether this is an archive directory (query will search for outputPath/<component>/hist/*.nc files) or not (query will search for outputPath/*.nc files)
    :type archive: bool, optional
    :param searchTerm: A string (can be a regex string) which the variable names and descriptions of all relevant output files will be searched for. Default is None, so all files/variables are returned. Still helpful because they are neatly organized.
    :type searchTerm: str or None, optional
    :param returnPath: Path to a text file to which the output of this function will be written. Default is None, in which case cccs.utils.log will either print or log the output.
    :type returnPath: str or None, optional
    """
    import os
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

    allFiles = pathSpec(outputPath, archive, **kwargs)

    # Find files with unique forms. E.g. <run-name>.cam.h0.stuff and <run-name>.cam.h1.things are different kinds of file, but not <run-name>.cam.h0.stuff and <run-name>.cam.h0.blah
    fileTypes = {}
    for file in allFiles:
        fname = os.path.basename(file) # Get the bit after the last / (or \ if on Windows for some reason)
        compAndFtype = '.'.join(fname.split('.')[-4:-2])
        try:
            fileTypes[compAndFtype].append(file)
        except KeyError:
            fileTypes[compAndFtype] = [file]

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

def varQuery(varToContain:str, outputPath:str, archive:bool = True, **kwargs) -> list[str]:
    """
    TODO Write this

    Keyword arguments are passed to fileSpec(), and are used to determine what subset of output files are allowable (e.g. which component they must come from, or whether they are "*.h1.*" history files). See fileSpec() for more details.

    :param varToContain: The variable which the returned file(s) will contain. Must match exactly (including case-sensitivity) with the netCDF file's name.
    :type varToContain: str
    :param outputPath: The root directory for the CESM run's output.
    :type outputPath: str
    :param archive: Whether this is an archive directory (query will search for outputPath/<component>/hist/*.nc files) or not (query will search for outputPath/*.nc files)
    :type archive: bool, optional

    :return: List of paths matching the specifications, and containing the variable varToContain.
    :rtype: list[str]
    """
    import os
    import re
    import netCDF4 as nc
    from .utils import log, timedInput

    allFiles = pathSpec(outputPath, archive, **kwargs)

    # Find files with unique forms. E.g. <run-name>.cam.h0.stuff and <run-name>.cam.h1.things are different kinds of file, but not <run-name>.cam.h0.stuff and <run-name>.cam.h0.blah
    fileTypes = {}
    for file in allFiles:
        fname = os.path.basename(file)
        compAndFtype = '.'.join(fname.split('.')[-4:-2])
        try:
            fileTypes[compAndFtype].append(file)
        except KeyError:
            fileTypes[compAndFtype] = [file]

    groupedFiles = {}
    for compAndFtype, files in fileTypes.items():
        ds = nc.Dataset(files[0], 'r')
        varsDict = ds.variables

        for varName in varsDict:
            varName = str(varName)
            if re.search(varToContain, varName):
                groupedFiles[compAndFtype] = files

    if len(groupedFiles) == 0:
        log(f'Unable to find file containing variable {varToContain} in {outputPath}')
        return []

    if len(groupedFiles) > 1:
        optionsString = ''
        for i, (compAndFtype, files) in enumerate(groupedFiles.items()):
            optionsString += f'{i} Files of the form {compAndFtype}, like {files[0]}\n'
        strInput = timedInput(f'Multiple files containing relevant files found. They are:\n{optionsString}Please enter a number between 0 and {len(groupedFiles) - 1} to determine which option is used. If no input is received in 30 seconds, "0" will be chosen.', default='0', timeout=30)
        keyInd = int(strInput)

        chosenKey = list(groupedFiles.keys())[keyInd]
    else:
        chosenKey = list(groupedFiles.keys())[0]

    return groupedFiles[chosenKey]

def getPaths(outputRoot:str, archive:bool = True, component:str = 'cam', fileType:str = 'h0', years:list[str]|None=None, months:list[str]|None=None, days:list[str]|None=None, seconds:list[str]|None=None) -> tuple[list[str], str]:
    """
    Gets paths of all output files matching the type of output data and time domain to draw from specified by this functions arguments. By default, will provide the paths of all files in outputRoot/atm/hist.

    :param outputRoot: A directory with CESM output. Often of the form "/scratch/$USER/cesm/output/archive/$CASE" or, occasionally, "/scratch/$USER/cesm/output/$CASE/run".
    :type outputRoot: str
    :param archive: Whether or not outputRoot leads to an archive directory, which things like lnd/hist subdirectories contain the actual data. If True, assumes that directory structure, and looks for output files accordingly. If False, assumes all data is in outputRoot, and does not do any recursive searching.
    :type archive: bool, optional
    :param component: A string representing the model component to retrieve data from. Commonly will be 'cam', 'clm2', or maybe 'mosart' or 'pop'.
    :type component: str, optional
    :param fileType: Which type of output file for this component to search for. Typically 'h0', maybe 'h1', occasionally 'h2'-'h9' or 'i'. Default is 'h0', which often corresponds to monthly output.
    :type fileType: str, optional
    :param year: A list of strings representing the years from which to get output. Each string must have four numerical characters (e.g. '0001') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type year: list[str] or None, optional
    :param month: A list of strings representing the months from which to get output. Each string must have two numerical characters (e.g. '01') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type month: list[str] or None, optional
    :param day: A list of strings representing the days from which to get output. Each string must have two numerical characters (e.g. '01') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type day: list[str] or None, optional
    :param second: A list of strings representing the seconds from which to get output. Each string must have five numerical characters (e.g. '00000') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type second: list[str] or None, optional

    :return: A list containing all the relevant paths found
    :rtype: list[str]
    """
    import os
    import warnings
    from itertools import product
    from .utils import log

    if component not in _componentToDir:
        raise ValueError(f'Invalid argument {component} for component in getPaths. Must be one of {_componentToDir.keys()}')
    if fileType not in list(f'h{i}' for i in range(10)) and fileType != 'i':
        raise ValueError(f'Invalid argument {fileType} for fileType in getPaths. Must be one of {list(f'h{i}' for i in range(10))} or i')

    if archive:
        dataRoot = os.path.join(outputRoot, _componentToDir[component], 'hist')
    else:
        dataRoot = outputRoot

    partialFile = os.path.join(dataRoot, f'*.{component}.{fileType}.')

    if years is None:
        years = ['????'] # Regex that will allow all years to be found
    if months is None:
        months = ['??'] # Regex that will allow all months to be found
    if days is None:
        days = ['??'] # Regex that will allow all days to be found
    if seconds is None:
        seconds = ['?????'] # Regex that will allow all seconds to be found

    if os.path.exists(f'{partialFile}{years[0]}.nc'):
        frequencyPrecision = 'year'
        fileSpecs = [partialFile] * len(years)
        for i, y in enumerate(years):
            fileSpecs[i] += f'{y}.nc'

    elif os.path.exists(f'{partialFile}{years[0]}-{months[0]}.nc'):
        frequencyPrecision = 'month'
        fileSpecs = [partialFile] * (len(years) * len(months))
        for i, (y, m) in enumerate(product(years, months)):
            fileSpecs[i] += f'{y}-{m}.nc'

    elif os.path.exists(f'{partialFile}{years[0]}-{months[0]}-{days[0]}.nc'):
        frequencyPrecision = 'day'
        fileSpecs = [partialFile] * (len(years) * len(months) * len(days))
        for i, (y, m, d) in enumerate(product(years, months, days)):
            fileSpecs[i] += f'{y}-{m}-{d}.nc'

    elif os.path.exists(f'{partialFile}{years[0]}-{months[0]}-{days[0]}.nc'):
        frequencyPrecision = 'second'
        fileSpecs = [partialFile] * (len(years) * len(months) * len(days) * len(seconds))
        for i, (y, m, d, s) in enumerate(product(years, months, days, seconds)):
            fileSpecs[i] += f'{y}-{m}-{d}-{s}.nc'

    else:
        raise FileNotFoundError(f'Unable to find file starting with {partialFile} with an ending matching time parameters years={years}, months={months}, days={days}, and seconds={seconds}.')

    validFiles = [] # Can't pre-allocate in case regex wildcards lead to multiple hits
    missingFiles = []
    for fileSpec in fileSpecs:
        if os.path.exists(fileSpec):
            validFiles += fileSpec
        else:
            missingFiles += fileSpec
    if missingFiles:
        warnings.warn(f'Expected to find files {missingFiles}, but they do not exist.', UserWarning)

    if 'h' not in fileType:
        frequencyPrecision = 'instantaneous'
    log(f'getPaths found {len(validFiles)} paths in {outputRoot} matching the specifications.')

    return validFiles, frequencyPrecision

def findRelated(baseFile:str, component:str = 'cam', fileType:str = '*') -> list[str]|None:
    """
    Finds a sample file from the specified component based on relative paths to baseFile or metadata contained within basefile. In the case where files from metadata are used, this function is recursive

    :param baseFile: The file whose "cousin" this function will search for.
    :type baseFile: str
    :param component: The CESM component tag to search for in file names. Should be one of the keys of _componentToDir (cam, clm2, mosart, etc.). Default is cam.
    :type component: str, optional
    :param fileType: Which type of output file for this component to search for. Typically 'h0', maybe 'h1', occasionally 'h2'-'h9' or 'i'. Default is '*', in which case the returned list will have one element for each found fileType.
    :type fileType: str, optional

    :return: Either a list of strings representing the paths to relvent files (each with unique fileTypes, so only will have len > 1 if fileType == *) or None if no relevant files are found.
    :rtype: list[str] or None
    """
    import re
    import os
    from glob import glob
    from copy import copy
    import netCDF4 as nc

    def makeOutput(relatedFiles:list):
        if fileType != '*':
            return [relatedFiles[0]]

        outFiles = []
        outFileTypes = []
        for relatedFile in relatedFiles:
            currentFileType = relatedFile.split('.')[-3]
            if currentFileType not in outFileTypes:
                outFileTypes.append(currentFileType)
                outFiles.append(relatedFile)

    if component not in _componentToDir:
        raise ValueError(f'Unknown CESM component {component} in findRelated().')
    if fileType not in list(f'h{i}' for i in range(10)) and fileType != 'i' and fileType != '*':
        raise ValueError(f'Invalid argument {fileType} for fileType in findRelated(). Must be one of {list(f'h{i}' for i in range(10))} or i or *')

    if re.match(f'*.{component}.{fileType}.*.nc', baseFile):
        return makeOutput(baseFile)

    baseDir = os.path.dirname(baseFile)

    # Assume archive-style directory structure
    searchPattern = os.path.join(baseDir, '..', '..', _componentToDir[compile], 'hist', f'*.{component}.{fileType}.*.nc')
    relatedFiles = glob(searchPattern)

    if relatedFiles:
        return makeOutput(relatedFiles)

    # Assume all data in the same directory
    relatedFiles = glob(os.path.join(baseDir, f'*.{component}.{fileType}.*.nc'))
    if relatedFiles:
        return makeOutput(relatedFiles)

    # Try metadata within baseFile. Typical when baseFile was generated with an NCO tool.
    with nc.Dataset(baseFile, 'r') as baseDs:
        hist = copy(baseDs.history)

    if not isinstance(hist, str) or '.nc' not in hist: # hist is not helpful. The "'.nc' not in hist" check is only carried out if the first fails (meaning hist is a str), so that shouldn't throw any errors
        return

    hist = hist.split(' ')
    for histElement in hist:
        if histElement[-3:] != '.nc':
            pass

        # # This is commented out because if avoids the case where histElement is in a directory with other valid fileTypes and the fileType argument is '*'
        # if re.match(f'*.{component}.{fileType}.*.nc', histElement):
        #     return makeOutput([histElement])

        relatedFiles = findRelated(histElement, component, fileType)
        if relatedFiles:
            return relatedFiles # No need to ensure list format, since this was returned recursively

    return

def ncoPath(cesmOutRoot:str, component:str = 'cam', years:list[str]|None=None, months:list[str]|None=None, days:list[str]|None=None, seconds:list[str]|None=None, ncoOutputRoot:str=_ncoOutputRoot, operation:str|None=None):
    """
    TODO
    """
    import os
    import numpy as np

    if component not in _componentToDir:
        raise ValueError(f'Unknown CESM component {component} in ncoPath().')

    cesmOutName = os.path.basename(os.path.normpath(cesmOutRoot)) # normpath gets rid of any extra '/' at the end. Overall, this usually makes outputName = $CASE
    ncoFile = f'{component}'

    if operation is not None:
        ncoFile += f'_{operation}'

    # Make a "hash" representing the time arguments. TODO Make this actually guarantee uniqueness for any unique category of inputs. Not sure how many digits that would require though?!?
    timeVal = 0
    if years:
        timeVal += np.sum(np.array(years) * 365 * 24 * 3600)
    if months:
        timeVal += np.sum(np.array(months) * 30 * 24 * 3600)
    if days:
        timeVal += np.sum(np.array(days) * 24 * 3600)
    if seconds:
        timeVal += np.sum(seconds)
    ncoFile += '_' + hex(timeVal)[2:].zfill(8)

    ncoFile += '.nc'
    return os.path.join(ncoOutputRoot, 'ncra', cesmOutName, ncoFile)

def avgOverTime(cesmOutRoot:str, archive:bool = True, varNames:list[str]|None=None, component:str = 'cam', fileType:str = 'h0', years:list[str]|None=None, months:list[str]|None=None, days:list[str]|None=None, seconds:list[str]|None = None, ncoOutputRoot:str|None = None, operation:str|None = None) -> str:
    """
    Uses getPaths() to find paths corresponding to a time period and then uses nco.ncra to place an average over them in a file specified by ncoPath(). If the averaged file corresponding to the provided cesmOutRoot, component, and time arguments already exists, variables which do not yet have data are appended to the file, while others are skipped for speed. Returns the path to the netCDF file containing the relevant data.

    :param cesmOutRoot: A directory with CESM output. Often of the form "/scratch/$USER/cesm/output/archive/$CASE" or, occasionally, "/scratch/$USER/cesm/output/$CASE/run".
    :type cesmOutRoot: str
    :param archive: Whether or not cesmOutRoot leads to an archive directory, which things like lnd/hist subdirectories contain the actual data. If True, assumes that directory structure, and looks for output files accordingly. If False, assumes all data is in cesmOutRoot, and does not do any recursive searching.
    :type archive: bool, optional
    :param varNames: A list containing the subset of variables from the CESM output to include in the output. Default is None, in which case all variables are averaged.
    :type varNames: list[str] or None, optional
    :param component: A string representing the model component to retrieve data from. Commonly will be 'cam', 'clm2', or maybe 'mosart' or 'pop'.
    :type component: str, optional
    :param fileType: Which type of output file for this component to search for. Typically 'h0', maybe 'h1', occasionally 'h2'-'h9' or 'i'. Default is 'h0' because it is most likely to exist. The type 'h0' corresponds to monthly output unless the CESM namelist for component was altered.
    :type fileType: str, optional
    :param years: A list of strings representing the years from which to get output. Each string must have four numerical characters (e.g. '0001') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type years: list[str] or None, optional
    :param months: A list of strings representing the months from which to get output. Each string must have two numerical characters (e.g. '01') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type months: list[str] or None, optional
    :param days: A list of strings representing the days from which to get output. Each string must have two numerical characters (e.g. '01') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type days: list[str] or None, optional
    :param seconds: A list of strings representing the seconds from which to get output. Each string must have five numerical characters (e.g. '000000') or be some regular expression that will evaluate in that way. Default is None, which will grab all data.
    :type seconds: list[str] or None, optional
    :param ncoOutputRoot: The root directory to which the output from NCO operations (like ncra here) should be written. Should be consistent between uses so that this and related functions can find output. Default is None, which uses _ncoOutputRoot, which in turn is set above to be /scratch/$USER/nco.
    :type ncoOutputRoot: str or None, optional
    :param operation: The operation argument to be passed to NCO's ncra. Must be one of 'avg', 'sqravg', 'avgsqr', 'max', 'min', 'mabs', 'mebs', 'mibs', 'rms', 'rmssdn', 'sqrt', 'tabs', and 'ttl', or None. Default is None, in which case ncra performs an arithmetic average (same as passing 'avg').
    :type operation: str or None, optional

    :return: String representing the path to the averaged data
    :rtype: str
    """
    import os
    import numpy as np
    from nco import Nco

    if component not in _componentToDir:
        raise ValueError(f'Unknown CESM component {component} in avgOverTime().')
    if ncoOutputRoot is None:
        ncoOutputRoot = _ncoOutputRoot
    if operation is None:
        operation = 'avg' # Explicitly set so that the ncoPath reflects that this is using ncra

    ncoOutFile = ncoPath(cesmOutRoot, component, years, months, days, seconds, ncoOutputRoot, operation)

    if not os.path.exists(ncoOutFile):
        cesmOutFiles, dataFrequency = getPaths(cesmOutRoot, archive, component, fileType, years, months, days, seconds)

        ncoOptions = ['-A'] # -A = append, so will add any variables that don't exist in ncoOutFile, but otherwise leave it be
        ncoKwargs = {}
        if varNames is not None:
            ncoKwargs['variable'] = ','.join(varNames) # Join will turn a list like ['U','V','T'] into a string like 'U,V,T' as required by the NCO CLI
        if operation in ['avg', 'sqravg', 'avgsqr', 'max', 'min', 'mabs', 'mebs', 'mibs', 'rms', 'rmssdn', 'sqrt', 'tabs', 'ttl']:
            ncoKwargs['operation'] = operation
        else:
            raise ValueError

        if dataFrequency == 'month':
            # NOTE Ignores leap years, though CESM usually does too
            if months is None:
                monthWeights = '31,28,31,30,31,30,31,31,30,31,30,31'
            else:
                monthLengths = np.array(['na','31','28','31','30','31','30','31','31','30','31','30','31']) # Assumes Jan=1, Dec=12 (as required by months argument anyway)
                relevantMonthLengths = monthLengths[months]
                monthWeights = ','.join(relevantMonthLengths.tolist())

            ncoKwargs['weight'] = monthWeights

        nco = Nco()
        nco.ncra(input=cesmOutFiles, output=ncoOutFile, options=ncoOptions, use_shell=True, **ncoKwargs)

    return ncoOutFile

def avgOverDims(dataFile:str, varAveraged:str, dimNames:list[str]|None = None, landWeight = True) -> _ndarray:
    """
    Identifies if provided dimNames correspond to dimensions of the provided data and, if so, takes an average along those dimensions. By default, takes the average in all dimensions. More useful cases for this function would be avgOverDims(x, ['time']), avgOverDims(y, ['lat', 'lon']), or avgOverDims(z, ['lev']).

    This function does NOT modify the NetCDF file from which ncVar is derived, even if write mode is on. That would require something like myNcVar[:] = avgOverDim(myNcVar), though you'd also want to delete the metadata for the removed dimensions.

    :param dataFile: Path to the file from which data will be derived.
    :type dataFile: str
    :param varAveraged: The variable to be averaged. Must be included as a variable in fPath.
    :type varAveraged: str
    :param dimNames: A list of strings. If any of the strings matches the name of a dimension of ncVar, that dimension will be averaged across. If an element of dimNames is not a dimension of ncVar, it will be silently skipped. By default, does not take any averages.
    :type dimNames: list[str] or None, optional
    :param landWeight: A boolean determining whether or not to weight the average by the amount of land in each grid cell. Default is True, so the average will be weighted.
    :type landWeight: bool, optional

    :return: Numpy array with data averaged and flattened across the specified dimension(s)
    :rtype: np.ndarray
    """
    import warnings
    import numpy as np
    import netCDF4 as nc
    from .utils import log

    def getNcVar(ds, varName):
        """"
        Tries to get the data from the provided dataset. If that fails, finds a related CESM dataset to use.
        """
        try:
            return ds.variables[varName]
        except KeyError:
            log(f'Variable {varName} not found by avgOverDims() in provided dataset. Will check for it in related CESM output.', 'debug')

        for component in _componentToDir:
            relatedFiles = findRelated(dataFile, component)

            for file in relatedFiles:
                with nc.Dataset(file, 'r') as ds:
                    try:
                        ds.variables[varName]
                    except KeyError:
                        continue # Moves on to the next file in relatedFiles
                return file # Did not move on, so this dataset has the variable varName. Return it

        # Unable to locate this variable
        warnings.warn(f'Variable {varName} not found in the provided dataset, and unable to fetch it from a related CESM output. avgOverDims will skip weighting by {varName}.')
        return 1

    def getSingleWeight(ds, varName):
        """
        Applies relevant functions to variables so they can be used to weight data.
        """
        if varName == 'lev':
            # Weight by (Delta P)/g
            ilev = ds.variables['ilev'][:] # Has one more element than lev, making difference easier
            out = ilev[1:] - ilev[:-1] # TODO Confirm that this is indexed corretly to result in an all-positive out

        elif varName == 'lev':
            # Weight by (Delta P)/g
            lev = ds.variables['lev'][:] # Has one less element than ilev, but still useful since it's spatially the half-way points
            diff = lev[1:] - lev[:-1]
            out = np.array([diff[0] + diff.tolist(), diff[-1]])

        else:
            out = getNcVar(ds, varName)

        if varName in _latNames:
            out = np.cos(np.deg2rad(out))

        out /= np.nanmean(out)
        return out

    def getWeights(dataPath:str, outShape:tuple[int], varDimsToNames:dict[int:str]) -> _ndarray|int:
        """
        Gets the variable given by varNames (or all the elements of the list varNames) from a relevant CESM output file for use in weighting. Could fail if no file is found containing the needed variable.
        """
        if not varDimsToNames:
            # Factor to mutliply is 1 since no weighting is being done
            return 1

        weightFactor = np.ones(outShape)
        for varDim, varName in varDimsToNames.items():
            var = getSingleWeight(dataPath, varName) # Will be 1D array with shape (outShape[i], )
            inds = (..., ) + (None, ) * (len(outShape) - varDim - 1) # Indexing by inds will empty axes extending to last dim of weightFactor. So shape will be (outShape[i], 1, 1, ..., 1). See Numpy docs on broadcasting: https://numpy.org/doc/stable/reference/arrays.nditer.html#broadcasting-array-iteration
            weightFactor *= var[inds]

        log(f'Retrieved weight factors {varDimsToNames.values()}', 'debug')
        return weightFactor/np.sum(weightFactor)

    with nc.Dataset(dataFile, 'r') as data:
        ncVar = data.variables[varAveraged]
        raw = ncVar[:]
        actualDimNames = [dim.name for dim in ncVar.get_dims()]

    if dimNames is None:
        dimNames = []

    possibleFactorVars = _latNames + ['lev', 'ilev']
    factorVars = {}
    matchingDims = []
    dimsToAvgOver = tuple()

    for dimName in dimNames:
        try:
            dimInd = actualDimNames.index(dimName)
        except ValueError: # This variable does not have dimension dimName
            continue # Skip to next dimName
        matchingDims += [dimName]
        dimsToAvgOver = dimsToAvgOver + (dimInd,)

        if dimName in possibleFactorVars:
            factorVars[dimInd] = dimName

    if landWeight and ('lat' not in dimsToAvgOver or 'lon' not in dimsToAvgOver):
        log('Not averaging over both latitude and longitude, so it does not make sense to apply land fraction weighting. avgOverDims will ignore landWeight = True argument.')
        landWeight = False

    if landWeight:
        try:
            latDim = actualDimNames.index('lat') # Must be lat/lon in particular (rather than other things in _latNames, for example) since those are the dimensions of landfrac and LANDFRAC
            lonDim = actualDimNames.index('lon')
        except ValueError:
            log('Unable to apply land weighting because one of lat and lon are not dimensions of the provided variable', 'warning')
        lastDim = max(latDim, lonDim) # So that empty dims are added after the LANDFRAC mask
        if '.clm2.' in dataFile:
            factorVars[lastDim] = 'landfrac'
        else:
            factorVars[lastDim] = 'LANDFRAC' # This is the relevant cam variable. getNcVar() will fetch related CAM data if dataFile is not CAM data itself

    log(f'avgOverDims found the following dimensions to average over: {matchingDims}', 'debug')
    log(f'A weighted average will be taken over {factorVars.values()}', 'debug')

    weights = getWeights(dataFile, raw.shape, factorVars)
    raw *= weights

    if dimsToAvgOver:
        averagedArr = np.nanmean(raw, axis=dimsToAvgOver)
    else: # If no matching dims found, will not perform a mean
        averagedArr = raw

    averagedArr = np.squeeze(averagedArr)

    return averagedArr

def avg(varAveraged: str, dimsAveragedOver: list[str], cesmOutRoot:str, archive:bool = True, yearRange:tuple[int]|None = None, landWeight:bool = True):
    """
    Combines avgOverTime() and avgOverDims() to allow for averaging over both time and other dimensions. Loses some of the customizability of the other functions (e.g. by requiring a range of years rather than allowing for a list), but this should make it simpler to use.
    """
    import os
    import re
    from glob import glob
    import netCDF4 as nc

    component, fileType = 1, 2 # TODO Use query to find component and fileType. Maybe use this in avgOverDims too? Could use something like timedInput from IATEM data management to resolve having multiple hits (as in, same variable recorded in cam.h0 and cam.h1 files or in cam.h0 and clm2.h0)

    averagedFile = avgOverTime(cesmOutRoot, archive, [varAveraged], component, fileType, years = list[range(yearRange[0], yearRange[1])])

    averagedData = avgOverDims(averagedFile, varAveraged, dimsAveragedOver, landWeight)

    return averagedData
