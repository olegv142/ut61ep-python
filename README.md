# The digital multimeter communication and data plotting tool supporting UNI-T UT61B/D/E+, UT60BT and several OWON Bluetooth multimeters

This repository provides simple alternative to vendor data collection programs. Since the code is written in python it may be easily incorporated onto your complex measuring or automation system. 

The project is inspired by https://github.com/ljakob/unit_ut61eplus and https://github.com/aroum/unit_ut61eplus_python.
The code was reworked with the following goals in mind:
 - keep code as small and simple as possible
 - support for USB HID and Bluetooth communication channel
 - support dual channel (DC+AC mode of UT61E+) reading and plotting
 - ensure seamless working on Windows and Linux
 - convenient working with several devices simultaneously
 - create simple CLI tool (**ut61xp-get**) for data collection and visualization
 - create GUI application (**ut61xp-start**) with the same capabilities as CLI tool
 - support for other multimeter vendors / models
 - make adding support for more model as simple as possible

## Supported devices

### UNI-T multimeters
- The UNI-T UT61E+ is high precision low cost digital multimeter with optically isolated USB interface which makes it perfect choice for hobbyist and professionals on tight budget.
The tool works via USB HID adapter D-09A commonly supplied with UT61X+ multimeter. Alternatively one can use UT-D07B Bluetooth adapter which provides the wireless communication channel at the expense of the lower communication speed. The minimum data readout interval is around 180 msec for USB adapter and around 800 msec for Bluetooth adapter. The BT adapter shows surprisingly good communication range. Its even able to communicate through the layer of reinforced concrete.
- The UT61B/D+ models are lower cost 6000 count versions sharing the same excellent DC voltage measuring accuracy of 10µV and having some additional features like thermocouple measuring (UT61D+).
- The UT60BT is consumer grade multimeter with built-in BT adapter using the same protocol as UT61X+ devices. It has even higher resolution than the UT61X+ in both millivolt and capacitance modes, with some caveats (see below).

### OWON multimeters
The tool supports the number of Bluetooth multimeters using the same 'BDM' protocol. In particular its tested with the following devices:
- The CM2100B clamp meter is inexpensive and quite versatile device capable of measuring AC or DC current without any electrical contact.
- The B41T+ is a multimeter with 22,000 counts and built-in Bluetooth. However, it is relatively expensive and has a number of disadvantages, including poor display quality and high power consumption when Bluetooth is enabled.
- The OW18B is a cheap, low resolution model with built in Bluetooth. However, it has better display and lower power consumption than B41T+.

Other compatible OWON multimeters like B35T+ and OW18E should work with this tool as well.

## Installation

```
git clone https://github.com/olegv142/ut61xpy.git
```

Alternatively you can download source code archive and unpack it. 
The code uses *hid/hidapi* package for communicating with USB multimeters, *bleak* package for communicating with Bluetooth multimeters and *matplotlib* package for data chart plotting. The can be installed by various ways depending on you operating system. To install the with pip (Windows):
```
pip install hidapi bleak matplotlib
```
On Linux you probably have to create virtual environment first or install packages using package manager like the following:
```
sudo apt install python3-hidapi python3-bleak python3-matplotlib
```
On some systems the package *python3-hid* is available instead of *python3-hidapi*. Note that you don't have to install the particular package unless you are not going to use the corresponding features. In particular, you can use the **ut61xp-get** tool without *matplotlib* package if you are not going to plot data charts. You can work without *bleak* package if you have only USB multimeters and without *hid/hidapi* package if you have only Bluetooth multimeters.

# Working with command line
The CLI workflow is built around **ut61xp-get** script which implements several commands for data acquisition, plotting and simple statistic analysis like making histogram and calculating momentums. The script has many command line options that we discuss briefly in the following sections. We first consider working with UNI-T UT61B/D/E+ multimeters via the standard USB HID adapter UT-D09A typically supplied with the device. After that we will consider working via Bluetooth and communicating with other supported multimeter models.

## Basic usage

