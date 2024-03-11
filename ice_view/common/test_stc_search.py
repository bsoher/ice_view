import wx
import wx.stc as stc

class XmlSTC(stc.StyledTextCtrl):

    def __init__(self, parent):
        stc.StyledTextCtrl.__init__(self, parent)

        self.SetLexer(stc.STC_LEX_XML)




class XmlPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.xml_view = XmlSTC(self)
        #self.view_hdr = stc.StyledTextCtrl(self)

        with open(r'D:\Users\bsoher\code\repo_github\ice_view\test_data\braino_svs_se\MiniHead_spe_00001.IceHead') as fobj:
            self.text = fobj.read()
            self.ntext = len(self.text)

        self.xml_view.SetText(self.text)
        self.xml_view.SetReadOnly(True)


        self.search = wx.TextCtrl(self)
        self.buttonPrev = wx.Button(self, wx.ID_ANY, "Prev")
        self.buttonPrev.Bind(wx.EVT_BUTTON, self.OnPrev)
        self.buttonNext = wx.Button(self, wx.ID_ANY, "Next")
        self.buttonNext.Bind(wx.EVT_BUTTON, self.OnNext)

        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer2.Add(self.search, 1, wx.EXPAND, 0)
        self.sizer2.Add(self.buttonPrev)
        self.sizer2.Add(self.buttonNext)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.xml_view, 1, wx.EXPAND)
        sizer.Add(self.sizer2)

        self.SetSizer(sizer)

    def OnPrev(self, event):
        print('In OnPrev')
        item = self.search.GetValue()
        curr = self.xml_view.GetCurrentPos()
        if curr == 0:
            minp = self.ntext-1
            maxp = 0
        else:
            minp = curr-1   # -1 so current location isn't found again
            maxp = 0
        istr, iend = self.xml_view.FindText(minPos=minp, maxPos=maxp, text=item)
        if istr>0 and iend>0:
            self.xml_view.ShowPosition(istr)
            self.xml_view.SetSelection(istr, iend)
        else:
            minp = self.ntext - 1
            maxp = 0
            istr, iend = self.xml_view.FindText(minPos=minp, maxPos=maxp, text=item)
            if istr > 0 and iend > 0:
                self.xml_view.ShowPosition(istr)
                self.xml_view.SetSelection(istr, iend)
            else:
                self.xml_view.ShowPosition(0)
                self.xml_view.SetCursor(0)


    def OnNext(self, event):
        print('In OnNext')
        item = self.search.GetValue()
        curr = self.xml_view.GetCurrentPos()
        if curr == self.ntext-1:
            minp = 0
            maxp = self.ntext-1
        else:
            minp = curr
            maxp = self.ntext-1
        istr, iend = self.xml_view.FindText(minPos=minp, maxPos=maxp, text=item)
        if istr>0 and iend>0:
            self.xml_view.ShowPosition(istr)
            self.xml_view.SetSelection(istr, iend)
        else:
            minp = 0
            maxp = self.ntext - 1
            istr, iend = self.xml_view.FindText(minPos=minp, maxPos=maxp, text=item)
            if istr > 0 and iend > 0:
                self.xml_view.ShowPosition(istr)
                self.xml_view.SetSelection(istr, iend)
            else:
                self.xml_view.ShowPosition(self.ntext-1)
                self.xml_view.SetCursor(self.ntext-1)


class XmlFrame(wx.Frame):

    def __init__(self):
        wx.Frame.__init__(self, None, title='XML View')
        panel = XmlPanel(self)
        self.Show()

if __name__ == '__main__':
    app = wx.App(False)
    frame = XmlFrame()
    app.MainLoop()