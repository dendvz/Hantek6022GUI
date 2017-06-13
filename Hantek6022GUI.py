#!/usr/bin/env python

import matplotlib as mpl
mpl.use('TkAgg')

from numpy import arange, sin, pi
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from matplotlib.backend_bases import key_press_handler
from PyHT6022.LibUsbScope import Oscilloscope

import sys
if sys.version_info[0] < 3:
  import Tkinter as Tk
else:
  import tkinter as Tk
import ttk
import tkFont, tkColorChooser

# Global variables
global fontNormal
global fontFixed

class CONST:
  CH1, CH2 = range(2)
  MIN_X = 0
  MAX_X = 1000
  MIN_Y = -4
  MAX_Y = 4

'''
    SAMPLE_RATES = {0x0A: ("100 KS/s", 100e3),
                    0x14: ("200 KS/s", 200e3),
                    0x32: ("500 KS/s", 500e3),
                    0x01: ("1 MS/s", 1e6),
                    0x04: ("4 MS/s", 4e6),
                    0x08: ("8 MS/s", 8e6),
                    0x10: ("16 MS/s", 16e6),
                    0x30: ("24 MS/s", 24e6)}

    VOLTAGE_RANGES = {0x01: ('+/- 5V', 0.0390625, 2.5),
                      0x02: ('+/- 2.5V', 0.01953125, 1.25),
                      0x05: ('+/- 1V', 0.0078125, 0.5),
                      0x0a: ('+/- 500mV', 0.00390625, 0.25)}

'''


################################################################################
class Selector(Tk.Spinbox):

  def __init__(self, master, values, callback = None):
    self.callback = callback
    self.boundVar = Tk.StringVar(master)

    # check whether values is list of strings, or list of (key, value) tuples
    # create self.values as list of (key, value) pairs
    self.values = []
    width = 0
    for i in range(len(values)):
      if isinstance(values[i], basestring):
        self.values.append([i, ' {} '.format(values[i])])
        width = max(width, len(values[i]) + 2)
      else:
        self.values.append([values[i][0], ' {} '.format(values[i][1])])
        width = max(width, len(values[i][1]) + 2)

    Tk.Spinbox.__init__(self,
      master,
      state = 'readonly',
      exportselection = False,
      takefocus = False,
      font = fontFixed,
      width = width,
      justify = Tk.RIGHT,
      values = [item[1] for item in self.values],
      command = self.update,
      textvariable = self.boundVar
    )

  def get(self):
    return [item[0] for item in self.values if item[1] == self.boundVar.get()][0]

  def set(self, itemIndex):
    for item in self.values:
      if item[0] == itemIndex:
        self.boundVar.set(item[1])
        break

  def update(self):
    if self.callback:
      self.callback(self.get())

################################################################################
class TimeBaseControl:

  SAMPLE_RATES = [
    0x0A, # 100 KS/s
    0x14, # 200 KS/s
    0x32, # 500 KS/s
    0x01, #   1 MS/s
    0x04, #   4 MS/s
    0x08, #   8 MS/s
    0x10, #  16 MS/s
    0x30  #  24 MS/s
  ]

  H_SCALE = [
    # tb_value,  tb_text,    sample_rate
    (   5E-03, '  5 ms/div', 100E+03 ),
    (   2E-03, '  2 ms/div', 100E+03 ),
    (   1E-03, '  1 ms/div', 100E+03 ),
    ( 500E-06, '500 us/div', 200E+03 ),
    ( 200E-06, '200 us/div', 500E+03 ),
    ( 100E-06, '100 us/div',   1E+06 ),
    (  50E-06, ' 50 us/div',   1E+06 ),
    (  20E-06, ' 20 us/div',   4E+06 ),
    (  10E-06, ' 10 us/div',   8E+06 ),
    (   5E-06, '  5 us/div',  16E+06 ),
    (   2E-06, '  2 us/div',  24E+06 ),
    (   1E-06, '  1 us/div',  24E+06 ),
    ( 500E-09, '500 ns/div',  24E+06 ),
    ( 200E-09, '200 ns/div',  24E+06 ),
    ( 100E-09, '100 ns/div',  24E+06 )
  ]

  def __init__(self, device, master, callback = None):

    self.device = device
    self.callback = callback

    frame = Tk.LabelFrame(master,
      text = 'Timebase',
      font = fontNormal,
      labelanchor = Tk.N,
      padx = 5,
      pady = 5
    )
    frame.grid()

    self.timeBase = Selector(frame,
      values = self.H_SCALE,
      callback = self.update
    )
    self.timeBase.grid(row = 0, sticky = 'NEWS')

    frame.rowconfigure(0, minsize = 40)

    self.timeBase.set(500E-06)
    self.update()

  def update(self, value = None):
    if value == None:
      value = self.timeBase.get()
    for item in self.H_SCALE:
      if value == item[0]:
        self.sampleRateIndex = filter(
          lambda i: self.device.SAMPLE_RATES[i][1] == item[2],
          self.SAMPLE_RATES
        )[0]
        break
    if self.callback:
      self.callback()

  def getSampleRate(self):
    return self.device.SAMPLE_RATES[self.sampleRateIndex][1]