The **ut61xp-get** will auto detect UT-D09A USB adapter provided that there is exactly one such adapter connected to your computer. The **ut61xp-get list** command prints paths for all connected adapters. The **ut61xp-get once** reads single value from the connected device and prints it to standard output. The **ut61xp-get data** reads values continuously from the connected device and either prints them or saves to the file if *-f/--file* option is provided. With *-p/--progress* option the tool will output dots to standard output while saving values to the file to indicate progress. In case the current reading is invalid (overflowed) the dot will be replaced by exclamation mark. To terminate data reading one can press Ctrl-C. The output file will contain time in seconds since readout start as the first column. With *-e/--epoch* option the epoch time will be used instead. One can use *-d/--delimiter* option to set additional delimiter to be used between columns which is the single space by default. With *-o/--offset, -m/--mult* options the data will be linearly scaled before saving / plotting. These options are handy to remove fixed offset from the data or to convert voltage across current sensing resistor to actual current value. The *-i/--interval* option may be used to specify data reading interval in seconds. Using zero value will result in reading with maximal possible rate.

## Automatic file naming

In case the file with the name provided with *-f* option already exists it will be silently overwritten. Therefore, you will either have to use a different name the next time you run data collection, or move the data file to a different location if you need it later. The **ut61xp-get** tool offers a convenient alternative: automatic file naming. In case the name given with *-f* option contains % character(s) it will be treated as the template for current date/time formatting as performed by [strftime](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior) function. Another useful feature is the possibility to add directory part to filename argument. The directory will be automatically created if not yet exists. For example with *-f %Y-%m-%d/%H%M%S.data* option the file with name representing current time will be placed to the directory with the name representing current date. In case the name given with *-f* option contains ${MODEL} substring, it will be replaced by the currently used multimeter model making filenames more informative.

## Dual channel mode

Dual channel mode is handy while reading data in DC+AC mode of UT61E+. To use this mode you will need to properly setup your device and specify filename for storing second channel by means of *-a/--alt-file* option. This may be convenient, but note that DC+AC mode has several peculiarities compared to other modes:
 - it takes ~0.7 sec to read single value of the single channel
 - the DC voltage channel fluctuates much more than in other modes
 - to ensure alternating reception of DC and AC readings, it is recommended to use the default sampling interval, which is set to zero in this mode

## Graph plotting

The **ut61xp-get data** command will plot data read from device in separate window if *-g/--graph* option is provided. To terminate data reading in such mode one can just close graph window. With dual channel mode the graph window will contain two plots. The *-w/--wnd* option may be used to limit the number of recent data samples utilized to produce the plot by the specific number. You can switch window mode on / off while plotting data by pressing 'w' hot key in the plot window. One can add any number of additional horizontal lines at specific levels to mark some specific value boundaries with *--hline* and *--alt-hline* options (the latter draws them on the second channel plot). These options may be used multiple times to add multiple horizontal lines. There are several other options that can be used for styling the graph window. One can set window title (*-t/--title*), plot title (*--plot-title, --alt-title*), data line style (*--line-style*), horizontal line style (*--hline-style*), data line colors (*--line-color, --alt-line-color*), horizontal line color (*--hline-color*). In case plot title is not provided as command line argument the current measuring mode reported by multimeter will be used as the title. In case window title is not provided as command line argument the multimeter model will be used as the title. You can use plot navigation bar as usual. In particular, you can use pan/zoom controls of the graph window while reading the data or use the dedicated button to save plot to the file, yet the acquisition will be paused until you done with plot saving. Additionally double clicking the plot will toggle full screen mode. To open the graph window in full screen mode from the start, you can use the *--full-screen* command line option. With '-z/--with-zero' the zero value will always be included in the displayed vertical axis range. This will help to understand the scale of the signal fluctuations with respect to the signal value. Pressing 'z' key in plot window switches 'with-zero' mode on / off regardless of the '-z/--with-zero' option.

## Plotting already collected data

The **ut61xp-get plot** command followed by the list of filenames plots the data sets reading them from the given files. It is just a convenient tool for viewing the collected data without any complex charting features. You can use plot navigation bar as usual and use double click to toggle full screen mode.

## Data units and scaling

