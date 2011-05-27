'''
Reporter

Author: Brennan Chapman
Date: 5/24
Version: 1.0

Reporter thread that runs separately from the render.
This reports the progress of the render to qube.
'''

import threading
import Queue
import qb

# Reports the progress of the render to Qube
# This will help to avoid buffer overflow conflicts
class Reporter(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.currAgendaItem = {}
    
    def run(self):
        
        # Grab the first agenda item
        self.currAgendaItem = qb.requestwork()
        
        while True:
            # Get the progress from the queue
            progress = int(self.queue.get())
                
            # Loop to update progress gaps
            while True:
                agendaProgress = int(self.currAgendaItem['id']) # ID represents the percent complete 1-100
                if (progress >= agendaProgress):
                    self.currAgendaItem['status'] = 'complete'
                    qb.reportwork(self.currAgendaItem)
                
                    # Get a new agenda item if possible
                    self.currAgendaItem = qb.requestwork()
                    if (int(self.currAgendaItem['id']) == -1 or int(self.currAgendaItem['id']) == 101):
                        break
                elif (progress < agendaProgress):
                    break
            
            # Signal that the queue task is complete
            self.queue.task_done()
            
            # If the job is complete, empty the queue of remaining jobs
            if (int(self.currAgendaItem['id']) == -1 or int(self.currAgendaItem['id']) == 101):
                print 'Reporter: Job Complete, emptying queue of ' + str(self.queue.qsize()) + ' extra jobs'
                while True:
                    self.queue.get()
                    self.queue.task_done()