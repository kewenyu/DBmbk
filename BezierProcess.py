import vapoursynth as vs
import mvsfunc as mvf
import math


def bezier_process(clip, accur=0.01, input_range='pc', planes=0, debug=False, **coordinate):
    """
    This function process clip according to a specified bezier curve
    :param clip: Source clip
    :param accur: Step size of exhaustion. Default: 0.01
    :param input_range: 'tv' or 'pc'. Normally set it to pc when clip is a mask otherwise set it to tv. Default: 'pc'
    :param planes: Specify a list of planes to process. Default: 0
    :param debug: Preview the curve you created using Matplotlib. Default: False
    :param coordinate: The coordinates of anchor point.
    :return: Output clip
    """

    core = vs.get_core()
    func_name = 'bezier process'
    bits = clip.format.bits_per_sample

    def normalize(val, clip_range):
        if clip_range is 'tv':
            if val < 16:
                normalized = 0
            elif val > 235:
                normalized = 1
            else:
                normalized = (val - 16) / (235 - 16)
        elif clip_range is 'pc':
            normalized = val / 255
        else:
            raise ValueError(func_name + ': Incorrect input_range setting.')
        return normalized

    x1 = normalize(coordinate.get('x1', 85), input_range)
    x2 = normalize(coordinate.get('x2', 170), input_range)
    begin = coordinate.get('begin', 128)
    y1 = coordinate.get('y1', 128)
    y2 = coordinate.get('y2', 128)
    end = coordinate.get('end', 128)

    # Check whether coordinates are in range
    parameters_check = [0 < x1 < 1, 0 < x2 < 1, accur <= 1]
    if False in parameters_check:
        raise ValueError(func_name + ': Incorrect coordinate setting.')

    def bezier_x(t):
        x = (3 * x1 * t * (1 - t) ** 2 +
             3 * x2 * (1 - t) * t ** 2 +
             t ** 3)
        return x

    def bezier_t(x):
        t = 0
        while t <= 1 + accur:
            if abs(bezier_x(t) - x) < accur:
                return t
            t += accur
        raise ValueError(func_name + ': can not get a solution of bezier.')

    def bezier_y(t):
        y = begin * (1 - t) ** 3 + \
            3 * y1 * t * (1 - t) ** 2 + \
            3 * y2 * (1 - t) * t ** 2 + \
            end * t ** 3
        return y

    def lut_expr(x):
        return min(max(math.floor(bezier_y(bezier_t(normalize(x, input_range)))), 0), 255)

    if debug is True:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ValueError(func_name + ': Matplotlib is required to run debug process.')
        x = []
        y = []
        for i in range(1000):
            num = i / 1000
            x.append(num)
            y.append(bezier_y(bezier_t(num)))
        plt.plot(x, y)
        plt.axis([0, 1, 0, 255])
        plt.show()
        return

    # Make sure process depth is 8bit because lut in high depth cost too much
    if bits != 8:
        clip = mvf.Depth(clip, 8)

    clip = core.std.Lut(clip, planes=planes, function=lut_expr)

    # Back to original depth
    if bits != 8:
        clip = mvf.Depth(clip, bits)

    return clip
