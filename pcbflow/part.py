#! /usr/bin/env python3
#
# PCB part class
#

from collections import defaultdict
import re
import math
import csv

from PIL import Image
import shapely.geometry as sg
import shapely.affinity as sa
import shapely.ops as so
import math

from pcbflow import *


class Part:
    mfr = ""
    footprint = ""
    val = ""
    inBOM = True
    source = {}

    def __init__(self, dc, val=None, source=None, side="top"):
        self.id = dc.board.assign(self)
        self.side = side.lower()
        if val is not None:
            self.val = val
        self.pads = []
        self.board = dc.board
        self.center = dc.copy()
        self.place(dc)
        if source is not None:
            self.source = source

    def _layers(self):
        if self.side == "top":
            return ["GTL", "GTS", "GTP"]
        else:
            return ["GBL", "GBS", "GBP"]

    def _silklayer(self):
        if self.side == "top":
            return "GTO"
        return "GBO"

    def text(self, dc, s):
        (x, y) = dc.xy
        dc.board.layers[self._silklayer()].add(
            hershey.ctext(
                x, y, s, side=self.side, linewidth=self.board.drc.text_silk_width
            )
        )

    def label(self, dc, angle=0):
        (x, y) = dc.xy
        gt = hershey.ctext(
                x, y, self.id, side=self.side, linewidth=self.board.drc.text_silk_width
            )
        gt = sa.rotate(gt, angle)
        dc.board.layers[self._silklayer()].add(gt)

    def minilabel(self, dc, s):
        dc.push()
        dc.rect(0.7, 0.7)
        dc.silko(side=self.side)
        dc.w("r 180 f 1.5")
        (x, y) = dc.xy
        dc.board.layers[self._silklayer()].add(
            hershey.ctext(
                x, y, s, side=self.side, linewidth=self.board.drc.text_silk_width
            )
        )
        dc.pop()
        dc.newpath()

    def notate(self, dc, s):
        (x, y) = dc.xy
        dc.board.layers[self._silklayer()].add(
            hershey.text(
                x,
                y,
                s,
                scale=0.1,
                side=self.side,
                linewidth=self.board.drc.text_silk_width,
            )
        )

    def chamfered(self, dc, w, h, drawid=True, idoffset=(0, 0)):
        # Outline in top silk, chamfer indicates top-left
        # ID next to chamfer

        nt = 0.4
        dc.push()
        dc.forward(h / 2)
        dc.left(90)
        dc.forward(w / 2 - nt)
        dc.right(180)
        dc.newpath()
        for e in (w - nt, h, w, h - nt):
            dc.forward(e)
            dc.right(90)
        dc.silko(side=self.side)
        dc.pop()

        dc.push()
        dc.forward(h / 2 + 0.5)
        dc.left(90)
        dc.forward(w / 2 + 0.5)
        dc.right(90)
        dc.goxy(*idoffset)
        (x, y) = dc.xy
        if drawid:
            dc.board.layers[self._silklayer()].add(
                hershey.ctext(
                    x,
                    y,
                    self.id,
                    side=self.side,
                    linewidth=self.board.drc.text_silk_width,
                )
            )
        dc.pop()

    def pad(self, dc):
        for n in self._layers():
            if n.endswith("S"):
                g = dc.poly().buffer(self.board.drc.soldermask_margin)
            else:
                g = dc.poly()
            dc.board.layers[n].add(g)
        p = dc.copy()
        p.part = self.id
        self.pads.append(p)

    def rpad(self, dc, w, h):
        dc.right(90)
        dc.rect(w, h)
        self.pad(dc)
        dc.left(90)

    def roundpad(self, dc, d):
        (dc.w, dc.h) = (d, d)
        g = sg.Point(dc.xy).buffer(d / 2)
        for n in self._layers():
            dc.board.layers[n].add(g)
        p = dc.copy()
        p.part = self.id
        self.pads.append(p)

    def train(self, dc, n, op, step):
        for i in range(n):
            op()
            dc.forward(step)

    def s(self, nm):
        if " " in nm:
            return [self.s(n) for n in nm.split()]
        return {p.name: p for p in self.pads}[nm]
