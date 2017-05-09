import math
from datetime import datetime
from itertools import groupby
import xarray as xr
import os


def create_geographic_chunks(longitude=None, latitude=None, geographic_chunk_size=0.5):
    """Chunk a parameter set defined by latitude, longitude, and a list of acquisitions.

    Process the lat/lon/time parameters defined for loading Data Cube Data - these should be
    produced by dc.list_acquisition_dates

    Args:
        latitude: Latitude range to split
        longitude: Longitude range to split

    Returns:
        A zip formatted list of dicts containing longitude, latitude that can be used to update params

    """

    assert latitude and longitude, "Longitude and latitude are both required kwargs."

    square_area = (latitude[1] - latitude[0]) * (longitude[1] - longitude[0])
    geographic_chunks = math.ceil(square_area / geographic_chunk_size)

    #we're splitting accross latitudes and not longitudes
    #this can be a fp value, no issue there.
    latitude_chunk_size = (latitude[1] - latitude[0]) / geographic_chunks
    latitude_ranges = [(latitude[0] + latitude_chunk_size * chunk_number,
                        latitude[0] + latitude_chunk_size * (chunk_number + 1))
                       for chunk_number in range(geographic_chunks)]
    longitude_ranges = [longitude for __ in latitude_ranges]

    return [{'longitude': pair[0], 'latitude': pair[1]} for pair in zip(longitude_ranges, latitude_ranges)]


def combine_geographic_chunks(chunks):
    """Combine a group of chunks generated by create_geographic_chunks

    Combines chunks, eliminating duplicates using combine first. reindexes
    on all dims to ensure that the resulting dataset is identical to what
    would be generated in a single monolithic load.

    Args:
        Chunks: array of xarray datasets to combine

    Returns:
        Xarray representing the combined product.
    """

    combined_chunks = None
    for chunk in chunks:
        if combined_chunks is None:
            combined_chunks = chunk
            continue
        combined_chunks = combined_chunks.combine_first(chunk)
    indices = {
        'latitude': sorted(combined_chunks.latitude.values, reverse=True),
        'longitude': sorted(combined_chunks.longitude.values)
    }
    if 'time' in combined_chunks:
        indices['time'] = sorted(combined_chunks.time.values),
    return combined_chunks.reindex(indices)


def create_time_chunks(datetime_list, _reversed=False, time_chunk_size=10):
    """Create an iterable containing groups of acquisition dates using class attributes

    Seperate a list of datetimes into chunks by acquisition, year, month, etc.


    Args:
        datetime_list: List or iterable of datetimes to chunk
        kwargs:
            _reversed (optional): boolean signifying that the acquisitions should be sorted least recent -> most recent (default)
                or most recent -> least recent

    Returns:
        iterable of time chunks
    """

    datetimes_sorted = sorted(datetime_list, reverse=_reversed)
    if time_chunk_size is None:
        return [datetimes_sorted]
    return _chunk_iterable(datetimes_sorted, time_chunk_size)


def group_datetimes_by_year(datetime_list):
    """Group a list of datetimes by year"""
    return dict(groupby(datetime_list, lambda x: x.year))


def group_datetimes_by_month(datetime_list, months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]):
    """Group an iterable of datetimes by month with an inclusion list"""
    month_filtered = filter(lambda x: x.month in months, datetime_list)
    return dict(groupby(datetime_list, lambda x: x.month))


def _chunk_iterable(_iterable, chunk_size):
    """Split an iterable into chunk_sized parts"""
    chunks = [_iterable[index:index + chunk_size] for index in range(0, len(_iterable), chunk_size)]
    return chunks


def _generate_baseline(_iterable, window_length):
    """Generate a sliding baseline of an iterable

    Creates a list of sliding baselines for the iterable. e.g. if you pass in
    a list of len==5 with a baseline length of 2, we will generate:
    [
        [elem0 (first element), elem1, elem2],
        [elem1, elem2, elem3],
        [elem2, elem3, elem4(last element)]
    ]

    The first element in each list is the element that the baseline is created for, followed by
    window_length number of elements as the baseline.

    Args:
        _iterable: iterable to create baselines for
        window_length: Number of elements to form a baseline

    Returns:
        list like [[window_1], [window_2], [window_3] ...]
    """
    if len(_iterable) <= window_length:
        return _iterable
    num_windows = len(_iterable) - window_length - 1
    return [[_iterable[window:window + window_length] for window in range(num_windows)]]
