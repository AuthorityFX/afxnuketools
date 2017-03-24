# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (C) 2012-2017, Ryan P. Wilson
#
#      Authority FX, Inc.
#      www.authorityfx.com

import nuke
from afxthreads.image import ImageMultiProcessor, Bounds


def _centroid(region, node_name, channel, step=1):
    """Calculates the channel centroid of channel.

    Args:
        region (Bounds): Region of interest
        step (int): The step size when iterating through pixels. Step size
            increases computation speed by a factor of step^2

    Returns:
        float: Returns tuple (mean_x, mean_y, mean_weight)
        mean_x is the mean of the x cords weighted by channel values
        mean_y is the mean of the y cords weighted by channel values
        mean_weight is the mean of the channel values

    """
    mean_x = 0.0
    mean_y = 0.0
    mean_weight = 0.0
    n = 0
    node = nuke.toNode(node_name)
    for y in xrange(region.y1, region.y2 + 1, step):
        for x in xrange(region.x1, region.x2 + 1, step):
            # Numerically stable weighted mean
            weight = node.sample(channel, x, y)
            n += 1
            mean_weight += (weight - mean_weight) / n
            mean_x += (weight * x - mean_x) / n
            mean_y += (weight * y - mean_y) / n

    return mean_x, mean_y, mean_weight


def _max_value(region, node_name, channel, step=1):
    """Calculates the maxiumum value for channel.

    Args:
        region (Bounds): Region of interest
        step (int): The step size when iterating through pixels. Step size
            increases computation speed by a factor of step^2

    Returns:
        float: Returns the maxium alpha of region.

    """
    max_val = 0.0
    node = nuke.toNode(node_name)
    for y in xrange(region.y1, region.y2 + 1, step):
        for x in xrange(region.x1, region.x2 + 1, step):
            # If the optional dx,dy are not given then impulse filter is used.
            max_val = max(max_val, node.sample(channel, x, y))

    return max_val

def centroid(node, channel, step=1):
    """Calculates the channel centroid of channel.

    Args:
        region (Bounds): Region of interest
        step (int): The step size when iterating through pixels. Step size
            increases computation speed by a factor of step^2

    Returns:
        float: Returns list coords [x, y] representing the centroid of channel.
        If aborted, or exception is handled, will return None

    """
    bbox = node.bbox()
    region = Bounds(bbox.x(), bbox.y(), bbox.w() + bbox.x() - 1, bbox.h() + bbox.y() - 1)
    centroid = (0.0, 0.0)
    with ImageMultiProcessor(log_exceptions=True) as mp:

        task = nuke.ProgressTask('Calculating centroid...')
        task.setProgress(0)

        mp.process_by_chunks(_centroid, (region, node.name(), channel, step))
        while mp.is_working():
            if task.isCancelled():
                mp.abort()
                break
            else:
                mp.wait_one()
                progress = int(100.0 * float(len(mp.results)) / float(mp.processes()))
                task.setProgress(progress)

        sum_x = 0.0
        sum_y = 0.0
        sum_weight = 0.0
        for r in mp.results:
            if mp.state() is False or issubclass(type(r), Exception):
                centroid = None
                del task
                raise Exception(str(r))
            else:
                sum_x += r[0]
                sum_y += r[1]
                sum_weight += r[2]
        if centroid is not None:
            if sum_weight > 0:
                sum_x /= sum_weight
                sum_y /= sum_weight
            centroid = (sum_x, sum_y)

    return centroid


def max_value(node, channel, step=1):
    """Calculates the maxiumum channel value for bbox of node.

    Args:
        node (nuke.node): The nuke node for which to calculate max alpha
        channel (string): The channel of interest
        step (int): Defaults to 1.  The step size when iterating through pixels.
            Step size increases computation speed by a factor of step^2

    Returns:
        float: Returns the maxium channel value.  If aborted, will return None

    """
    bbox = node.bbox()
    region = Bounds(bbox.x(), bbox.y(), bbox.w() + bbox.x() - 1, bbox.h() + bbox.y() - 1)
    max_val = 0.0
    with ImageMultiProcessor(log_exceptions=True) as mp:

        task = nuke.ProgressTask('Calculating max value...')
        task.setProgress(0)

        mp.process_by_chunks(_max_value, (region, node.name(), channel, step))
        while mp.is_working():
            if task.isCancelled():
                mp.abort()
                break
            else:
                mp.wait_one()
                progress = int(100.0 * float(len(mp.results)) / float(mp.processes()))
                task.setProgress(progress)

        for r in mp.results:
            if mp.state() is False or issubclass(type(r), Exception):
                centroid = None
                del task
                raise Exception(str(r))
            max_val = max(max_val, r)

    return max_val