The data reported by multimeter typically contains information about measurement mode (say voltage) and/or measurement units (say millivolts). The units may be voluntary changed by the device as a result of the automatic range selection (for ex. millivolts to volts). Many vendor provided and third party data readout applications just save data in the units reported by device. This practice is bad since the data with sudden change of units will show abrupt jump with several orders of magnitude and will look as a mess overall. The **ut61xp-get** tool takes special care to guarantee that the units of the data will be the same no matter how auto-ranging works on the particular device. The particular units used for the data representation will be shown as the default plot title with *-g* option and will be saved in the first line of the output file with *-f* or *-a* options.

## Using configurations

The configuration is the file storing the full set of command line options in the form of json dictionary. Use *--cfg-save* option with **ut61xp-get data** command to create such file filled with options specified in the current command line and *-c/--cfg-load* option to load such file back. They may be handy to save typing and even more importantly to make data acquisition from several devices easier. Several examples of using them while reading data from several devices simultaneously will be given below.

## Printing data statistics

With *-s/--stat* option the **ut61xp-get data** command will print various collected data statistic metrics upon acquisition termination. In particular:
 - the number of data samples (total and valid)
 - the min / max values
 - the median and pure average values
 - the standard deviation (absolute and relative)
 - the integral in val * sec units
 - the 3rd central moment relative to the standard deviation (*skewness*)
 - the 4th central moment relative to the standard deviation minus 3 (*kurtosis exess*)

The last two metrics may be used to characterize deviations from the mean. The smaller they are the close the values distribution to the standard one with *Gaussian* noise.

### Print statistics while plotting data

With *-S/--plot-stat* option the **ut61xp-get data** command will show data statistics on the plot window and update it on every new data sample. The *--plot-stat-loc* option may be used to specify the particular location on the plot where the statistics box will be placed. The default is 'lower left'. With *--plot-stat-loc "best"* options the location will be chosen automatically to minimize overlapping with data curve. The statistic display area may be shown / hidden while plotting by pressing 't' key. This hot key works regardless of the *-S/--plot-stat* option.
Another way to view current statistics is to press the space bar in the chart window. This will print the statistics on the terminal so you can easily copy / paste them.

### Print statistics given the existing data file

The **ut61xp-get stat input_file** command prints statistics of the data stored in the given *input_file*.

## Plot window hotkeys
The following keys (partially discussed above) have special meaning when pressed in the data plot window:
| key   | meaning                                                                                    |
|-------|--------------------------------------------------------------------------------------------|
| space | print current statistics to terminal so you can easily copy/paste them                     |
| t     | show / hide statistics display area on the plot                                            |
| w     | turn data window on / off (provided that it was initially configured by *-w/--wnd* option) |
| z     | turn on / off 'with-zero' mode                                                             |
| s     | opens file chooser dialog to save plot as an image                                         |
| q     | close plot window                                                                          |

## Working with data histograms

The **ut61xp-get hist input_file** command creates histogram for the given input file. It either prints it to standard output or saves to the file if *-f/--out-file* option is given. The output data formatting may be customized by *-d/--delimiter* option. The *-b/--bins* option may be used to set the required number of bins in the histogram. With *-g/--graph* the histogram will be plotted in the separate window. One can plot the histogram saved to the file by  **ut61xp-get plot** command as any other data file.

## Getting help

Execute **ut61xp-get** tool with *-h* option to get detailed information about command line options. On Windows:
```
python ut61xpy/ut61xp-get -h
python ut61xpy/ut61xp-get data -h
python ut61xpy/ut61xp-get hist -h
```
On Linux the following will work either:
```
./ut61xpy/ut61xp-get -h
./ut61xpy/ut61xp-get data -h
./ut61xpy/ut61xp-get hist -h
```

## Working with several devices simultaneously

Suppose we have UT61E+ and UT61D+ devices and are going to read data from them simultaneously. We use different models just for illustrative purpose, they may be the same. We can find out path to each device by connecting them one by one and using **ut61xp-get list** command. After that we can pass the path to **ut61xp-get data** command like *ut61xp-get --path PATH data OPTIONS* but it takes a lot of typing. Using configurations may make life easier. One can do the following
1. Connect first device (UT61E+) only and issue the command:
```
python ut61xpy/ut61xp-get data -gps -f e.data -t UT61E+ --cfg-save ut61e.cfg
```
It will auto detect device, plot the data saving it to the file e.data, showing a progress and printing stats on termination. It will also create the configuration file ut61e.cfg. The *-t* option will set window title so we can tell which window shows data from which device.

