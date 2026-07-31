import math
import time
from collections import namedtuple

Stat = namedtuple('Stat', ('aver', 'std_dev', 'cm3', 'cm4'))

class StatCollector:
    """Measured values sequence stat collector"""
    median_wnd = 1025

    def __init__(self, XY=None):
        self.total_samples = self.total_valid = 0
        self.total_sum = self.total_sum2 = self.total_sum3 = self.total_sum4 = 0
        self.total_min = float('inf')
        self.total_max = -self.total_min
        self.median_sum, self.median_cnt = 0, 0
        self.median_buff = []
        self.last_ts = None
        self.last_val = None
        self.integral = 0.
        if XY:
            for x, y in zip(XY[0], XY[1]):
                self.account(x, y)

    def account(self, t, val):
        self.total_samples += 1
        if self.last_ts is not None:
            elapsed = t - self.last_ts
        else:
            elapsed = 0
        self.last_ts = t
        if self.last_val is not None:
            self.integral += self.last_val * elapsed / 2
        if math.isnan(val):
            self.last_val = None
            return
        self.integral += val * elapsed / 2
        self.last_val = val
        v2 = val * val
        self.total_valid += 1
        self.total_sum   += val
        self.total_sum2  += v2
        self.total_sum3  += v2 * val
        self.total_sum4  += v2 * v2
        self.total_min    = min(self.total_min, val)
        self.total_max    = max(self.total_max, val)
        self.median_buff.append(val)
        while len(self.median_buff) > self.median_wnd:
            self.median_buff.pop(0)
        if len(self.median_buff) == self.median_wnd:
            self.median_sum += sorted(self.median_buff)[self.median_wnd//2]
            self.median_cnt += 1

    def get_median(self):
        if self.median_cnt:
            return self.median_sum / self.median_cnt
        vals = sorted(self.median_buff)
        cnt  = len(self.median_buff)
        assert cnt == self.total_valid
        return (vals[(cnt-1)//2] + vals[cnt//2]) / 2

    def get_stat(self):
        aver, aver2 = self.total_sum / self.total_valid, self.total_sum2 / self.total_valid
        aver_2  = aver * aver
        sigma_2 = aver2 - aver_2
        sigma   = math.sqrt(sigma_2) if sigma_2 > 0 else 0
        cm3     = self.total_sum3 / self.total_valid - aver * (aver_2 + 3 * sigma_2)
        cm4     = self.total_sum4 / self.total_valid - aver * (aver * (aver_2 + 6 * sigma_2) + 4 * cm3)
        return Stat(aver, sigma, cm3, cm4)

    def print(self, outf):
        print('total samples  : %d' % self.total_samples, file=outf)
        print('valid samples  : %d' % self.total_valid, file=outf)
        if self.total_valid:
            st = self.get_stat()
            print('min  value     : %f' % self.total_min, file=outf)
            print('max  value     : %f' % self.total_max, file=outf)
            print('median average : %f' % self.get_median(), file=outf)
            print('aver value     : %f' % st.aver, file=outf)
            print('std deviation  : %f' % st.std_dev, file=outf)
            if st.aver:
                print('rel. dev. [%%]  : %.2f' % (100 * st.std_dev / abs(st.aver)), file=outf)
            if st.std_dev:
                print('skewness       : %.2f' % (st.cm3 / (st.std_dev ** 3)), file=outf)
                print('kurtosis exess : %.2f' % (st.cm4 / (st.std_dev ** 4) - 3), file=outf)
            print('integral       : %f' % self.integral, file=outf)

def histogram(Y, N):
    """
    Returns histogram of the dataset Y with N bins as pair of lists (Yc, Cnt),
    where Yc is the coordinate of the bin center, Cnt is the number of samples in the bin
    """
    if not Y:
        return [], []
    Y0, Y1 = min(Y), max(Y)
    dY = (Y1 - Y0) / N
    Cnt = [0] * N
    for y in Y:
        Cnt[min(int((y - Y0) / dY), N - 1)] += 1
    return [Y0 + dY / 2 + dY * i for i in range(N)], Cnt

