# bold_identification

**Important**

This package relies on Python3. If you do not have Python3 installed, please intall it first. If you do not know how to install Python packages, please refer to `https://packaging.python.org/tutorials/installing-packages/`. Please go to `https://docs.python.org/3/` to learn more about Python. I cannot offer any support for such kind of problems.

## 1 Introduction

see `https://github.com/linzhi2013/bold_identification`.

This is a Python3 package which can get the taxonomy information of sequences from BOLD [http://www.boldsystems.org/index.php](http://www.boldsystems.org/index.php).

Currently, `bold_identification` only runs on Mac OS, Windows 64bit, Linux.


## 2 Installation

    pip install bold_identification

There will be a command `bold_identification` created under the same directory as your `pip` command.

## 3 Usage
run `bold_identification`


    usage: bold_identification [-h] -i <str> [-f <str>] -o <str>
                              [-d {COX1,COX1_SPECIES,COX1_SPECIES_PUBLIC,COX1_L640bp,ITS,MATK_RBCL}]
                              [-n <int>] [-r <int>] [-c] [-D] [--version]

    To identify taxa of given sequences from BOLD (http://www.boldsystems.org/).
    Some sequences can fail to get taxon information, which can be caused by
    TimeoutException if your network to the BOLD server is bad.
    Those sequences will be output in the file '*.TimeoutException.fasta'.

    You can:
    1) run another searching with the same command directly (but add -c option);
    2) lengthen the time to wait for each query (-t option);
    3) increase submission times (-r option) for a sequence.

    Also, the sequences without BOLD matches will be output in the
    file '*.NoBoldMatchError.fasta'

    By mengguanliang AT genomics DOT cn.
    See https://github.com/linzhi2013/bold_identification.

    version: 0.0.22

    optional arguments:
      -h, --help            show this help message and exit
      -i <str>              input file name
      -f <str>              input file format [fasta]
      -o <str>              outfile
      -d {COX1,COX1_SPECIES,COX1_SPECIES_PUBLIC,COX1_L640bp,ITS,MATK_RBCL}
                            database to search [COX1]
      -n <int>              how many first top hits will be output. [1]
      -r <int>              Maximum submission time for a sequence, useful for
                            handling TimeOutException. [4]
      -c                    continuous mode, jump over the ones already in "-o"
                            file, will resubmit all the remained. use "-cc" to
                            also jump over the ones in "*.NoBoldMatchError.fasta"
                            file. [False]
      -D                    debug mode output [False]
      --version             show program's version number and exit



## 4 Citation
When you use `bold_identification` in your study, please cite:

    Yang, Chentao, Shangjin Tan, Guanliang Meng, David G. Bourne, Paul A. O'brien, Junqiang Xu, Sha Liao, Ao Chen, Xiaowei Chen, and Shanlin Liu. "Access COI barcode efficiently using high throughput Single End 400 bp sequencing." BioRxiv (2018): 498618. DOI: 10.1101/498618









