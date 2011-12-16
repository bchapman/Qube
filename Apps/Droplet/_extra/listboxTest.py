# using a wx.ListCtrl() to display US-state information
# in columns and rows, also added sort by column feature
# source: Dietrich  14NOV2008

import wx
import operator

class MyFrame(wx.Frame):
    def __init__(self, parent, mytitle, mysize, states):
        wx.Frame.__init__(self, parent, wx.ID_ANY, mytitle,
            size=mysize)
        self.SetBackgroundColour("yellow")
        # make data available to the instance
        self.states = states

        # create the list control
        self.lc = wx.ListCtrl(self, wx.ID_ANY,
             style=wx.LC_REPORT|wx.SUNKEN_BORDER|wx.LC_HRULES)
        # select an item (left mouse click on it) and bind to a method
        self.lc.Bind(wx.EVT_LIST_ITEM_SELECTED,self.onSelect)

        # create and load the columns with header titles, set width
        self.lc.InsertColumn(0,"State")
        self.lc.SetColumnWidth(0, 110)
        self.lc.InsertColumn(1,"State Capital")
        self.lc.SetColumnWidth(1, 110)
        self.lc.InsertColumn(2,"State Flower")
        self.lc.SetColumnWidth(2, 160)
        self.lc.InsertColumn(3,"State Bird")
        self.lc.SetColumnWidth(3, 180)

        # load the rest of the list with data
        self.loadList()

        # create the sort buttons ...
        sort_state = wx.Button(self, wx.ID_ANY, "Sort by State")
        sort_capital = wx.Button(self, wx.ID_ANY, "Sort by Capital")
        sort_flower = wx.Button(self, wx.ID_ANY, "Sort by Flower")
        sort_bird = wx.Button(self, wx.ID_ANY, "Sort by Bird")
        # bind the button clicks ...
        self.Bind (wx.EVT_BUTTON, self.onSortState, sort_state)
        self.Bind (wx.EVT_BUTTON, self.onSortCapital, sort_capital)
        self.Bind (wx.EVT_BUTTON, self.onSortFlower, sort_flower)
        self.Bind (wx.EVT_BUTTON, self.onSortBird, sort_bird)

        # create an output widget
        self.text = wx.TextCtrl(self, wx.ID_ANY, 
            value="Select a state from the list above", 
            style=wx.TE_MULTILINE)
        
        # use a vertical boxsizer as main layout sizer
        sizer_v = wx.BoxSizer(wx.VERTICAL)
        # use a horizontal sizer for the buttons
        sizer_h = wx.BoxSizer(wx.HORIZONTAL)
        sizer_h.Add(sort_state, 1, flag=wx.ALL|wx.EXPAND, border=5)
        sizer_h.Add(sort_capital, 1, flag=wx.ALL|wx.EXPAND, border=5)
        sizer_h.Add(sort_flower, 1, flag=wx.ALL|wx.EXPAND, border=5)
        sizer_h.Add(sort_bird, 1, flag=wx.ALL|wx.EXPAND, border=5)
        # add the rest + sizer_h to the vertical sizer
        sizer_v.Add(self.lc, 1, flag=wx.ALL|wx.EXPAND, border=10)
        sizer_v.Add(sizer_h, 0, flag=wx.ALL|wx.EXPAND, border=10)
        sizer_v.Add(self.text, 0, flag=wx.ALL|wx.EXPAND, border=10)
        self.SetSizer(sizer_v)

    def loadList(self):
        # clear the listctrl
        self.lc.DeleteAllItems()
        # load each data row
        for ix, line in enumerate(self.states):
            # set max_rows, change if need be
            max_rows = 100
            # also sets/updates row index starting at 0
            index = self.lc.InsertStringItem(max_rows, line[0])
            #print index
            self.lc.SetStringItem(index, 1, line[1])
            self.lc.SetStringItem(index, 2, line[2])
            self.lc.SetStringItem(index, 3, line[3])

    def onSortState(self, event):
        state_index = operator.itemgetter(0)
        self.states.sort(key=state_index)
        self.loadList()

    def onSortCapital(self, event):
        capital_index = operator.itemgetter(1)
        self.states.sort(key=capital_index)
        self.loadList()

    def onSortFlower(self, event):
        flower_index = operator.itemgetter(2)
        self.states.sort(key=flower_index)
        self.loadList()

    def onSortBird(self, event):
        bird_index = operator.itemgetter(3)
        self.states.sort(key=bird_index)
        self.loadList()

    def onSelect(self, event):
        """get the selected item/row"""
        # -1 --> get the first item that matches the specified flags
        # wx.LIST_NEXT_ALL  search for subsequent item by index
        # wx.LIST_STATE_SELECTED  get the selected item
        ix_selected = self.lc.GetNextItem(item=-1,
            geometry=wx.LIST_NEXT_ALL, state=wx.LIST_STATE_SELECTED)
        # each selected tuple is (state, city, flower, bird)
        state = states[ix_selected][0]
        city = states[ix_selected][1]
        flower = states[ix_selected][2]
        bird = states[ix_selected][3]
        s1 = "I am sitting in lovely " + city + ", " + state + "\n"
        s2 = "watching a " + bird + " eat my " + flower
        self.text.ChangeValue(s1 + s2)


