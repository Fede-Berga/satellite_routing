from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension("sns.leo_satellite", ['sns/leo_satellite.py']),
    Extension("sns.packet_generator", ['sns/packet_generator.py']),
    Extension("sns.sns", ['sns/sns.py']),
    Extension("sns.sr_header_builder", ['sns/sr_header_builder.py'])
]

setup(
    ext_modules=cythonize(extensions)
)