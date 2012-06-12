import math
import colorsys
from PyQt4 import QtCore, QtGui
from main import _leaf, tracktime
from qt4_gui import _NodeActions
from collections import deque

class _LineItem(QtGui.QGraphicsLineItem):
    def paint(self, painter, option, widget):
        #painter.setClipRect( option.exposedRect )
        QtGui.QGraphicsLineItem.paint(self, painter, option, widget)


class ArcPartition(QtGui.QGraphicsPathItem):
    def __init__(self, parent=None):
        QtGui.QGraphicsPathItem.__init__(self, parent)
        self.setCacheMode(QtGui.QGraphicsItem.DeviceCoordinateCache)
        #self.setCacheMode(QtGui.QGraphicsItem.ItemCoordinateCache)
        
    def set_arc(self, cxdist, cydist, r1, r2, angle_start, angle_end):
        """ Draws a 2D arc with two arc lines of length r1 (inner) and
        r2 (outer) with center in cxdist,cydist. angle_start and
        angle_end are relative to the starting rotation point equal 0
        degrees """

        #self.data = [cxdist, cydist, r1, r2, angle_start, angle_end]
        d1 = r1 * 2
        d2 = r2 * 2 
        r1_xstart = -r1 - cxdist
        r1_ystart = -r1 + cydist
        r2_xstart = -r2 - cxdist
        r2_ystart = -r2 + cydist
        angle_start = angle_start
        angle_end = angle_end
        angle_span = angle_end + angle_start
        
        path = QtGui.QPainterPath()
        # Calculate start and end points of inner arc
        path.arcMoveTo(r1_xstart, r1_ystart, d1, d1, -angle_start)
        i1 = path.currentPosition()
        path.arcMoveTo(r1_xstart, r1_ystart, d1, d1, angle_end)
        i2 = path.currentPosition()
        # Moves to outer arc start position
        path.arcMoveTo(r2_xstart, r2_ystart , d2, d2, -angle_start)
        o1 = path.currentPosition()
        # Draws outer arc
        path.arcTo(r2_xstart, r2_ystart, d2, d2, -angle_start, angle_span)
        o2 = path.currentPosition()
        # Draws line to the end point in inner arc (straight line)
        path.lineTo(i2)
        # Draws inner arc from end point to to start 
        path.arcTo(r1_xstart, r1_ystart, d1, d1, angle_end, -angle_span)
        # Draws line to the start point of outer arc (straight line)
        path.lineTo(o1)
        self.setPath(path)

    def paint(self, painter, option, index):
        return QtGui.QGraphicsPathItem.paint(self, painter, option, index)


class _ArcItem(QtGui.QGraphicsPathItem):
    def __init__(self):
        QtGui.QGraphicsPathItem.__init__(self)
       
    def set_arc(self, cxdist, cydist, r1, r2, angle_start, angle_end):
        """ Draws a 2D arc with two arc lines of length r1 (inner) and
        r2 (outer) with center in cxdist,cydist. angle_start and
        angle_end are relative to the starting rotation point equal 0
        degrees """

        def clockwise(a):
            if a<0: 
                return -1 * (a)
            else:
                return -a
            return a

        #self.data = [cxdist, cydist, r1, r2, angle_start, angle_end]
        d1 = r1 * 2
        d2 = r2 * 2 
        r1_xstart = -r1 - cxdist
        r1_ystart = -r1 + cydist
        r2_xstart = -r2 - cxdist
        r2_ystart = -r2 + cydist

        # ArcTo does not use clockwise angles
        angle_start = clockwise(angle_start)
        angle_end = clockwise(angle_end)
        angle_span = angle_end - angle_start

        path = QtGui.QPainterPath()
        # Calculate start and end points of inner arc
        path.arcMoveTo(r1_xstart, r1_ystart, d1, d1, angle_start)
        i1 = path.currentPosition()
        path.arcMoveTo(r1_xstart, r1_ystart, d1, d1, angle_end)
        i2 = path.currentPosition()
        # Moves to outer arc start position
        path.arcMoveTo(r2_xstart, r2_ystart , d2, d2, angle_start)
        o1 = path.currentPosition()
        # Draws outer arc
        path.arcTo(r2_xstart, r2_ystart, d2, d2, angle_start, angle_span)
        o2 = path.currentPosition()
        # Draws line to the end point in inner arc (straight line)
        path.lineTo(i2)
        # Draws inner arc from end point to to start 
        path.arcTo(r1_xstart, r1_ystart, d1, d1, angle_end, -angle_span)
        # Draws line to the start point of outer arc (straight line)
        #path.lineTo(o1)
        self.setPath(path)

    def paint(self, painter, option, index):
        return QtGui.QGraphicsPathItem.paint(self, painter, option, index)

