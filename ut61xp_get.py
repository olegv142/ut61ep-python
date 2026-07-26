"""
The UNI-T UT61X+/UT60BT and OWON multimeters data acquisition and plotting tool
"""

import os
import io
import sys
import math
import time
import json
import argparse
import logging
from ut61xp import UTDevice, HIDDevice, BTDevice, UT60BTDevice
from owon import OwonBtDevice
from data_stat import StatCollector, histogram
from datetime import datetime

log = logging.getLogger('DEV')

_parent_conn = None

_supported_devices = (
    HIDDevice, BTDevice, UT60BTDevice, OwonBtDevice
)

class Plotter:
    """Data plotter"""
    padding = .075
    dual_with_stat_min_h = 7

    def __init__(self, args, devT, stat):
        import matplotlib.pyplot as plt
        plt.rcParams["figure.raise_window"] = False
        plt.ion()
        self.plt = plt
        self.args = args
        self.devT = devT
        self.stat = stat
        self.expanded = False
        if args.alt_file:
            nchan = 2 # dual channel plot
            self.fig, self.ax = self.plt.subplots(2, 1, sharex = True)
            if args.alt_title:
                self.ax[1].set_title(args.alt_title)
            if args.alt_hline:
                for y in args.alt_hline:
                    self.ax[1].axhline(y, linestyle=args.hline_style, color=args.hline_color)
        else:
            nchan = 1
            self.fig, ax = self.plt.subplots()
            self.ax = [ax]
        if args.plot_title:
            self.ax[0].set_title(args.plot_title)
        if args.hline:
            for y in args.hline:
                self.ax[0].axhline(y, linestyle=args.hline_style, color=args.hline_color)

        self.x_data, self.y_data = [[] for _ in range(nchan)], [[] for _ in range(nchan)]
        self.line = [self.ax[i].plot([], [],
                linestyle=args.line_style,
                color=(args.line_color, args.alt_line_color)[i]
            )[0] for i in range(nchan)]
        self.vmin, self.vmax = [float('inf')] * nchan, [float('-inf')] * nchan
        self.fig.canvas.manager.set_window_title(args.title if args.title else devT.model_name)
        self.init_window_icon(self.fig.canvas)
        self.init_dbl_click_handler(self.fig.canvas)
        self.init_hot_keys(self.fig.canvas)
        if args.full_screen:
            self.fig.canvas.manager.full_screen_toggle()

    @staticmethod
    def init_window_icon(canvas):
        if not hasattr(canvas.manager, 'window'):
            return
        icon_path = os.path.dirname(os.path.realpath(__file__)) + '/meter.png'
        if hasattr(canvas.manager.window, 'set_icon_from_file'):
            canvas.manager.window.set_icon_from_file(icon_path)
        elif hasattr(canvas.manager.window, 'iconphoto'):
            import tkinter as tk
            canvas.manager.window.iconphoto(False, tk.PhotoImage(file=icon_path))

    @staticmethod
    def init_dbl_click_handler(canvas):
        last_click = 0
        def on_click(e):
            nonlocal last_click
            ts = time.time()
            if ts < last_click + .5: # double click
                canvas.manager.full_screen_toggle()
            last_click = ts
        canvas.mpl_connect('button_press_event', on_click)

    def init_hot_keys(self, canvas):
        wnd = None
        def on_key_press(e):
            nonlocal wnd
            if e.key == ' ':
                print_stat(self.args, self.stat)
                print(file=sys.stderr)
            elif e.key == 'w' or e.key == 'W':
                if self.args.wnd:
                    self.args.wnd, wnd = None, self.args.wnd
                    log.info('\nwnd off')
                elif wnd:
                    self.args.wnd = wnd
                    log.info('\nwnd[%u] on' % wnd)
            elif e.key == 'z' or e.key == 'Z':
                self.args.with_zero = not self.args.with_zero
            elif e.key == 't' or e.key == 'T':
                if self.args.plot_stat:
                    for ax in self.ax:
                        if l := ax.get_legend():
                            l.remove()
                self.args.plot_stat = not self.args.plot_stat

        canvas.mpl_connect('key_press_event', on_key_press)
        log.info('press space to print data statistics, z to toggle zero axis display, w to toggle data window, t to toggle stat display, q to exit')

    def is_closed(self):
        return not self.plt.fignum_exists(self.fig.number)

    def update_xlim(self, chan, xmin, xmax):
        ax = self.ax[chan]
        if xmin == xmax:
            xmax += self.args.interval if self.args.interval else 1
        ax.set_xlim(xmin, xmax)

    def update_ylim(self, chan, ymin, ymax):
        ax = self.ax[chan]
        hlines = self.args.hline if not chan else self.args.alt_hline
        if hlines:
            for y in hlines:
                ymin = min(ymin, y)
                ymax = max(ymax, y)
        if ymin > 0 and self.args.with_zero:
            vmin = 0
            vmax = ymax * (1 + self.padding)
        elif ymax < 0 and self.args.with_zero:
            vmax = 0
            vmin = ymin * (1 + self.padding)
        else:
            vrange = ymax - ymin if ymax > ymin else abs(ymax) if ymax else 1
            vmin = ymin - vrange * self.padding
            vmax = ymax + vrange * self.padding
        ax.set_ylim(vmin, vmax)

    def show_stat(self, ax, stat):
        buff = io.StringIO()
        stat.print(buff)
        ax.legend(
            [buff.getvalue().strip()], 
            loc=self.args.plot_stat_loc,
            handlelength=0,      # Removes the line symbol 
            handletextpad=0,     # Removes padding between the symbol and text
            facecolor='white',   # Background color of the text box
            edgecolor='black',   # Border color
            framealpha=.5,       # Background opacity (1.0 = fully opaque)
            fancybox=True,
            prop={'family': 'monospace'} # Use monospace font
        )
        if len(self.ax) > 1 and not self.expanded:
            h = self.fig.get_figheight()
            if h < self.dual_with_stat_min_h:
                self.fig.set_figheight(self.dual_with_stat_min_h)
                self.expanded = True

    def update(self, t, data, val, chan):
        if not math.isnan(val) and chan < len(self.ax):
            axis = self.ax[chan]
            self.vmin[chan] = min(self.vmin[chan], val)
            self.vmax[chan] = max(self.vmax[chan], val)
            wnd = self.args.wnd
            xdata, ydata = self.x_data[chan], self.y_data[chan]
            xdata.append(t)
            ydata.append(val)
            pan_zoom = axis.get_navigate_mode() is not None
            while wnd and not pan_zoom and len(xdata) > wnd:
                xdata.pop(0)
                ydata.pop(0)
            self.line[chan].set_data(xdata, ydata)
            if not pan_zoom:
                if not chan:
                    self.update_xlim(chan, xdata[0], xdata[-1])
                self.update_ylim(chan, *((min(ydata), max(ydata)) if wnd else (self.vmin[chan], self.vmax[chan])))
            if not (self.args.plot_title, self.args.alt_title)[chan]:
                mode = self.devT.get_mode(data)
                if axis.get_title() != mode:
                    axis.set_title(mode)
            if self.args.plot_stat:
                self.show_stat(axis, self.stat[chan])
        self.fig.canvas.flush_events()
        self.plt.show()

