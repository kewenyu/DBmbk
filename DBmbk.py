﻿##=====================================================================================
## 2017.01.04                               DBmbk 0.1.0
##               A de-banding script which dynamically adjust the values of y, cb, 
##               cr of f3kdb according to average luma of each frame. The intensity
##               of adjustment can follow a elementary function or a bezier curve.
##=====================================================================================
##
##               Made By Kewenyu - 1059902659@qq.com
##
##=====================================================================================
##
## Reqirements:
##               F3kdb
##               Matplotlib (optional)
##
##=====================================================================================
##
## Example:
##              If you want to use the curve of logarithm function:
##                 dbobj = DBmbk.Elementary(mode='log', range=15, y=72, grainy=0)
##                 dbed = dbobj.deband(clip)
##
##              If you want to use the bezier curve:
##                 dbobj = DBmbk.BezierCurve(left=48, right=22, range=15, grainy=0)
##                 dbed = dbobj.deband(clip)
##
##              If you want to see what does the bezier curve you created look like:
##                 dbobj = DBmbk.BezierCurve(left=48, right=22, range=15, grainy=0)
##                 dbobj.show_curve()
##              *This function require matplotlib
##
##=====================================================================================
import vapoursynth as vs
import functools
import math

class DBmbk:
    def __init__(self, f3kargs):
        self.core = vs.get_core()
        self.name = 'DBmbk'
        try:
            self.f3k_y = f3kargs['y']
            self.f3k_cb = f3kargs['cb']
            self.f3k_cr = f3kargs['cr']
        except KeyError:
            raise ValueError(self.name + ': y, cb, cr of f3kdb must be set !')

class Elementary(DBmbk):
    def __init__(self, mode='lin', paraments=None, chroma=False, debug=0, **f3kargs):
        super(Elementary, self).__init__(f3kargs)
        self.mode = mode
        if mode is 'lin' and paraments is None:
            self.paraments = (20, 0.5)
        elif mode is 'log' and paraments is None:
            self.paraments = (20, 0.42, 3)
        elif mode is 'pow' and paraments is None:
            self.paraments = (20, 0.84, 3)
        self.chroma = chroma
        self.f3kargs = f3kargs
        self.debug = debug

    def deband(self, clip):
        clip = self.core.std.PlaneStats(clip, plane=0, prop='props')

        def adaptive_process(n, f, clip):
            average_luma = f.props.propsAverage

            if self.mode is 'lin':
                if len(self.paraments) != 2:
                    raise ValueError(self.name + ': Incorrect paraments for this mode !')
                bias = self.paraments[0] * (self.paraments[1] - average_luma)

            elif self.mode is 'log':
                if len(self.paraments) != 3:
                    raise ValueError(self.name + ': Incorrect paraments for this mode !')
                bias = self.paraments[0] * math.log((self.paraments[1] - average_luma + 1), self.paraments[2])
            
            elif self.mode is 'pow':
                if len(self.paraments) != 3:
                    raise ValueError(self.name + ': Incorrect paraments for this mode !')
                bias = self.paraments[0] * (self.paraments[1] - average_luma) ** self.paraments[2]

            else:
                raise ValueError(self.name + ': Unknown mode !')

            self.f3kargs['y'] = min(max(int(self.f3k_y + bias), 0), 128)
            if self.chroma is True:
                self.f3kargs['cb'] = min(max(int(self.f3k_cb + bias), 0), 128)
                self.f3kargs['cr'] = min(max(int(self.f3k_cr + bias), 0), 128)

            dbed = self.core.f3kdb.Deband(clip, **self.f3kargs)

            if self.debug == 1:
                text = 'Frames: {num}\nAverage Luma: {luma}\nShift: {shift}\nY: {y} ({y_org})\nCb: {cb} ({cb_org})\nCr: {cr} ({cr_org})'.format(num=n, luma=average_luma,
                                                                                                                                         shift=bias, y=self.f3kargs['y'], 
                                                                                                                                         cb=self.f3kargs['cb'], cr=self.f3kargs['cr'], 
                                                                                                                                         y_org=self.f3k_y, cb_org=self.f3k_cb, cr_org=self.f3k_cr)
                out = self.core.text.Text(dbed, text)
            else:
                out = dbed

            return out

        return self.core.std.FrameEval(clip, functools.partial(adaptive_process, clip=clip), prop_src=clip)

class BezierCurve(DBmbk):
    def __init__(self, left=64, right=32, anc_x=0.4, anc_y=70, accur=0.001, chroma=False, debug=0, **f3kargs):
        super(BezierCurve, self).__init__(f3kargs)
        self.left = left
        self.right = right
        self.anc_x = anc_x
        self.anc_y = anc_y
        self.accur = accur
        self.chroma = chroma
        self.debug = debug
        self.f3kargs = f3kargs

    def bezier_x(self, t):
        return 2 * self.anc_x * t * (1 - t) + t**2    # x0 is 0, x2 is 1

    def bezier_t(self, x):
        t = 0
        while t <= 1:
            if abs(self.bezier_x(t) - x) < self.accur:
                return t
            else:
                t = t + self.accur
        raise ValueError(self.name + ': Can\'t get a solution of bezier.')

    def bezier_y(self, t):
        return self.left * (1 - t) ** 2 + 2 * self.anc_y * t * (1 - t) + self.right * t ** 2

    def deband(self, clip):
        clip = self.core.std.PlaneStats(clip, plane=0, prop='props')

        def adaptive_process(n, f, clip):
            average_luma = f.props.propsAverage

            t = self.bezier_t(average_luma)
            self.f3kargs['y'] = min(max(int(self.bezier_y(t)), 0), 128)
            if self.chroma is True:
                self.f3kargs['cb'] = min(max(int(self.f3k_cb / self.f3k_y * self.f3kargs['y']), 0), 128)
                self.f3kargs['cr'] = min(max(int(self.f3k_cr / self.f3k_y * self.f3kargs['y']), 0), 128)

            dbed = self.core.f3kdb.Deband(clip, **self.f3kargs)

            if self.debug == 1:
                text = 'Frames: {num}\nAverage Luma: {luma}\nt: {t}\nY: {y}\nCb: {cb}\nCr: {cr}'.format(num=n, luma=average_luma, t=t,
                                                                                                        y=self.f3kargs['y'], cb=self.f3kargs['cb'], cr=self.f3kargs['cr'])
                out = self.core.text.Text(dbed, text)
            else:
                out = dbed
            
            return out

        return self.core.std.FrameEval(clip, functools.partial(adaptive_process, clip=clip), prop_src=clip)

    def show_curve(self):
        try:
            import matplotlib.pyplot as plt
        except:
            raise ValueError(self.name + ': Matplotlib is required to run this function')
        x = []
        y = []
        for i in range(1000):
            num = i / 1000
            x.append(num)
            y.append(self.bezier_y(num))
        plt.plot(x, y)
        plt.show()