def rotate_and_displace(item, rotation, height, offset):
    """ Rotates an item of a given height over its own left most edis and moves
    the item offset units in the rotated x axis """
    t = QtGui.QTransform()
    t.rotate(rotation)
    t.translate(0, - (height / 2))
    t.translate(offset, 0)
    item.setTransform(t)


def get_min_radius(w, h, angle, xoffset):
    """ returns the radius and X-displacement required to render a
    rectangle (w,h) within and given angle (a)."""

    # converts to radians
    angle = (angle * math.pi) / 180 
    b = xoffset + w
    a = h / 2
    off = 0
    if xoffset:
        effective_angle = math.atan(a / xoffset)
        if effective_angle > angle / 2 and angle / 2 < math.pi:
            off = a / math.tan(angle / 2) 
            bb = off + w 
            #r = math.sqrt(a**2 + bb**2)
            r = math.hypot(a, bb)
            off = max (off, xoffset) - xoffset
        else:
            #r = math.sqrt(a**2 + b**2)
            r = math.hypot(a, b)
    else:
        # It happens on root nodes
        #r1 = math.sqrt(a**2 + b**2)
        r1 = math.hypot(a, b)
        #effective_angle = math.asin(a/r1)
        #r2 = w / math.cos(effective_angle)
        #print r1, r2
        r = r1#+r2
        
    return r, off

def render_circular(root_node, n2i, rot_step):
    max_r = 0.0
    for node in root_node.traverse('preorder'):
        item = n2i[node]
        w = sum(item.widths[1:4])
        h = item.effective_height

        parent_radius = n2i[node.up].radius if node.up else 0 
        angle = rot_step if _leaf(node) else item.angle_span

        if hasattr(item, "radius"):
            r = item.radius
            xoffset = 0
        else:
            r, xoffset = get_min_radius(w, h, angle, parent_radius + item.widths[0])
            item.radius = r
            node.add_features(rad=item.radius)

        if xoffset: # DEBUG ONLY. IF Scale is correct, this should not be printed
            print "Offset detected in node", xoffset

        rotate_and_displace(item.content, item.rotation, h, parent_radius)
        
        max_r = max(max_r, r)

        if not _leaf(node) and len(node.children) > 1:
            first_c = n2i[node.children[0]]
            last_c = n2i[node.children[-1]]
            # Vertical arc Line
            rot_end = n2i[node.children[-1]].rotation
            rot_start = n2i[node.children[0]].rotation
            rot_span = abs(rot_end - rot_start)
            C = item.vt_line
            C.setParentItem(item)
            path = QtGui.QPainterPath()
            # Counter clock wise
            path.arcMoveTo(-r, -r, r * 2, r * 2, 360 - rot_start - rot_span)
            path.arcTo(-r, -r, r*2, r * 2, 360 - rot_start - rot_span, rot_span)
            # Faces
            C.setPath(path)
            item.static_items.append(C)


        if hasattr(item, "content"):
            # If applies, it sets the length of the extra branch length
            if item.extra_branch_line:
                xtra =  item.extra_branch_line.line().dx()
                if xtra > 0:
                    xtra = xoffset + xtra
                else:
                    xtra = xoffset
                item.extra_branch_line.setLine(item.branch_length, item.center,\
                                               item.branch_length + xtra , item.center)
                item.nodeRegion.setWidth(item.nodeRegion.width()+xtra)

            # And moves elements 
            if xoffset:
                for i in item.movable_items:
                    i.moveBy(xoffset, 0)
            
    n2i[root_node].max_r = max_r
    print "MAX R", max_r
    return max_r

def init_circular_leaf_item(node, n2i, n2f, last_rotation, rot_step):
    item = n2i[node]
    item.rotation = last_rotation
    item.full_start = last_rotation - (rot_step / 2)
    item.full_end = last_rotation + (rot_step / 2)
    item.angle_span = rot_step
    item.effective_height = get_effective_height(node, n2i, n2f)
    item.center = item.effective_height/2