def _device_type(is_bt, model=None):
    for T in _supported_devices:
        if is_bt == T.isBT:
            if model is None:
                return T
            elif model == T.model_name:
                return T
    return None

def device_type(args):
    """Returns selected device type (class)"""
    T = _device_type(args.bt, args.model)
    if T is not None:
        return T
    assert args.model is not None
    T = _device_type(args.bt)
    assert T is not None
    log.warning('model %s is not supported in %s mode, using default %s',
            args.model, 'BT' if args.bt else 'HID', T.model_name
        )
    return T

def open_device(args):
    """Open HID or BT device"""
    T = device_type(args)
    if args.path:
        dev = T.open_addr(args.path) if T.isBT else T.open_path(args.path)
    else:
        dev = T.open(args.name) if T.isBT else T.open(args.VID, args.PID)
    if dev:
        log.info('%s %s at %s', 'open' if args.path else 'found', dev.model_name, dev.path)
    return dev

def do_list(args):
    T = device_type(args)
    if not T.isBT:
        for path in T.list_paths(args.VID, args.PID):
            print(path)
    else:
        for addr in T.list_addrs(args.name):
            print(addr)
    return 0

def do_once(args):
    """Read and print single value"""
    dev = open_device(args)
    if dev is None:
        return -1
    try:
        data = dev.query_raw(args.tout)
        if not data:
            log.error('\nno data')
            return -1
        print(dev.get_value(data))
        return 0
    finally:
        dev.close()

