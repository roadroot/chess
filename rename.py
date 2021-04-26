import os.path
from os import listdir, rename
from os.path import isfile, join
from sys import argv

dirn = os.path.dirname(argv[0])
source = [f for f in listdir(dirn) if isfile(join(dirn, f)) and f.count('_') > 1]
target = [join(dirn, f[:f.index('_', 2)].replace('_', ''))+f[f.index('.', len(f)-6):] for f in source]
source = [join(dirn, f) for f in source]

for index in range(len(source)):
    rename(source[index], target[index])