2. Disconnect first device and connect other device (UT61D+) and run the command:
```
python ut61xpy/ut61xp-get data -gps -f d.data -t UT61D+ --cfg-save ut61d.cfg 
```
The corresponding configuration will be saved to ut61d.cfg

3. Now we can connect both devices and run some acquisition in parallel (in separate terminals):
```
python ut61xpy/ut61xp-get data -c ut61d.cfg -i 0
python ut61xpy/ut61xp-get data -c ut61e.cfg -a a.data
```
The first command will read data from UT61D+ at maximum rate. The second command will acquire data from UT61E+ in DC+AC mode.

4. One can even create specialized configuration file for DC+AC mode by modifying basic configuration:
```
python ut61xpy/ut61xp-get data -c ut61e.cfg -a a.data --cfg-save acdc.cfg
```
Now one can just execute the following short command line to use DC+AC readout with dual plot graph:
```
python ut61xpy/ut61xp-get data -c acdc.cfg
```
Of cause the *./ut61xpy/ut61xp-get* invocation will work on Linux as well since *ut61xp-get* is executable script on this system.
Note that to be able to combine measurements made by different devices you will probably have to use epoch time option (*-e*). Otherwise data samples originated from different devices may be read at different time even if they have the same time stamp (since its relative to acquisition start of the particular readout session).

## Device paths and Windows/Linux peculiarities

The configuration tricks shown above work just because the auto-detected device path becomes part of the configuration saved with *--cfg-save* option. One can check that by looking at the configuration file content saved as text. But what is the device path after all? It turns out that on Windows it contains some unique device identifier but on Linux it depends only on the USB port where the device is attached. So its critically important to use different ports for different devices and always use the same port for the particular device while working with configurations / device paths on Linux.

## Using Bluetooth adapter

Working with Bluetooth adapter conceptually is not different from using USB. Just add *-B/--bt* option right after *ut61xp-get* to force script to use BT adapter. Similar to USB use case the script is able to auto detect BT adapter provided that its powered on and no other adapters are in the accessible range. By means of using the *--cfg-save* option one can save the address of the adapter discovered (which plays the role of USB device path) for the subsequent reuse. One can specify BT address in the command line explicitly via *--path/--addr* option. Opening BT device by its address is significantly faster and more reliable than autodetecting it.

## Working with other supported devices

By default, the **ut61xp-get** tool always expects the UT61X+ multimeter as the target device. To change this, one can use *-M/--model* option. Please note that if device works via Bluetooth, the *-B* option must be provided with *-M/--model* option.

### UT60BT
The UT60BT is inexpensive consumer grade multimeter with built-in BT adapter using the same protocol as UT61X+ devices. It has even better resolution than UT61X+ of 1pF in capacitance mode and 1µV in millivolt mode. Unfortunately, this latter advantage is offset by an annoying hack. To hide fluctuations in readings, the device uses a dead band from -10 µV to +10 µV, where the voltage is always read as zero. Similar dead band exists in A mode between -5mA and +5mA in both UT60BT and UT61X+.

To read from UT60BT one can supply *-B -M UT60BT* options right after **ut61xp-get** in the command line.

### OWON multimeters
To read from OWON multimeter using 'BDM' protocol one can supply *-B -M OWON* options right after **ut61xp-get** in the command line.

### Adding your own device
To add new device you should implement its adapter class inherited from *Device* and *BTMixin* or *HIDMixin* from **device.py**. Then the class type should be added to *_supported_devices* from **ut61xp-get** and that's it.
In case the device is using already supported protocol but having different USB VIP/PID or Bluetooth device name, one can try to connect to it by tweaking these parameters specifying *--VID, --PID, --name* command line options.

# Working with GUI
The GUI workflow is built around **ut61xp-start** script that provides convenient UI for setting **ut61xp-get** options and launching data acquisition in separate processes. The single instance of **ut61xp-start** UI can launch any number of data acquisition processes working in parallel, saving data to separate files and showing collected data in their own data plot windows.