################################################################################
class ChannelControl:

  V_SCALE = [
    # value  text          _x1   _x10
    ( 50.0, ' 50  V/div',     0, 0x01 ),
    ( 20.0, ' 20  V/div',     0, 0x01 ),
    ( 10.0, ' 10  V/div',     0, 0x02 ),
    (  5.0, '  5  V/div',  0x01, 0x05 ),
    (  2.0, '  2  V/div',  0x01, 0x0a ),
    (  1.0, '  1  V/div',  0x02, 0x0a ),
    (  0.5, '500 mV/div',  0x05,    0 ),
    (  0.2, '200 mV/div',  0x0a,    0 ),
    (  0.1, '100 mV/div',  0x0a,    0 )
  ]

  V_LIMIT = {
    'x1_min'  :  0.1,
    'x1_max'  :  5.0,
    'x10_min' :  1.0,
    'x10_max' : 50.0
  }

  def __init__(self, device, master, channelIndex, callback = None):

    self.device = device
    self.channelIndex = channelIndex
    self.master = master
    self.callback = callback
    self.probe = 1
    self.trigger = 0.5

    if channelIndex == CONST.CH1:
      self.color = '#ffff00'
      self.position = 2
    elif channelIndex == CONST.CH2:
      self.color = '#00ffff'
      self.position = -2
    else:
      self.color = '#ffffff'
      self.position = 0.0

    frame = Tk.LabelFrame(master,
      text = 'CH{:1d}'.format(channelIndex),
      font = fontNormal,
      labelanchor = Tk.N,
      padx = 5,
      pady = 5
    )
    frame.grid()

    self.colorChooser = Tk.Button(frame,
      text = self.color,
      font = fontFixed,
      activebackground = self.color,
      activeforeground = 'black',
      background = self.color,
      foreground = self.color,
      command = self.setColor
    )
    self.colorChooser.grid(row = 0, columnspan = 2, sticky = 'NEWS', pady = 5)

    self.voltage = Selector(frame,
      values = self.V_SCALE,
      callback = self.setVoltageRange
    )
    self.voltage.grid(row = 1, columnspan = 2, sticky = 'NEWS')

    Tk.Label(frame, text = 'Probe', font = fontNormal).grid(row = 2, columnspan = 2, sticky = 'S')

    self.probeVar = Tk.IntVar(master)
    self.probeVar.trace(mode = 'w', callback = self.onTrace)

    probeX1 = Tk.Radiobutton(frame,
      text = "x1",
      font = fontFixed,
      variable = self.probeVar,
      indicatoron = 0,
      value = 1
    ).grid(row = 3, sticky = 'NEWS')

    probeX10 = Tk.Radiobutton(frame,
      text = "x10",
      font = fontFixed,
      variable = self.probeVar,
      indicatoron = 0,
      value = 10
    ).grid(row = 3, column = 1, sticky = 'NEWS')

    # TODO: Load settings from file
    self.probeVar.set(1)
    self.voltage.set(1.0)

    frame.rowconfigure(1, minsize = 40)
    frame.rowconfigure(2, minsize = 30)
    frame.rowconfigure(3, minsize = 40)

  def onTrace(self, varname, elementname, mode):
    if varname == str(self.probeVar):
      self.update(probe = self.probeVar.get())

  def setVoltageRange(self, value):
    self.update(voltage = value)

  def update(self, probe = None, voltage = None):
    if probe:
      self.probe = probe
      if self.probe == 10:
        self.voltage.set(self.voltage.get() * 10.0)
        self.voltage.set(max(self.voltage.get(), self.V_LIMIT['x10_min']))
        self.voltage.set(min(self.voltage.get(), self.V_LIMIT['x10_max']))
      elif self.probe == 1:
        self.voltage.set(self.voltage.get() / 10.0)
        self.voltage.set(max(self.voltage.get(), self.V_LIMIT['x1_min']))
        self.voltage.set(min(self.voltage.get(), self.V_LIMIT['x1_max']))
    elif voltage:
      if self.probe == 10:
        self.voltage.set(voltage)
        self.voltage.set(max(self.voltage.get(), self.V_LIMIT['x10_min']))
        self.voltage.set(min(self.voltage.get(), self.V_LIMIT['x10_max']))
      elif self.probe == 1:
        self.voltage.set(voltage)
        self.voltage.set(max(self.voltage.get(), self.V_LIMIT['x1_min']))
        self.voltage.set(min(self.voltage.get(), self.V_LIMIT['x1_max']))

    if self.callback:
      self.callback()

  def setColor(self):
    _, color = tkColorChooser.askcolor(
      parent = self.master,
      initialcolor = self.color,
      title = 'CH{} Color'.format(self.channelIndex)
    )
    if color:
      self.color = color
      self.colorChooser.config(text = color,
        background = color,
        foreground = color,
        activebackground = color
      )

  def getVoltageRange(self):
    voltage = self.voltage.get()
    if self.probe == 10:
      for item in self.V_SCALE:
        if voltage == item[0]:
          return item[3]
    elif self.probe == 1:
      for item in self.V_SCALE:
        if voltage == item[0]:
          return item[2]
    return 0

  def getScaleFactor(self):
    return self.probe * self.device.VOLTAGE_RANGES[self.getVoltageRange()][2] / self.voltage.get()