def update_cfg(args, dev_path, fname, alt_fname):
    """Save configuration if necessary"""
    opts = args.__dict__.copy()
    del opts['func']
    opts['cfg_save'] = None
    opts['path'] = dev_path
    if cfg_save_fname := getattr(args, 'cfg_save', None):
        with open(cfg_save_fname, 'w') as f:
            f.write(json.dumps(opts))
    if _parent_conn:
        opts['_file'] = fname 
        opts['_alt_file'] = alt_fname
        _parent_conn.send(opts)

def print_stat(args, stats):
    print('\n--- data statistics:', file=sys.stderr)
    stats[0].print(sys.stderr)
    if args.alt_file:
        print('\n--- alternative channel:', file=sys.stderr)
        stats[1].print(sys.stderr)

def update_measuring_defaults(args):
    if args.interval is None:
        args.interval = 1 if not args.alt_file else 0

def get_fname(dev, fname):
    """Makes filename from parameter string and makes sure folder part exists"""
    if not fname:
        return None
    if '$' in fname:
        fname = fname.replace('${MODEL}', dev.model_name)
    if '%' in fname:
        fname = datetime.now().strftime(fname)
    dirname = os.path.dirname(fname)
    if dirname:
        try:
            os.mkdir(dirname)
        except FileExistsError:
            pass
    return fname

def write_data_info(out_file, dev, data):
    print('#', dev.get_mode(data), '|', dev.model_name, file=out_file)

def do_data(args):
    """
    Read data continuously and plot them if -g option is present in args.
    The read loop ends either by typing Ctr-C (without -g option) or by
    closing data graph window.
    """
    dev = open_device(args)
    if dev is None:
        return -1

    fname, alt_fname = get_fname(dev, args.file), get_fname(dev, args.alt_file)
    if fname != args.file:
        log.info('saving data to %s', fname)
    if alt_fname != args.alt_file:
        log.info('saving alternative channel to %s', alt_fname)
    update_cfg(args, dev.path, fname, alt_fname)
    update_measuring_defaults(args)

    out_fmt = '%.3f%s %f'
    out_file = sys.stdout if not fname else open(fname, 'w')
    alt_file = None if not alt_fname else open(alt_fname, 'w')
    out_empty, alt_empty = True, True
    stat = [StatCollector(), StatCollector()]
    if args.graph:
        plotter = Plotter(args, type(dev), stat)
        sleep_fn = plotter.plt.pause
    else:
        plotter = None
        sleep_fn = time.sleep
    errs_max = 1 if not args.bt else 5
    errs_left = errs_max
    try:
        start = ts = time.time()
        while True:
            # Query data
            data = dev.query_raw(args.tout, sleep_fn)
            if not data:
                if not dev.is_connected():
                    log.error('\ndisconnected')
                    return -1
                if fname and args.progress:
                    print('~', end='', file=sys.stderr, flush=True)
                if plotter and plotter.is_closed():
                    return 0
                errs_left -= 1
                if errs_left <= 0:
                    log.error('\nno data')
                    return -1
                continue
            errs_left = errs_max
            t = ts - start
            val = dev.get_value(data)
            val_chan = dev.get_channel(data)
            val_good = not math.isnan(val)
            # Output data
            if val_good or args.keep_nan:
                if val_chan == 0:
                    if val_good: # apply value transformation
                        val = (val - args.offset) * args.mult
                    if out_empty:
                        out_empty = False
                        if fname:
                            write_data_info(out_file, dev, data)
                    print(out_fmt % (ts if args.epoch else t, args.delimiter, val), file=out_file)
                elif alt_file:
                    if alt_empty:
                        alt_empty = False
                        write_data_info(alt_file, dev, data)
                    print(out_fmt % (ts if args.epoch else t, args.delimiter, val), file=alt_file)
            if fname and args.progress:
                # Show progress
                print('.' if val_good else '!', end='', file=sys.stderr, flush=True)
            # Update stat
            stat[val_chan].account(val, t)
            if plotter:
                if plotter.is_closed():
                    return 0
                # Update plot
                plotter.update(t, data, val, val_chan)
            # Introduce delay according to acquisition interval
            now = time.time()
            elapsed = now - ts
            if elapsed < args.interval:
                sleep_fn(args.interval - elapsed)
                ts += args.interval
            else:
                ts = now
    finally:
        dev.close()
        if fname:
            if args.progress:
                print(file=sys.stderr)
            out_file.close()
        if alt_file:
            alt_file.close()
        if args.stat:
            print_stat(args, stat)

