# Python modules

# 3rd party modules
import wx

# Our modules
from ice_view.common.plot_panel_spectrum import PlotPanelSpectrum


class PlotPanelSpectral(PlotPanelSpectrum):

    def __init__(self, parent, tab, tab_dataset, **kwargs):
        '''
        This is a customization of the PlotPanel object for use in a specific
        location in our application. The basic matplotlib functionality is
        contained in the base class, all we are doing here is overwriting the
        various canvas Event functions to mesh with our application.

        parent      - the widget to which the PlotPanel is directly attached
        tab         - the Spectral tab in which the PlotPanel resides
        tab._dataset - the Dataset tab in which the Spectral tab resides

        '''
        tab.SizerSplitterWindow.Fit(tab)  # bugfix wxGlade 0.9.6 to 1.0.0

        super().__init__(parent, **kwargs)

        self.tab = tab
        self.tab_dataset = tab_dataset
        self.top = wx.GetApp().GetTopWindow()

        # these are in points to facilitate area calculations
        self.ref_locations = 0,self.tab.block.dims[0]-1

        self.set_color( (255,255,255) )


    # EVENT FUNCTIONS -----------------------------------------------

    def on_motion(self, xdata, ydata, val, bounds, iaxis):
        ppm = xdata
        hz  = xdata * self.tab.dataset.frequency

        self.top.statusbar.SetStatusText( " PPM = %.3f" % (ppm, ), 0)
        self.top.statusbar.SetStatusText( " Hz = %.3f"  % (hz,  ), 1)

        self.top.statusbar.SetStatusText(( " Value = "+str(val[0])), 2)


    def on_scroll(self, button, step, iaxis):
        self.set_vertical_scale(step)
        self.tab.FloatScale.SetValue(self.vertical_scale)


    def on_zoom_select(self, xmin, xmax, val, ymin, ymax, reset=False, iplot=None):
        self.tab.FloatScale.SetValue(self.dataymax)


    def on_zoom_motion(self, xmin, xmax, val, ymin, ymax, iplot=None):
        ppm_str  = xmin
        ppm_end  = xmax
        if ppm_str > ppm_end: ppm_str, ppm_end = ppm_end, ppm_str
        hz_str = ppm_str * self.tab.dataset.frequency
        hz_end = ppm_end * self.tab.dataset.frequency

        delta_ppm = -1*(ppm_str - ppm_end)  # keeps delta positive
        delta_hz  = delta_ppm * self.tab.dataset.frequency
        self.top.statusbar.SetStatusText(( " PPM Range = %.2f to %.2f" % (ppm_str, ppm_end)), 0)
        self.top.statusbar.SetStatusText(( " Hz Range = %.1f to %.1f"  % (hz_str, hz_end)), 1)
        self.top.statusbar.SetStatusText(( " dPPM = %.2f  dHz = %.1f"  % (delta_ppm, delta_hz)), 2)


    def on_refs_select(self, xmin, xmax, val, reset=False, iplot=None):
        # Calculate area of span
        area, rms = self.calculate_area()
        self.top.statusbar.SetStatusText(self.tab.build_area_text(area[0], rms[0], plot_label='A'), 3)


    def on_refs_motion(self, xmin, xmax, val, iplot=None):
        ppm_str  = xmin
        ppm_end  = xmax
        if ppm_str > ppm_end: ppm_str, ppm_end = ppm_end, ppm_str
        hz_str = ppm_str * self.tab.dataset.frequency
        hz_end = ppm_end * self.tab.dataset.frequency
        delta_ppm = -1*(ppm_str - ppm_end)
        delta_hz  = delta_ppm * self.tab.dataset.frequency
        self.top.statusbar.SetStatusText(( " PPM Range = %.2f to %.2f" % (ppm_str, ppm_end)), 0)
        self.top.statusbar.SetStatusText(( " Hz Range = %.1f to %.1f" % (hz_str, hz_end)), 1)
        self.top.statusbar.SetStatusText(( " dPPM = %.2f  dHz = %.1f" % (delta_ppm, delta_hz)), 2)

        # Calculate area of span
        area, rms = self.calculate_area()
        self.top.statusbar.SetStatusText(self.tab.build_area_text(area[0], rms[0], plot_label='A'), 3)


    def on_middle_select(self, xstr, ystr, xend, yend, iplot):
        pass


    def on_middle_motion(self, xcur, ycur, xprev, yprev, iplot):
        '''
        Interactive phasing occurs when the user holds down the middle button
        and moves around.  Up/down for phase0 and left/right for phase1.

        The actual calls to plot_panel_spectrum.set_phase_0() or phase_1()
        occur at the dataset level.  That is because phase0/1 can be changed
        from multiple locations (main spectral plot interactive, svd filter
        plot interactive, voigt tab plot interactive, main spectral phase 0
        and phase 1 widgets, voigt initial value widgets. (Note. this is
        true for B0 shift as well by not dealt with here). In tab._dataset.py,
        the set_phase_0() and set_phase_1() methods can be called from any
        tab without sibling tabs talking to each other.

        An important differentiation to understand is that now that phase is
        inherently taken care of in the plot_panel_spectral object, the phase
        value stored in the block AND the new phase displayed in various plots
        have to be explicitly applied.  It is no longer sufficient to just set
        the phase0/1 in the block and then call process_and_plot to get the
        plots to update.  We go to this trouble in order to gain flexibility
        and speed in the interactive phasing and general display of data in
        each plot_panel_spectrum derived class.

        '''
        if iplot not in (0,1): return
        voxel = self.tab.voxel

        # The mouse probably moved in both the X and Y directions, but to
        # make phasing easier for the user to do accurately, we only pay
        # attention to the larger of the two movements.

        dy = ycur - yprev
        dx = xcur - xprev

        if abs(dy) > abs(dx):
            # 0 order phase
            delta = dy
            self.tab.set_phase_0(delta, voxel)
            phase0 = self.tab.block.get_phase_0(voxel)
            self.set_phase_0(phase0, index=[0], absolute=True, no_draw=True)
            self.canvas.draw()
            # r = self.tab.block.get_phase_0(voxel)
            # print('phase0 = '+str(r))
        else:
            # pass
            # first order phase, x10 makes Phase1 changes more noticeable
            delta = dx*10
            self.tab.set_phase_1(delta, voxel)
            phase1 = self.tab.block.get_phase_1(voxel)
            self.set_phase_1(phase1, index=[0], absolute=True, no_draw=True)
            self.canvas.draw()

        # Calculate the new area after phasing
        area, rms = self.calculate_area()
        self.top.statusbar.SetStatusText(self.tab.build_area_text(area[0], rms[0], plot_label='A'), 3)