class Reader:
  def __init__(self, device, tb, ch1, ch2):
    self.device = device
    self.tb     = tb
    self.ch1    = ch1
    self.ch2    = ch2
    self.sampleCount = 0x400
    device.setup()

  def acquire(self):
    data_points = 0x400
    self.sampleCount = min(int(10 * self.tb.getSampleRate() * self.tb.timeBase.get()), data_points)

    try:
      self.device.open_handle()
      self.device.set_sample_rate(self.tb.sampleRateIndex)
      self.device.set_ch1_voltage_range(self.ch1.getVoltageRange())
      self.device.set_ch2_voltage_range(self.ch2.getVoltageRange())

      self.ch1_data, self.ch2_data = self.device.read_data(data_points)
      self.device.close_handle()
    except AssertionError:
      t = arange(0.0, float(data_points), 1.0)
      # samples per oscillation (1kHz)
      spo = self.device.SAMPLE_RATES[self.tb.sampleRateIndex][1] / 1e3
      k1 = 127
      k2 = 127
      self.ch1_data = k1 * sin((2 * pi / spo) * t) + 128
      self.ch2_data = [k2 * (1 - int(2 * i / spo) % 2) + 128 for i in range(data_points)]

  def getData(self, channelIndex = None):
    bias = 0x80
    if channelIndex == None:
      scaleFactor = 1000.0 / float(self.sampleCount)
      return [i * scaleFactor for i in range(self.sampleCount)]
    elif channelIndex == CONST.CH1:
      scaleFactor = self.ch1.getScaleFactor() / bias
      print "scaleFactor 1 =", scaleFactor
      return [self.ch1.position + (v - bias) * scaleFactor for v in self.ch1_data[:self.sampleCount]]
    elif channelIndex == CONST.CH2:
      scaleFactor = self.ch2.getScaleFactor() / bias
      print "scaleFactor 2 =", scaleFactor
      return [self.ch2.position + (v - bias) * scaleFactor for v in self.ch2_data[:self.sampleCount]]
    else:
      return []