def load_data_file(fname, skip_nan=False):
    """
    Load x, y data from the file and info from the header.
    Returns X, Y, info tuple.
    """
    xdata, ydata, info = [], [], None
    with open(fname, 'r') as f:
        for line in f:
            if line[:1] == '#' and not info:
                info = line[1:].strip()
                continue
            xy = line.split()
            if len(xy) != 2:
                continue
            try:
                x, y = float(xy[0]), float(xy[1])
            except ValueError:
                continue
            if math.isnan(y) and skip_nan:
                continue
            xdata.append(x)
            ydata.append(y)
    return xdata, ydata, info

def split_file_info(info):
    """Returns units, model pair"""
    if not info:
        return '', ''
    infos = info.split('|')
    return infos[0].strip(), (infos[1].strip() if len(infos) > 1 else '')

def get_file_base_name(fname):
    """Returns file base name without extension"""
    if not fname:
        return ''
    name = os.path.basename(fname)
    return os.path.splitext(name)[0]

def plot_data(Xs, Ys, Names, Infos, no_yticks=False, title_suffix=''):
    """Plot one or more datasets"""
    import matplotlib.pyplot as plt
    models = {}
    for xdata, ydata, name, info in zip(Xs, Ys, Names, Infos):
        if info:
            units, model = split_file_info(info)
            name += ' [' + units + ']'
            if model:
                models[model] = None
        plt.plot(xdata, ydata, label=name)
    if len(Names) == 1:
        plt.title(Names[0])
    else:
        plt.legend()
    if no_yticks:
        plt.yticks([])
    canvas = plt.gcf().canvas
    if models:
        canvas.manager.set_window_title(', '.join(list(models.keys())) + title_suffix)
    Plotter.init_window_icon(canvas)
    Plotter.init_dbl_click_handler(canvas)
    plt.show()

def do_plot(args):
    """Just plots input files"""
    Xs, Ys, Names, Infos = [], [], [], []
    for fname in args.input_files:
        xdata, ydata, info = load_data_file(fname)
        Xs.append(xdata)
        Ys.append(ydata)
        Infos.append(info)
        Names.append(get_file_base_name(fname))
    plot_data(Xs, Ys, Names, Infos)

def do_stat(args):
    stat = StatCollector()
    with open(args.input_file, 'r') as f:
        for line in f:
            if line[:1] == '#':
                continue
            xy = line.split()
            if len(xy) != 2:
                continue
            try:
                x, y = float(xy[0]), float(xy[1])
            except ValueError:
                continue
            stat.account(y, x)
    stat.print(sys.stdout)