def init_circular_node_item(node, n2i, n2f):
    item = n2i[node]
    if len(node.children) >1: 
        first_c = n2i[node.children[0]]
        last_c = n2i[node.children[-1]]
        rot_start = first_c.rotation
        rot_end = last_c.rotation 
        item.rotation = rot_start + ((rot_end - rot_start) / 2)
        item.full_start = first_c.full_start
        item.full_end = last_c.full_end
        item.angle_span = item.full_end - item.full_start
    else:
        child = n2i[node.children[0]]
        rot_start = child.full_start
        rot_end = child.full_end
        item.angle_span = child.angle_span
        item.rotation = rot_start + ((rot_end - rot_start) / 2)
        item.full_start = child.full_start
        item.full_end = child.full_end
    
    item.effective_height = get_effective_height(node, n2i, n2f)
    item.center = item.effective_height/2

def get_effective_height(n, n2i, n2f):
    """Returns the height needed to calculated the adjustment
    of node to its available angle.
    """
    down_h = n2f[n]["branch-bottom"].h
    up_h = n2f[n]["branch-top"].h

    right_h = n2i[n].nodeRegion.height()/2
    up_h = max(right_h, up_h)
    down_h = max(right_h, down_h)
        
    fullR = n2i[n].fullRegion
    center = fullR.height()/2
    return max(up_h, down_h)*2
    
@tracktime
def calculate_optimal_scale(root_node, n2i, rot_step, img):
    """ Seems to be fast. 0.5s from a tree of 10.000 leaves""" 
    
    n2minradius = {}
    n2sumdist = {}
    n2sumwidth = {}
    visited_nodes = []
    # Calcula la posicion minima de los elementos (con scale=0, es
    # decir, sin tener en cuenta branch lengths.
    for node in root_node.traverse('preorder'):
        visited_nodes.append(node)
        ndist = node.dist if not img.force_topology else 1.0
        item = n2i[node]
        # Uses size of all node parts, except branch length
        w = sum(item.widths[1:4])
        h = item.effective_height
        parent_radius = n2minradius.get(node.up, 0)
        angle = rot_step if node.is_leaf() else item.angle_span
            
        r, xoffset = get_min_radius(w, h, angle, parent_radius)
        n2minradius[node] = r 
        n2sumdist[node] = n2sumdist.get(node.up, 0) + ndist 
        # versed sine: the little extra line needed to complete the
        # radius.
        #vs = r - (parent_radius + xoffset + w)
        n2sumwidth[node] = n2sumwidth.get(node.up, 0) + sum(item.widths[2:4]) #+ vs
        
    best_scale = None
    for node in visited_nodes:
        item = n2i[node]
        ndist = node.dist if not img.force_topology else 1.0
        if best_scale is None:
            best_scale = (n2minradius[node] - n2sumwidth[node]) / ndist if ndist else 0.0
        else:
            #Whats the expected radius of this node?
            current_rad = n2sumdist[node] * best_scale + n2sumwidth[node]
            # If too small, it means we need to increase scale.
            if current_rad < n2minradius[node]:
                # This is a simplification of the real ecuacion needed
                # to calculate the best scale. Given that I'm not
                # taking into account the versed sine of each parent
                # node, the equation is actually very simple.
                best_scale = (n2minradius[node] - n2sumwidth[node]) / n2sumdist[node]
                print "OOps adjusting scale", ndist, best_scale, n2minradius[node], current_rad, item.heights[5], node.name

            # If the width of branch top/bottom faces is not covered,
            # we can also increase the scale to adjust it. This may
            # produce huge scales, so let's keep it optional
            if img.optimal_scale_level == "full" and \
               item.widths[1] > ndist * best_scale:
                best_scale = item.widths[1] / ndist
                print "OOps adjusting scale because  branch-faces", ndist, best_scale, item.widths[1]


    # Adjust scale for aligned faces
    aligned_h = [(n2i[node].heights[5], node) for node in visited_nodes]
    aligned_h.sort(reverse=True)
    maxh, maxh_node = aligned_h[0]
    angle = n2i[maxh_node].angle_span
    rad, off = get_min_radius(1, maxh, angle, 0.0001)
    print "MIN RAD, OPTR", rad
    min_scale = None
    for node in visited_nodes:
        if n2i[node].heights[5]:
            new_scale = (rad - n2sumwidth[node]) / n2sumdist[node]
            min_scale = min(new_scale, min_scale) if min_scale is not None else new_scale
    if min_scale >  best_scale:
        best_scale = min_scale

    
    #for node in visited_nodes:
    #    item = n2i[node]
    #    h = item.effective_height
    #    a = n2sumdist[node] * best_scale + n2sumwidth.get(node) 
    #    b = h/2
    #    item.radius = math.sqrt(a**2 + b**2)
    return best_scale