# data to load the listctrl with, in the form of a list of
# (State, State Capital, State Flower, State Bird) tuples
states = [
('Alabama', 'Montgomery', 'Camellia', 'Yellowhammer'),
('Alaska', 'Juneau', 'Forget-me-not', 'Willow Ptarmigan'),
('Arizona', 'Phoenix', 'Suguaro Cactus Blossom', 'Cactus Wren'),
('Arkansas', 'Little Rock', 'Apple Blossom', 'Mockingbird'),
('California', 'Sacremento', 'Golden Poppy', 'California Valley Quail'),
('Colorado', 'Denver', 'Mountain Columbine', 'Lark Bunting'),
('Connecticut', 'Hartford', 'Mountain Laurel', 'Robin'),
('Florida', 'Tallahassee', 'Orange Blossom', 'Mockingbird'),
('Georgia', 'Atlanta', 'Cherokee Rose', 'Brown Thrasher'),
('Hawaii', 'Honolulu', 'Red Hibiscus', 'Nene (Hawaiian Goose)'),
('Idaho', 'Boise', 'Syringa', 'Mountain Bluebird'),
('Illinois', 'Springfield', 'Violet', 'Cardinal'),
('Indiana', 'Indianapolis', 'Peony', 'Cardinal'),
('Iowa', 'Des Moines', 'Wild Rose', 'Eastern Goldfinch'),
('Kansas', 'Topeka', 'Sunflower', 'Western Meadowlark'),
('Kentucky', 'Frankfort', 'Goldenrod', 'Cardinal'),
('Louisiana', 'Baton Rouge', 'Magnolia', 'Eastern Brown Pelican'),
('Maine', 'Augusta', 'Pine Cone & Tassel', 'Chickadee'),
('Tennessee', 'Nashville', 'Iris', 'Mockingbird'),
('Maryland', 'Annapolis', 'Black-eyed Susan', 'Baltimore Oriole'),
('Delaware', 'Dover', 'Peach Blossom', 'Blue Hen Chicken'),
('Massachusetts', 'Boston', 'Mayflower', 'Chickadee'),
('Rhode Island', 'Providence', 'Violet', 'Rhode Island Red'),
('Minnesota', 'St. Paul', 'Lady-slipper', 'Loon'),
('Mississippi', 'Jackson', 'Magnolia', 'Mockingbird'),
('Missouri', 'Jefferson City', 'Hawthorn', 'Bluebird'),
('Michigan', 'Lansing', 'Apple Blossom', 'Robin'),
('Montana', 'Helena', 'Bitterroot', 'Western Meadowlark'),
('Nebraska', 'Lincoln', 'Goldenrod', 'Western Meadowlark'),
('Nevada', 'Carson City', 'Sagebrush', 'Mountain Bluebird'),
('New Hampshire', 'Concord', 'Purple Lilac', 'Purple Finch'),
('Vermont', 'Montpelier', 'Red Clover', 'Hermit Thrush'),
('New Jersey', 'Trenton', 'Violet', 'Eastern Goldfinch'),
('New Mexico', 'Santa Fe', 'Yucca', 'Road Runner'),
('New York', 'Albany', 'Rose', 'Bluebird'),
('North Carolina', 'Raleigh', 'Flowering Dogwood', 'Cardinal'),
('Wyoming', 'Cheyenne', 'Indian Paintbrush', 'Meadowlark'),
('North Dakota', 'Bismarck', 'Prairie Rose', 'Meadowlark'),
('Ohio', 'Columbus', 'Scarlet Carnation', 'Cardinal'),
('Oklahoma', 'Oklahoma City', 'Mistletoe', 'Scissor-tailed Flycatcher'),
('Oregon', 'Salem', 'Oregon Grape', 'Western Meadowlark'),
('Pennsylvania', 'Harrisburg', 'Mountain Laurel', 'Ruffed Grouse'),
('South Carolina', 'Columbia', 'Yellow Jessamine', 'Carolina Wren'),
('South Dakota', 'Pierre', 'Pasqueflower', 'Ring-necked Pheasant'),
('Texas', 'Austin', 'Bluebonnet', 'Mockingbird'),
('Utah', 'Salt Lake City', 'Sego Lily', 'Sea Gull'),
('Virginia', 'Richmond', 'Dogwood', 'Cardinal'),
('Washington', 'Olympia', 'Coast Rhododendron', 'Willow Goldfinch'),
('West Virginia', 'Charleston', 'Rhododendron', 'Cardinal'),
('Wisconsin', 'Madison', 'Wood Violet', 'Robin')
]

app = wx.App(0)
# set title and size for the MyFrame instance
mytitle = "US States Information (using a wx.ListCtrl)"
width = 580
height = 360
MyFrame(None, mytitle, (width, height), states).Show()
app.MainLoop()