class MainApp:

  def __init__(self):

    global fontNormal
    global fontFixed

    self.root = Tk.Tk()
    self.root.wm_title("Hantek")

    self.root.rowconfigure(0, weight = 1)
    self.root.columnconfigure(0, weight = 1)

    fontNormal = tkFont.Font(family = 'Sans', size = 12)
    fontFixed  = tkFont.Font(family = 'Mono', size = 12)

    self.controlPanel = Tk.Frame(self.root)
    self.createControlPanel(self.controlPanel)

    self.plotArea = Tk.Frame(self.root, borderwidth = 6)
    self.createPlotArea(self.plotArea)

    # Layout
    self.controlPanel.grid(row = 0, column = 1, sticky = 'news', padx = 5, pady = 5)
    self.plotArea.grid(row = 0, column = 0, sticky = 'news')

    self.traces = []
    self.acquire()

    Tk.mainloop()

  def createPlotArea(self, frame):

    f = mpl.figure.Figure(figsize = (10, 8), facecolor = 'k')
    f.subplots_adjust(left = 0.05, bottom = 0.15, right = 0.95, top = 0.95)

    self.axes = f.add_subplot(111)
    self.axes.set_axis_bgcolor('k')

    self.axes.set_xlim((CONST.MIN_X, CONST.MAX_X), auto = False)
    self.axes.set_ylim((CONST.MIN_Y, CONST.MAX_Y), auto = False)
    self.axes.tick_params(
      which       = 'both',
      labelbottom = False,
      labeltop    = False,
      labelleft   = False,
      labelright  = False
    )
    self.axes.set_axisbelow(False)

    self.axes.set_xticks([(CONST.MIN_X + CONST.MAX_X) / 2], minor = False)
    self.axes.set_xticks([100 * x for x in range(10) if x % 5 != 0], minor = True)

    self.axes.set_yticks([(CONST.MIN_Y + CONST.MAX_Y) / 2], minor = False)
    self.axes.set_yticks([y for y in range(CONST.MIN_Y, CONST.MAX_Y) if y % 4 != 0], minor = True)

    self.axes.grid(b = True, which = 'major', color = 'w', linestyle = '-')
    self.axes.grid(b = True, which = 'minor', color = 'w', linestyle = ':')

    border = mpl.patches.Rectangle(
      [CONST.MIN_X, CONST.MIN_Y],
      width  = CONST.MAX_X - CONST.MIN_X,
      height = CONST.MAX_Y - CONST.MIN_Y,
      color = 'w',
      fill = False,
      linewidth = 2
    )

    self.axes.add_patch(border)
    border.set_clip_on(False)

    self.canvas = FigureCanvasTkAgg(f, master = frame)
    self.canvas.show()
    self.canvas.get_tk_widget().pack(fill = Tk.BOTH, expand = 1)
    self.drawMarker(
      direction = Tk.RIGHT,
      position = self.ch1.position,
      color = self.ch1.color,
      text = 'CH{}'.format(self.ch1.channelIndex + 1)
    )
    self.drawMarker(
      direction = Tk.RIGHT,
      position = self.ch2.position,
      color = self.ch2.color,
      text = 'CH{}'.format(self.ch2.channelIndex + 1)
    )
    self.drawMarker(
      direction = Tk.LEFT,
      position = 3,
      color = self.ch1.color,
      text = 'TR{}'.format(self.ch1.channelIndex + 1)
    )
    self.drawMarker(
      direction = Tk.LEFT,
      position = -1,
      color = self.ch2.color,
      text = 'TR{}'.format(self.ch2.channelIndex + 1),
      alpha = 0.15
    )
    self.drawMarker(
      direction = Tk.BOTTOM,
      position = 30,
      color = 'w',
      text = 'T'
    )
    # Cursors
    self.drawMarker(
      direction = Tk.TOP,
      position = 250,
      color = 'w',
      text = '1',
      alpha = 0.5
    )
    self.drawMarker(
      direction = Tk.TOP,
      position = 620,
      color = 'w',
      text = '2',
      alpha = 0.5
    )
    self.drawChannelInfo(0)
    self.drawChannelInfo(1)

