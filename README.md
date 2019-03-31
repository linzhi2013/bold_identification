# bold_identification

**Important**

This package relies on Python3.5 or hihger version. If you do not have Python3 installed, please intall it first. If you do not know how to install Python packages, please refer to `https://packaging.python.org/tutorials/installing-packages/`. Please go to `https://docs.python.org/3/` to learn more about Python. I cannot offer any support for such kind of problems.

## 1 Introduction

see `https://github.com/linzhi2013/bold_identification`.

This is a Python3 package which can get the taxonomy information of sequences from BOLD [http://www.boldsystems.org/index.php](http://www.boldsystems.org/index.php).

To get the taxonomy information of a sequence from BOLD, what we usually do is: (1) open the website `http://www.boldsystems.org/index.php/IDS_OpenIdEngine` with a browser; (2) Choose a database; (3) input the sequence (4) click `submit` and wait for the result. (5) Copy the taxonomy information from the result page.

`bold_identification` actually does the same things as above, but it does such a thing automatically for you, and makes life easier.


Currently, `bold_identification` only runs on Mac OS, Windows 64bit, Linux.

Beware,

* only the Chrome browser and PhantomJS browser work on Windows, while FireFox doesn't.

* Only PhantomJS browser can be run on a non-graphical computer, while Chrome and FireFox cannot, even though there is a '-H' option.

## 2 Installation

    pip install bold_identification

There will be a command `bold_identification` created under the same directory as your `pip` command.

## 3 Usage
run `bold_identification`

    usage: bold_identification [-h] -i <str> [-f <str>] -o <str>
                               [-d {COX1,COX1_SPECIES,COX1_SPECIES_PUBLIC,COX1_L640bp,ITS,Plant}]
                               [-n <int>] [-b {PhantomJS,Firefox,Chrome}]
                               [-t <int>] [-t2 <int>] [-r <int>] [-c] [-D] [-H]
                               [--version]

    To identify taxa of given sequences from BOLD (http://www.boldsystems.org/).
    Some sequences can fail to get taxon information, which can be caused by
    TimeoutException if your network to the BOLD server is bad.
    Those sequences will be output in the file '*.TimeoutException.fasta'.

    You can:
    1) run another searching with the same command directly (but add -c option);
    2) change the browser (-b option);
    3) lengthen the time to wait for each query (-t option);
    4) increase submission times (-r option) for a sequence.

    Also, the sequences without BOLD matches will be output in the
    file '*.NoBoldMatchError.fasta'

    By mengguanliang@genomics.cn.
    See https://github.com/linzhi2013/bold_identification.

    Notes:

    It seems that PhantomJS sometimes doesn't work when search Plant and Fungi
    databases. If this happens, you can try another browser.

    version: 0.0.20

    optional arguments:
      -h, --help            show this help message and exit
      -i <str>              input file name
      -f <str>              input file format [fasta]
      -o <str>              outfile
      -d {COX1,COX1_SPECIES,COX1_SPECIES_PUBLIC,COX1_L640bp,ITS,Plant}
                            database to search [COX1]
      -n <int>              how many first top hits will be output. [1]
      -b {PhantomJS,Firefox,Chrome}
                            browser to be used [PhantomJS]
      -t <int>              the time to wait for a query [60]
      -t2 <int>             the extra time to wait for ITS or Plant query [10]
      -r <int>              Maximum submission time for a sequence, useful for
                            handling TimeOutException. [4]
      -c                    continuous mode, jump over the ones already in "-o"
                            file, will resubmit all the remained. use "-cc" to
                            also jump over the ones in "*.NoBoldMatchError.fasta"
                            file. [False]
      -D                    debug mode output [False]
      -H                    No graphical window mode, possibly not work for "-b
                            Firefox", has no effect on "-b PhantomJS". [False]
      --version             show program's version number and exit
      

## 4 Problems

### Cannot download the browsers
This can happen when your network is not good.

Solution:   
Download the executable driver file manaully, then extract the executable and put it on the `drivers` directory. See more details output by `bold_identification` when you run into this problem.

### Browser doen't work
Sometimes it happens to me. And I don't know why. I guess it is because the browser driver is not so stable.

Solution:   
Try another browser with the `-b` option.   
if this happens with '-H' option, try not to use it.


## 5 Citation
When you use `bold_identification` in your study, please cite:

    Guanliang MENG, Chengran ZHOU, et. al., Shanlin LIU, Shaoying LIU. Mitogenome and nuclear gene datasets of small mammals on Qinghai-Tibetan Plateau.









