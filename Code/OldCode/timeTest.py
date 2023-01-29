# -*- coding: utf-8 -*-
"""
Created on Fri Jan 10 23:10:54 2020

@author: Dominic
"""

import time

heat=50
rate=0.1
duty=0.080

upper=100
lower=0

for i in range(1000):
    heat+=rate*(100-heat)*duty #Heat it up
    upper=heat
    heat-=rate*heat*(.1-duty)
    lower=heat
print((upper+lower)/2)