#    timeBase = self.reader.getData()
#    self.ch1trace, self.ch2trace = self.axes.plot(
#      timeBase, self.reader.getData(CONST.CH1), self.ch1.color,
#      timeBase, self.reader.getData(CONST.CH2), self.ch2.color
#    )

  def drawMarker(self, direction = Tk.RIGHT, position = 0, color = 'w', text = '', alpha = 1.0):
    if direction == Tk.LEFT:
      tipX = CONST.MAX_X
      tipY = position
      offX = 0.05 * (CONST.MAX_X - CONST.MIN_X)
      offY = 0
    elif direction == Tk.RIGHT:
      tipX = CONST.MIN_X
      tipY = position
      offX = -0.05 * (CONST.MAX_X - CONST.MIN_X)
      offY = 0
    elif direction == Tk.TOP:
      tipX = position
      tipY = CONST.MIN_Y
      offX = 0
      offY = -0.05 * (CONST.MAX_Y - CONST.MIN_Y)
    elif direction == Tk.BOTTOM:
      tipX = position
      tipY = CONST.MAX_Y
      offX = 0
      offY = 0.05 * (CONST.MAX_Y - CONST.MIN_Y)
    else:
      return

    self.axes.annotate(
      '',
      xy = (tipX, tipY),
      xytext = (tipX + offX, tipY + offY),
      ha = "center",
      va = "center",
      size = 10,
      arrowprops = dict(
        arrowstyle='simple, head_width=1.4, tail_width=1.4',
        fc = color,
        ec = color,
        connectionstyle = "arc3",
        clip_on = False,
        alpha = alpha
      )
    )
    self.axes.text(
      tipX + offX / 1.8,
      tipY + offY / 1.8,
      text,
      color = 'k',
      weight = 'bold',
      size = 11,
      ha = "center",
      va = "center"
    )

  def drawChannelInfo(self, channelIndex):
    if channelIndex == 0:
      color = self.ch1.color
    else:
      color = self.ch2.color

    self.axes.text(
      0,
      -4.75 - 0.5 * channelIndex,
      'CH{} Info'.format(channelIndex + 1),
      color = color,
      size = 16,
      ha = "center",
      va = "center",
      clip_on = False
    )
#    ch1_info = Tk.Label(self.root, text = 'Ch1 Info...', anchor = Tk.W, font = fontFixed, bg = 'black', fg = self.ch1.color)
#    ch1_info.grid(row = 1, sticky = 'news')
#    ch2_info = Tk.Label(self.root, text = 'Ch2 Info...', anchor = Tk.W, font = fontFixed, bg = 'black', fg = self.ch2.color)
#    ch2_info.grid(row = 2, sticky = 'news')

  


  def createControlPanel(self, frame):

    self.device = Oscilloscope()
    self.reader = None

    self.ch1 = ChannelControl(self.device, frame, CONST.CH1, self.acquire)
    self.ch2 = ChannelControl(self.device, frame, CONST.CH2, self.acquire)
    self.tb = TimeBaseControl(self.device, frame, self.acquire)

    self.reader = Reader(self.device, self.tb, self.ch1, self.ch2)

#    Tk.Button(frame, text = 'acquire', command = self.acquire).grid()

    # TODO: Load settings from config file
#    self.timeBase.set(100E-6)
#    self.sampleRate.set(0x10)

  # This stuff does not work yet
  def acquire(self):
    if self.reader:
      self.reader.acquire()

      if len(self.traces) == 0:
#      self.ch1trace.set_ydata(self.reader.getData(CONST.CH1))
#      self.ch2trace.set_ydata(self.reader.getData(CONST.CH2))
        t = self.reader.getData()
        self.traces = self.axes.plot(
          t, self.reader.getData(CONST.CH1), self.ch1.color,
          t, self.reader.getData(CONST.CH2), self.ch2.color
        )
      else:
        print "len=", len(self.traces)

  def quit(self):
    self.root.quit()     # stops mainloop
    self.root.destroy()  # this is necessary on Windows to prevent
                         # Fatal Python Error: PyEval_RestoreThread: NULL tstate

### main

mainApp = MainApp()