def do_hist(args):
    xdata, ydata, info = load_data_file(args.input_file, skip_nan=True)
    N = args.bins
    if not N: # provides meaningful default
        N = min(2 + len(xdata) // 4, 100)
    H, Cnt = histogram(ydata, N)
    outf = sys.stdout if not args.out_file else open(args.out_file, 'w')
    if args.out_file:
        outf = open(args.out_file, 'w')
        if info:
            print('#', info + ' [histogram]', file=outf)
    else:
        outf = sys.stdout
    for i in range(N):
        print('%f%s %f' % (H[i], args.delimiter, Cnt[i]), file=outf)
    if args.out_file:
        outf.close()
    if args.graph:
        plot_data([H], [Cnt], [get_file_base_name(args.input_file)], [info],
            no_yticks=True, title_suffix=' [histogram]')

def main(argv=None):
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    main_impl(argv)

def main_impl(argv=None):
    formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=40)
    parser = argparse.ArgumentParser(
            description='UNI-T UT61X+/UT60BT and OWON multimeters data acquisition and plotting tool',
            usage='%(prog)s [options] COMMAND [command options]',
            formatter_class=formatter
        )

    def get_help(args):
        parser.print_help()
        return 1

    parser.set_defaults(func=get_help)

    parser.register('type', 'hex-int', lambda s: int(s, 16))
    parser.add_argument('--VID', type='hex-int', required=False, metavar='HEX', default=None,
            help='device vendor id (optional)')
    parser.add_argument('--PID', type='hex-int', required=False, metavar='HEX', default=None,
            help='device product id (optional)')
    parser.add_argument('--path', '--addr', type=str, required=False,
            help='device path or Bluetooth mac address (optional, auto detect by default)')
    parser.add_argument('--tout', type=float, required=False, default=None, metavar='SECONDS',
            help='device read timeout (optional)')
    parser.add_argument('-B', '--bt', action='store_true',
            help='use Bluetooth for communicating with device')
    parser.add_argument('-M', '--model', type=str, required=False, metavar='NAME', default=None,
            help='BT device model (%s (default), %s)' % (UTDevice.model_name, UT60BTDevice.model_name))
    parser.add_argument('--name', type=str, required=False, default=None,
            help='set Bluetooth adapter name (optional)')
    parser.add_argument('--exit-prompt', action='store_true',
            help='wait Enter on exit')

    subparsers = parser.add_subparsers(metavar='COMMAND')
    subparser_prog = os.path.basename(sys.argv[0]) if argv else None
    subparsers.add_parser('list', prog=subparser_prog,
            help='list path for connected devices'
        ).set_defaults(func=do_list)
    subparsers.add_parser('once', prog=subparser_prog,
            help='get single reading'
        ).set_defaults(func=do_once)
    data_parser = subparsers.add_parser('data', prog=subparser_prog,
            help='read data continuously',
            formatter_class=formatter
        )
    data_parser.set_defaults(func=do_data)

    data_parser.add_argument('-i', '--interval', type=float, required=False, default=None, metavar='SECONDS',
            help='data acquisition interval (default is 1 sec)')
    data_parser.add_argument('-f', '--file', type=str, required=False, metavar='FILENAME',
            help='output file (optional, stdout by default), may have folder part and/or date time pattern and model name, like %%Y-%%m-%%d/%%H%%M%%S-${MODEL}.data')
    data_parser.add_argument('-a', '--alt-file', type=str, required=False, metavar='FILENAME',
            help='alternative channel output file name (for storing AC voltage in DC mode)')
    data_parser.add_argument('--keep-nan', action='store_true',
            help='keep invalid data values (NaN) resulting from overload (optional, discarding them by default)')
    data_parser.add_argument('-p', '--progress', action='store_true',
            help='show progress when writing to file')
    data_parser.add_argument('-o', '--offset', type=float, required=False, metavar='VALUE', default=0,
            help='set data offset')
    data_parser.add_argument('-m', '--mult', type=float, required=False, metavar='VALUE', default=1,
            help='set data multiplier')
    data_parser.add_argument('-e', '--epoch', action='store_true',
            help='use epoch timestamps (optional, use time since start by default)')
    data_parser.add_argument('-d', '--delimiter', type=str, default='', metavar='SYMBOL',
            help='data delimiter on output (optional, space by default)')
    data_parser.add_argument('-g', '--graph', action='store_true',
            help='show data graph')
    data_parser.add_argument('-w', '--wnd', type=int, required=False, metavar='SAMPLES',
            help='data graph window samples (optional, show all samples by default); press w to toggle')
    data_parser.add_argument('-z', '--with-zero', action='store_true',
            help='make sure the zero is within data graph vertical axis range; press z to toggle')
    data_parser.add_argument('-S', '--plot-stat', action='store_true',
            help='show statistic while plotting data; press t to toggle')
    data_parser.add_argument('-s', '--stat', action='store_true',
            help='output statistic upon termination')
    data_parser.add_argument('--plot-stat-loc', default='lower left', metavar='LOC',
            help='statistic box location on plot (optional, default is \'lower left\')')
    data_parser.add_argument('-t', '--title', type=str, required=False, metavar='TEXT',
            help='set data graph window title')
    data_parser.add_argument('--plot-title', type=str, required=False, metavar='TEXT',
            help='set data plot title')
    data_parser.add_argument('--alt-title', type=str, required=False, metavar='TEXT',
            help='set alternative channel data plot title')
    data_parser.add_argument('--full-screen', action='store_true',
            help='display the graph on the entire screen (use dbl-click to toggle)')
    data_parser.add_argument('--hline', type=float, metavar='VAL', action='append',
            help='draw horizontal line through the specified vertical axis value (may be used multiple times)')
    data_parser.add_argument('--alt-hline', type=float, metavar='VAL', action='append',
            help='draw horizontal line through the specified alternative channel vertical axis value (may be used multiple times)')
    data_parser.add_argument('--line-style', type=str, required=False, metavar='STR', default='-',
            help="line style specifier (optional, default is '-')")
    data_parser.add_argument('--hline-style', type=str, required=False, metavar='STR', default='--',
            help="horizontal line style specifier (optional, default is '--')")
    data_parser.add_argument('--line-color', type=str, required=False, metavar='STR', default='C0',
            help="line color specifier (optional, default is 'C0')")
    data_parser.add_argument('--alt-line-color', type=str, required=False, metavar='STR', default='C2',
            help="alternative channel line color specifier (optional, default is 'C2')")
    data_parser.add_argument('--hline-color', type=str, required=False, metavar='STR', default='C1',
            help="horizontal line color specifier (optional, default is 'C1')")
    data_parser.add_argument('--cfg-save', type=str, required=False, metavar='FILENAME',
            help='save command line options to the file with given name')
    data_parser.add_argument('-c', '--cfg-load', type=str, required=False, metavar='FILENAME',
            help='load command line options from the file with given name')

    plot_parser = subparsers.add_parser('plot', prog=subparser_prog,
            help='plot data file(s)'
        )
    plot_parser.set_defaults(func=do_plot)
    plot_parser.add_argument('input_files', nargs='+', help='list of input files')

    stat_parser = subparsers.add_parser('stat', prog=subparser_prog,
            help='print stat for existing data file'
        )
    stat_parser.set_defaults(func=do_stat)
    stat_parser.add_argument('input_file', help='input file')

    hist_parser = subparsers.add_parser('hist', prog=subparser_prog,
            help='make histogram for given data file',
            formatter_class=formatter
        )
    hist_parser.set_defaults(func=do_hist)
    hist_parser.add_argument('input_file', help='input file')
    hist_parser.add_argument('-g', '--graph', action='store_true',
            help='plot histogram graph')
    hist_parser.add_argument('-f', '--out-file', type=str, required=False, metavar='FILENAME',
            help='output file (optional, stdout by default)')
    hist_parser.add_argument('-b', '--bins', type=int, required=False, metavar='CNT',
            help='the number of bins')
    hist_parser.add_argument('-d', '--delimiter', type=str, default='', metavar='SYMBOL',
            help='data delimiter on output (optional, space by default)')

    args = parser.parse_args(argv)

    cfg_load_fname = getattr(args, 'cfg_load', None)
    if cfg_load_fname:
        with open(cfg_load_fname, 'r') as f:
            opts = json.loads(f.read())
        data_parser.set_defaults(func = args.func, **opts)
        args = parser.parse_args(argv)

    try:
        rc = args.func(args)
        if args.exit_prompt:
            print('\npress Enter to exit', file=sys.stderr)
            input()
        return rc
    except KeyboardInterrupt:
        return 0

def _main(conn, args, log_queue):
    global _parent_conn
    _parent_conn = conn
    if log_queue:
        sys.stdout = sys.stderr = open('.logs/dmm_out.log', 'w', encoding='utf-8')
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.handlers = []
        handler = logging.handlers.QueueHandler(log_queue)
        logger.addHandler(handler)
    else:
        logging.basicConfig(format='%(message)s', level=logging.INFO)
    main_impl(args)
