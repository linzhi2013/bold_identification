import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bold_identification",
    version="0.0.27",
    author='Guanliang Meng',
    author_email='linzhi2012@gmail.com',
    description="To get taxa information of sequences from BOLD system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires='>=3.5',
    url='https://github.com/linzhi2013/bold_identification',
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=['biopython>1.5', 'bs4','requests', 'html5lib'],

    entry_points={
        'console_scripts': [
            'bold_identification=bold_identification.BOLD_identification:main',
        ],
    },
    classifiers=(
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
    ),
)
