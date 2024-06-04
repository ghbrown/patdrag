import sys
import os
from pathlib import Path
import argparse
from PyQt5.QtWidgets import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *

def argsort(seq):
    #https://stackoverflow.com/questions/3382352/equivalent-of-numpy-argsort-in-basic-python
    return sorted(range(len(seq)), key=seq.__getitem__)


class MovingImage(QGraphicsPixmapItem):
    # adapted from:
    # https://learndataanalysis.org/drag-and-move-an-object-with-your-mouse-pyqt5-tutorial/
    def __init__(self,pixmap,x,y):
        super().__init__(pixmap)
        self.setPos(x, y)
        self.setAcceptHoverEvents(True)

    # mouse hover event
    def hoverEnterEvent(self, event):
        app.instance().setOverrideCursor(Qt.OpenHandCursor)

    def hoverLeaveEvent(self, event):
        app.instance().restoreOverrideCursor()

    # mouse click event
    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        orig_cursor_position = event.lastScenePos()
        updated_cursor_position = event.scenePos()

        orig_position = self.scenePos()

        updated_cursor_x = updated_cursor_position.x() - orig_cursor_position.x() + orig_position.x()
        updated_cursor_y = updated_cursor_position.y() - orig_cursor_position.y() + orig_position.y()
        self.setPos(QPointF(updated_cursor_x, updated_cursor_y))

    def mouseReleaseEvent(self, event):
        pass


class App(QWidget):

    def __init__(self,path):
        super().__init__()
        # internal data variables
        self.path = path            # original parent path
        self.original_names = []    # original names (no path)
        self.pixmap_keys    = []    # keys identifiying pixmap contents
        self.temp_dir = '.patdrag'  # place to store randomly named copies
        # internal GUI elements
        self.pattern_field = None
        self.rename_button = None
        # set GUI size
        screen = QApplication.instance().primaryScreen().availableGeometry()
        width, height = screen.width(), screen.height()
        self.resize(width,height)
        # handle rest of setup
        self.setLayout(QVBoxLayout())
        self.setup()      # attach all components to GUI
        self.add_items()  # get images from path and add thumbnails
        self.show()


    def rename(self):
        """
        rename images according to entered pattern and current order
        """
        def get_original_name(qgpi):
            # gets the name associated with a QGraphicsPixmapItem
            key = qgpi.pixmap().cacheKey()
            for i, cur_key in enumerate(self.pixmap_keys):
                if (key == cur_key):
                    return self.original_names[i]

        # retrieve pattern
        self.pattern = self.pattern_field.text()
        pretext, posttext = self.pattern.split('#')

        # move items to temp_dir to prevent overwrite problems
        ## create temp_dir if it doesn't exist
        Path(os.path.join(self.path,self.temp_dir)).mkdir(parents=True,exist_ok=True)
        for filename in self.original_names:
            os.rename(os.path.join(self.path,filename),
                      os.path.join(self.path,self.temp_dir,filename))

        # looks over self.pics to get x coordinates of each object
        qgpis = self.pics.items()  # not sorted left to right
        x_coord = [qgpi.x() for qgpi in qgpis]
        sort_indices = argsort(x_coord)

        for i, ind in enumerate(sort_indices):
            newname = pretext + f'{i:03}' + posttext  # e.g. <pattern>000<pattern>.<extension>
            old_filename = get_original_name(qgpis[ind])
            __, extension = os.path.splitext(filename)
            new_filename = newname + extension
            os.rename(os.path.join(self.path,self.temp_dir,old_filename),
                      os.path.join(self.path,new_filename))

        # delete temporary directory
        ## create temp_dir if it doesn't exist
        Path.rmdir(os.path.join(self.path,self.temp_dir))
        # shut down application
        self.close()
            

    def add_items(self):
        """
        adds images on current path as thumbnails
        """
        def even_scale(pixmap,n):
            # scale image down using maximal dimension
            new_dim = min(int(self.width()/10),
                          int(2*self.width()/n))
            qsize = pixmap.size()
            width, height = qsize.width(), qsize.height()
            if (width >= height):
                scaled_pixmap = pixmap.scaledToWidth(new_dim)
            else:  # height larger than width
                scaled_pixmap = pixmap.scaledToHeight(new_dim)
            return scaled_pixmap

        # get names of images at path/
        filenames = os.listdir(self.path)  # unsorted!
        filenames.sort()
        filenames = [f for f in filenames
                     if os.path.isfile(os.path.join(self.path,f))]
        self.original_names = filenames

        # initial image layout
        n_image = len(self.original_names)
        stack_edge = 0 
        stack_start = 0
        stack_depth = 0
        cur_pos = [0,0] # x and y positions
        offset = 50
        old_width = 0
        for i, name in enumerate(self.original_names):
            fullpath = os.path.join(self.path,name)
            thumbnail_pixmap = even_scale(QPixmap(fullpath),n_image)
            self.pixmap_keys.append(thumbnail_pixmap.cacheKey())
            qsize = thumbnail_pixmap.size()
            width, height = qsize.width(), qsize.height()
            if ( (cur_pos[1] + height >= self.height())
                 or (stack_depth >= 3) ):  # move to new stack
                cur_pos[0]  = stack_edge + offset
                cur_pos[1]  = 0
                stack_start = cur_pos[0]
                stack_edge  = stack_start + width
                stack_depth = 0
            thumbnail = MovingImage(thumbnail_pixmap,cur_pos[0],cur_pos[1])

            self.pics.scene.addItem(thumbnail)
            stack_depth += 1
            stack_edge = max(stack_edge,cur_pos[0]+width)
            cur_pos[1] += height
            cur_pos[0] += 50

    def setup(self):
        """
        sets up basic (but possibly empty) main elements of GUI
        """
        # basic structure
        container, controls = QWidget(), QWidget()
        self.pics = QGraphicsView()

        # set layouts of (sub)widgets
        container.setLayout(QVBoxLayout())
        controls.setLayout(QHBoxLayout())

        # important data
        self.pattern_field = QLineEdit('Sampler_#')
        self.rename_button = QPushButton('Rename',clicked=self.rename)

        # add items to controls
        controls.layout().addWidget(QLabel('Enter pattern (#: number):'))
        controls.layout().addWidget(self.pattern_field)
        controls.layout().addWidget(self.rename_button)
        # add contents to pics
        self.pics.scene = QGraphicsScene()
        self.pics.setScene(self.pics.scene)       
        # add sections to container
        container.layout().addWidget(controls)
        container.layout().addWidget(self.pics)
        # add container to window
        self.layout().addWidget(container)


# parser for single positional argument
parser = argparse.ArgumentParser()
parser.add_argument('path')
args = parser.parse_args()

app = QApplication(sys.argv)
view = App(args.path)
app.exec_()

