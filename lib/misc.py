"""
Created: Camden Opfer, June 2025
"""

import numpy as np
from pyproj import Proj, Transformer

def reproject(xIn:np.ndarray, yIn:np.ndarray, projTypeIn:str='utm', projTypeOut:str='latlong', datum:str='WGS84', utmZone:int=24):
    """
    Converts coordinates between two projections.
    
    The projTypeIn and projTypeOut arguments are fed to the pyproj.Proj class, which only accepts particular string values like 'latlong', 'utm', or 'EPSG:<four digit code>'.

    :param xIn: The starting x/longitude grid.
    :type xIn: np.ndarray
    :param yIn: The starting y/latitude grid.
    :type yIn: np.ndarray
    :param projTypeIn: The projection of the input data. Must be a valid option for the pyproj.Proj class. Default is utm.
    :type projTypeIn: str, optional
    :param projTypeOut: The projection for the out data to be transformed into. Must be a valid option for the pyproj.Proj class. Default is latitude/longitude (keyword 'latlong').
    :type projTypeOut: str, optional
    :param utmZone: If one of the projTypes is 'utm', this zone is applied to it. Converting between two utm zones would require slight editing of this function, but is unlikely to be useful.
    :type utmZone: int
    """
    if projTypeIn == 'utm':
        projIn = Proj(proj=projTypeIn, datum=datum, zone=utmZone)
    elif isinstance(projTypeIn, str) and 'EPSG' not in projTypeIn:
        projIn = Proj(proj=projTypeIn, datum=datum)
    else:
        projIn = Proj(projTypeIn, datum=datum)

    if projTypeOut == 'utm':
        projOut = Proj(proj=projTypeOut, datum=datum, zone=utmZone)
    elif isinstance(projTypeOut, str) and 'EPSG' not in projTypeOut:
        projOut = Proj(proj=projTypeOut, datum=datum)
    else:
        projOut = Proj(projTypeOut)

    transformer = Transformer.from_proj(projIn, projOut) # create a transformer object to convert from lat/lon to UTM
    xout, yOut = transformer.transform(xIn, yIn) # convert the coordinates

    return xout, yOut
