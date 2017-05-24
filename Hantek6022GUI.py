#!/usr/bin/env python

import matplotlib as mpl
#matplotlib.use('TkAgg')

from numpy import arange, sin, pi
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from PyHT6022.LibUsbScope import Oscilloscope

import sys
if sys.version_info[0] < 3:
  import Tkinter as Tk
else:
  import tkinter as Tk
import ttk
import tkFont

# Global variables
global fontNormal
global fontFixed

################################################################################
class Selector(Tk.Spinbox):

  def __init__(self, master, values, callback = None):
    self.callback = callback
    self.boundVar = Tk.StringVar(master)
    self.boundVar.trace(mode = 'w', callback = self.onTrace)

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
      textvariable = self.boundVar
    )

  def get(self):
    for item in self.values:
      if item[1] == self.boundVar.get():
        return item[0]
    return None

  def set(self, itemIndex):
    for item in self.values:
      if item[0] == itemIndex:
        self.boundVar.set(item[1])
        break

  def onTrace(self, varname, elementname, mode):
    if varname == str(self.boundVar) and self.callback:
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

  def __init__(self, device, master):

    sampleRateList = []
    for key in self.SAMPLE_RATES:
      sampleRateList.append([key, device.SAMPLE_RATES[key][0]])

    frame = Tk.LabelFrame(master,
      text = 'Horizontal',
      font = fontNormal,
      labelanchor = Tk.N,
      padx = 5,
      pady = 5
    )
    frame.grid()

    Tk.Label(frame, text = "Timebase", font = fontNormal).grid(sticky = Tk.S)

    self.timeBase = Selector(frame,
      values = self.H_SCALE,
      callback = self.setTimeBase
    )
    self.timeBase.grid(row = 1, sticky = 'NEWS')

    Tk.Label(frame, text = "Sample Rate", font = fontNormal).grid(row = 2, sticky = Tk.S)

    self.sampleRate = Selector(frame,
      values = sampleRateList,
      callback = self.setSampleRate
    )
    self.sampleRate.grid(row = 3, sticky = 'NEWS')

    frame.rowconfigure(0, minsize = 30)
    frame.rowconfigure(1, minsize = 40)
    frame.rowconfigure(2, minsize = 30)
    frame.rowconfigure(3, minsize = 40)

    self.timeBase.set(5e-6)

  def setTimeBase(self, value):
    print("setTimeBase", value)

  def setSampleRate(self, value):
    print("setSampleRate", value)

################################################################################
class ChannelControl:

  VOLTAGE_RANGES = [
    0x01, # +/- 5.0 V
    0x02, # +/- 2.5 V
    0x05, # +/- 1.0 V
    0x0a  # +/- 0.5 V
  ]

  V_SCALE = [
    # value  text          range  scale
    ( 50.0, ' 50  V/div',  0x01,  0.4 ),
    ( 20.0, ' 20  V/div',  0x01,  1.0 ),
    ( 10.0, ' 10  V/div',  0x02,  1.0 ),
    (  5.0, '  5  V/div',  0x01,  0.4 ),
    (  2.0, '  2  V/div',  0x01,  1.0 ),
    (  1.0, '  1  V/div',  0x02,  1.0 ),
    (  0.5, '500 mV/div',  0x05,  1.0 ),
    (  0.2, '200 mV/div',  0x0a,  1.0 ),
    (  0.1, '100 mV/div',  0x0a,  2.0 )
  ]

  def __init__(self, device, channelIndex, master, callback = None):

    self.device = device
    self.channelIndex = channelIndex
    self.callback = callback

    frame = Tk.LabelFrame(master,
      text = 'CH{:1d}'.format(channelIndex),
      font = fontNormal,
      labelanchor = Tk.N,
      padx = 5,
      pady = 5
    )
    frame.grid()

    self.voltage = Selector(frame,
      values = self.V_SCALE,
      callback = self.setVoltageRange
    )
    self.voltage.grid(row = 0, columnspan = 2, sticky = 'NEWS')

    Tk.Label(frame, text = 'Probe', font = fontNormal).grid(row = 1, columnspan = 2, sticky = Tk.S)

    self.probeVar = Tk.IntVar()
    self.probeVar.trace(mode = 'w', callback = self.onTrace)

    probeX1 = Tk.Radiobutton(frame,
      text = "x1",
      font = fontFixed,
      variable = self.probeVar,
      indicatoron = 0,
      value = 1
    ).grid(row = 2, sticky = 'NEWS')

    probeX10 = Tk.Radiobutton(frame,
      text = "x10",
      font = fontFixed,
      variable = self.probeVar,
      indicatoron = 0,
      value = 10
    ).grid(row = 2, column = 1, sticky = 'NEWS')

    # TODO: Load settings from file
    self.probeVar.set(1)
    self.voltage.set(2.0)

    frame.rowconfigure(0, minsize = 40)
    frame.rowconfigure(1, minsize = 30)
    frame.rowconfigure(2, minsize = 40)

  def onTrace(self, varname, elementname, mode):
    if varname == str(self.probeVar):
      print('probeVar({})'.format(self.channelIndex), self.probeVar.get())
      self.update()

  def setVoltageRange(self, value):
    print('setVoltageRange({})'.format(self.channelIndex), value)
    self.update()

  def update(self):
    if self.probeVar.get() == 10:
      if self.voltage.get() < 1.0:
        self.voltage.set(1.0)
    else:
      if self.voltage.get() > 5.0:
        self.voltage.set(1.0)

class PlotArea:
  def __init__(self, master):
    self.master = master
    f = Figure(tight_layout = True)
    a = f.add_subplot(111)
    a.set_axis_bgcolor('k')

    t = arange(0.01, 6.0, 0.01)
    s = sin(2*pi*t) / (2*pi*t)

    a.plot(t, s)

    # a tk.DrawingArea

    self.panel = Tk.Frame(master)
    self.panel.pack()

    self.canvas = FigureCanvasTkAgg(f, master = self.panel)
    self.canvas.show()
    self.canvas.get_tk_widget().pack(side = Tk.LEFT, fill = Tk.BOTH, expand = 1)

class MainApp:

  def __init__(self):

    global fontNormal
    global fontFixed

    self.root = Tk.Tk()
    self.root.wm_title("Hantek")

    fontNormal = tkFont.Font(family = 'Sans', size = 12)
    fontFixed  = tkFont.Font(family = 'Mono', size = 12)

    self.createControlPanel()
    self.plotArea = PlotArea(self.root)

    Tk.mainloop()

  def createControlPanel(self):
    self.controlPanel = Tk.Frame(self.root)
    self.controlPanel.pack(side = Tk.RIGHT, padx = 5, pady = 5)

    self.device = Oscilloscope()

    tb = TimeBaseControl(self.device,    self.controlPanel)
    ch1 = ChannelControl(self.device, 1, self.controlPanel)
    ch2 = ChannelControl(self.device, 2, self.controlPanel)

    # TODO: Load settings from config file
#    self.timeBase.set(100E-6)
#    self.sampleRate.set(0x10)

  def quit(self):
    self.root.quit()     # stops mainloop
    self.root.destroy()  # this is necessary on Windows to prevent
                         # Fatal Python Error: PyEval_RestoreThread: NULL tstate

### main

mainApp = MainApp()
