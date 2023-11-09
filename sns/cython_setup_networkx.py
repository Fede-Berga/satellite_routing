from setuptools import Extension, setup
from Cython.Build import cythonize
import os

files = [
    os.path.join(root, file)
    for root, _, files in os.walk("./networkx")
    for file in files
    if file.endswith(".py")
    and "test" not in os.path.join(root, file)
    and "__init__" not in os.path.join(root, file)
]
print(files)

extensions = []
for file in files:
    try:
        tmp
        if "utils" not in file:
            tmp = cythonize(Extension(".".join(file[1:-3].split("/")), [file]))
        else:
            tmp = cythonize(Extension(".".join(file[1:-8].split("/")), [file]))
        extensions.append(tmp)
    except:
        continue

setup(ext_modules=extensions)
