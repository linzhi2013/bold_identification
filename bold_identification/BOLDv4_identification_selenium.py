#!/usr/bin/env python3
# Copyright Guanliang MENG 2018
# License: GPL v3
import re
import sys
import time
import platform
import os
import argparse
from Bio import SeqIO
import selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import shutil
import requests
import pathlib
import stat
import logging
import collections
from glob import glob

# chrome, all animal database passed
# crhome, Plant, passed

'''
when do something with the page (input), before you next thing (submit),
or you get a new page, try add following actions on specific time point:

driver.execute_script("document.body.style.zoom='100%'")
time.sleep(1)

driver.execute_script("window.scrollTo(0,0);")
time.sleep(1)

css selector is better than xpath
'''


class NoBoldMatchError(Exception):
    def __init__(self, arg):
        super(NoBoldMatchError, self).__init__()
        self.arg = arg

    def __str__(self):
        return "NoBoldMatchError:\n{0}\n".format(self.arg)


class TimeoutOrNoBoldMatch(object):
    def __init__(self, locator, seqid):
        self.locator = locator
        self.seqid = seqid

    def __call__(self, driver):
        if 'Unable to match any records in the selected database.' in driver.page_source:
                raise NoBoldMatchError(self.seqid)
        else:
            elem = EC.visibility_of_element_located(self.locator)
            return elem

def get_parameters():
    version = '0.0.20'
    description = '''
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

version: {version}
'''.format(version=version)

    parser = argparse.ArgumentParser(description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-i', dest='infile', required=True, metavar='<str>',
                        help='input file name')

    parser.add_argument('-f', dest='infileformat', default='fasta',
        metavar='<str>', help='input file format [%(default)s]')

    parser.add_argument('-o', dest='outfile', required=True, metavar='<str>',
                        help='outfile')

    parser.add_argument('-d', dest='db', choices=['COX1', 'COX1_SPECIES', 'COX1_SPECIES_PUBLIC', 'COX1_L640bp','ITS', 'Plant'],
        required=False, default='COX1',
        help='database to search [%(default)s]')

    parser.add_argument('-n', dest='topnum', type=int, default=1,
        metavar='<int>',
        help='how many first top hits will be output. [%(default)s]')

    parser.add_argument('-b', dest='browser',
        choices=['PhantomJS', 'Firefox', 'Chrome'],
        required=False, default='PhantomJS',
        help='browser to be used [%(default)s]')

    parser.add_argument('-t', dest='timeout', type=int, required=False,
        metavar='<int>', default=60,
        help='the time to wait for a query [%(default)s]')

    parser.add_argument('-t2', dest='extra_time', type=int,
        required=False,
        metavar='<int>', default=10,
        help='the extra time to wait for ITS or Plant query [%(default)s]')

    parser.add_argument('-r', dest='submissiontimes', type=int, required=False,
        default=4, metavar='<int>',
        help='Maximum submission time for a sequence, useful for handling TimeOutException. [%(default)s]')

    parser.add_argument('-c', dest='to_continue', action='count',
        default=False, help='continuous mode, jump over the ones already in "-o" file, will resubmit all the remained. use "-cc" to also jump over the ones in "*.NoBoldMatchError.fasta" file. [%(default)s]')

    parser.add_argument('-D', dest='debug', action='store_true', default=False,
        help='debug mode output [%(default)s]')

    parser.add_argument('-H', dest='headless_browser', action='store_true',
        default=False, help='No graphical window mode, possibly not work for "-b Firefox", has no effect on "-b PhantomJS". [%(default)s]')

    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(version))

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()
    else:
        args = parser.parse_args()
        return args


def choose_css_selector(db=None, logger=None):
    clade_chooseDB_css = {}
    clade_getREUSLT_css = {}
    db_clade = {}

    filedir = os.path.abspath(os.path.dirname(__file__))
    css_selector_config_file = os.path.join(filedir, 'css_selector.config')
    with open(css_selector_config_file, 'r') as fh:
        DBbegin = False
        RESULT_begin = False
        for i in fh:
            i = i.strip()
            if i.startswith('#') or not i:
                continue

            # choose a database
            if i.startswith('=DBbegin:'):
                DBbegin = True
                clade = i.split(':')[-1]
                continue
            if i.startswith('=DBend:'):
                DBbegin = False
                continue
            if DBbegin:
                key, val = i.split('=', 1)
                if clade not in clade_chooseDB_css:
                    clade_chooseDB_css.setdefault(clade, {})

                if key.startswith('db_'):
                    db = key.split('_', 1)[1]
                    if 'db' not in clade_chooseDB_css[clade]:
                        clade_chooseDB_css[clade].setdefault('db', {})
                    clade_chooseDB_css[clade]['db'][db] = val
                else:
                    clade_chooseDB_css[clade][key] = val
                continue

            # get result
            if i.startswith('=RESULT_begin:'):
                RESULT_begin = True
                clade = i.split(':', 1)[-1]
                continue
            if i.startswith('=RESULT_end:'):
                RESULT_begin = False
                continue
            if RESULT_begin:
                key, val = i.split('=', 1)
                if clade not in clade_getREUSLT_css:
                    clade_getREUSLT_css[clade] = collections.OrderedDict()
                if key.startswith('Header_'):
                    db = key.split('_', 1)[1]
                    if 'Header' not in clade_getREUSLT_css[clade]:
                        clade_getREUSLT_css[clade].setdefault('Header', {})
                    clade_getREUSLT_css[clade]['Header'][db] = val
                else:
                    clade_getREUSLT_css[clade][key] = val
                continue

    for clade in clade_chooseDB_css:
        for db in clade_chooseDB_css[clade]['db']:
            db_clade[db] = clade

    logger.debug('clade_chooseDB_css:\n{0}\n'.format(clade_chooseDB_css))
    logger.debug('clade_getREUSLT_css:\n{0}\n'.format(clade_getREUSLT_css))
    logger.debug('db_clade:\n{0}\n'.format(db_clade))

    return clade_chooseDB_css, clade_getREUSLT_css, db_clade


def find_phantomjs_exe(under_dir=None):
    under_dir = re.sub('/$', '', under_dir)
    fake_exe = os.path.join(under_dir, 'phantomjs')
    files = glob(under_dir+'/**/bin/phantomjs')
    phantomjs_exe = ''
    if len(files) == 1:
        phantomjs_exe = files[0]
    else:
        files = glob(under_dir+'/**/bin/phantomjs.exe')
        if len(files):
            phantomjs_exe = files[0]

    if phantomjs_exe:
        return phantomjs_exe
    else:
        return fake_exe


def download_browser(executable_path=None, logger=None):
    brow_plt_url = {
        'Firefox': {
            'Darwin': 'https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-macos.tar.gz',
            'Linux': 'https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-linux64.tar.gz',
            'Windows': 'https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-win64.zip',
        },
        'Chrome': {
            'Darwin': 'https://chromedriver.storage.googleapis.com/2.40/chromedriver_mac64.zip',
            'Linux': 'https://chromedriver.storage.googleapis.com/2.40/chromedriver_linux64.zip',
            'Windows': 'https://chromedriver.storage.googleapis.com/2.40/chromedriver_win32.zip',
        },
        'PhantomJS': {
            'Darwin': 'https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-macosx.zip',
            'Linux': 'https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2',
            'Windows': 'https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-windows.zip',
        }

    }

    logger.debug('brow_plt_url:\n{0}\n'.format(brow_plt_url))

    executable_name = os.path.basename(executable_path)
    outdir = os.path.dirname(executable_path)
    platform = os.path.basename(outdir)
    browser = os.path.basename(os.path.dirname(outdir))
    url = brow_plt_url[browser][platform]

    pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
    zname = os.path.basename(url)
    outfile = os.path.join(outdir, zname)

    logger.warn('Downloading browser from:\n{0}\n'.format(url))
    with open(outfile, 'wb') as zfile:
        try:
            resp = requests.get(url)
            zfile.write(resp.content)
        except requests.exceptions.ConnectionError:
            log = '''requests.exceptions.ConnectionError

Your network is bad. Please download the file {url} manually

Then unpack the file and put the executable file to {outdir}

And change the name to be {executable_name}

You May also add executable permissions for this file, e.g. with chmod 755 command on Linux system

 Or, you may change to use another browser (-b option)'''.format(url=url, outdir=outdir, executable_name=executable_name)
            logger.error(log)
            sys.exit()

    logger.warn('Unpacking the file:\n{0}\n'.format(outfile))
    shutil.unpack_archive(outfile, extract_dir=outdir)

    logger.warn('Removing the file:\n{0}\n'.format(outfile))
    pathlib.Path(outfile).unlink()

    if browser == 'PhantomJS':
        executable_path = find_phantomjs_exe(under_dir=outdir)

    logger.warn('Making the file be executable\n')
    os.chmod(executable_path, 0o555)

    return executable_path


def get_driver(browser='Firefox', headless_browser=False, logger=None):
    plt = platform.system()
    filedir = os.path.abspath(os.path.dirname(__file__))
    drivers_dir = os.path.join(filedir, 'drivers')

    if plt in ['Darwin', 'Linux']:
        if browser == 'Firefox':
            executable_path = os.path.join(drivers_dir, browser, plt,
                                           'geckodriver')
        elif browser == 'Chrome':
            executable_path = os.path.join(drivers_dir, browser, plt,
                                           'chromedriver')
        elif browser == 'PhantomJS':
            executable_path = find_phantomjs_exe(os.path.join(drivers_dir, browser, plt))
    elif plt == 'Windows':
        if browser == 'Firefox':
            sys.exit('Firefox on Windows platform is bad, use "-b Chrome" instead.')
        elif browser == 'Chrome':
            executable_path = os.path.join(drivers_dir, browser, plt,
                                           'chromedriver.exe')
        elif browser == 'PhantomJS':
            executable_path = find_phantomjs_exe(os.path.join(drivers_dir, browser, plt))
    else:
        logger.error('unSupported platform: ' + plt)
        sys.exit()

    if not os.path.exists(executable_path):
        logger.warn('Local ' + executable_path + ' not found!',)

        executable_path = download_browser(executable_path=executable_path, logger=logger)

        if (plt == 'Windows') and (browser == 'Chrome'):
            win_chrome = os.path.join(filedir, 'chromedriver.exe')

            if not os.path.exists(win_chrome):
                shutil.copyfile(executable_path, win_chrome)
                executable_path = win_chrome

    if browser == 'Firefox':
        if headless_browser:
            os.environ['MOZ_HEADLESS'] = '1' # if options method not working
            options = webdriver.FirefoxOptions()
            options.add_argument('-headless')
            driver = webdriver.Firefox(executable_path=executable_path, firefox_options=options)
        else:
            driver = webdriver.Firefox(executable_path=executable_path)
    elif browser == 'Chrome':
        if headless_browser:
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            driver = webdriver.Chrome(executable_path=executable_path, chrome_options=options)
        else:
            driver = webdriver.Chrome(executable_path=executable_path)
    elif browser == 'PhantomJS':
        driver = webdriver.PhantomJS(executable_path=executable_path)
    else:
        logger.error('unSupported browser: {0}\n'.format( browser))
        sys.exit()

    logger.debug('driver path:\n{0}\n'.format(executable_path))

    return driver


def BOLD_identification(driver=None, chooseDB_css=None, getREUSLT_css=None, ranks=None, seq=None, db=None, topnum=1, timeout=None, extra_time=5, logger=None):
    seqid = seq.split('\n')[0]

    # open the search web, waiting for the presence of elements
    try:
        logger.debug('opening http://www.boldsystems.org/index.php/IDS_OpenIdEngine\n')
        driver.get("http://www.boldsystems.org/index.php/IDS_OpenIdEngine")
        driver.execute_script("document.body.style.zoom='100%'")
        driver.execute_script("window.scrollTo(0,0);")

        logger.debug("chooseDB_css['pannel']:\n{0}\n".format(chooseDB_css['pannel']))
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, chooseDB_css['pannel'])))

        # choose a pannel, animal, fungi, plant
        elem = driver.find_element_by_css_selector(chooseDB_css['pannel'])
        driver.execute_script("window.scrollTo(0,0);")
        time.sleep(1)
        elem.click()
    except:
        logger.warn(
            'bad network to open http://www.boldsystems.org/index.php/IDS_OpenIdEngine\n')
        return None

    assert "Identification" in driver.title

    # choose a database
    try:
        driver.execute_script("document.body.style.zoom='100%'")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0,0);")
        time.sleep(3)
        elem = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, chooseDB_css['db'][db])))
        #elem = driver.find_element_by_css_selector(chooseDB_css['db'][db])
        elem.click()
    except selenium.common.exceptions.ElementNotVisibleException as e:
        logger.debug(e)
        logger.warn('ElementNotVisibleException: {0}\n'.format(seqid))
        return None

    except selenium.common.exceptions.TimeoutException as e:
        logger.debug(e)
        logger.warn('TimeoutException: {0}\n'.format(seqid))
        return None
    # the following expression is critical for Chrome driver!
    # if not used, Chrome fails to click when opens the searching page
    # second time.
    # driver.execute_script("document.body.style.zoom='100%'")
    # time.sleep(3)
    # driver.execute_script("window.scrollTo(0,0);")
    # time.sleep(3)


    # find textarea
    logger.debug("chooseDB_css['textarea']:\n{0}\n".format(chooseDB_css['textarea']))
    elem = driver.find_element_by_css_selector(chooseDB_css['textarea'])

    # input sequence
    driver.execute_script("window.scrollTo(0,0);")
    elem.send_keys(seq)

    # submit
    logger.debug("chooseDB_css['submit_button']:\n{0}\n".format(chooseDB_css['submit_button']))
    elem = driver.find_element_by_css_selector(chooseDB_css['submit_button'])
    elem.click()

    # wait returning result
    time.sleep(20)
    header_css=getREUSLT_css['Header'][db]
    logger.debug('header_css:\n{0}\n'.format(header_css))
    taxa = collections.defaultdict(dict)
    try:
        WebDriverWait(driver, timeout).until(TimeoutOrNoBoldMatch((By.CSS_SELECTOR, header_css), seqid))
        # WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, header_css))) # work

        # print('found Phylum!')
        driver.execute_script("document.body.style.zoom='100%'")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0,0);")
        time.sleep(2)

        # double check.
        # because sometimes the previous can not succeed
        if 'Unable to match any records in the selected database.' in driver.page_source:
            raise NoBoldMatchError(seqid)

    except selenium.common.exceptions.TimeoutException as e:
        logger.warn('TimeoutException: {0}\n'.format(seqid))
        return None
    except selenium.common.exceptions.WebDriverException as e:
        logger.warn('WebDriverException:\n{0}\n'.format(e))
        return None
    else:
        if db in ['ITS', 'Plant']:
            time.sleep(extra_time)

        # the third check.
        # because sometimes the previous can not succeed
        if 'Unable to match any records in the selected database.' in driver.page_source:
            raise NoBoldMatchError(seqid)

        for j in range(1, topnum+1):
            for i in ranks:
                taxa[str(j)][i] = ''
            # tips:
            # do not capture too exactly, to the 'td' level is fine,
            # but do not capture 'h' or 'em' level. Because BOLD result
            # page won't have 'h' or 'em' item when the result is empty.
            try:
                check_visi = True
                for i in ranks:
                    column_css = getREUSLT_css[i].format(j+1)
                    if (j+1)%2:
                        column_css = column_css.replace('evenRow', 'oddRow')
                    logger.debug('\n{0} css selector: {1}\n'.format(i,column_css))
                    # taxa[str(j)][i] = driver.find_element_by_css_selector(column_css).text
                    if j == 1 and check_visi:
                        check_visi = False
                        try:
                            WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.CSS_SELECTOR, column_css)))
                        except selenium.common.exceptions.TimeoutException as e:
                            logger.warn('Header has been found, but the content cannot be located, this often happens to PhantomJS browser. You should try another browser!\nTimeoutException: {0}\n'.format(e))
                            return None

                    hidden_content = driver.find_element_by_css_selector(column_css)
                    logger.debug('\ninnerHTML got: {0}\n'.format(hidden_content.get_attribute('innerHTML')))

                    taxa[str(j)][i] = hidden_content.get_attribute('textContent').strip()
                    logger.debug('\ntext got: {0}\n'.format(taxa[str(j)][i]))

            except selenium.common.exceptions.NoSuchElementException as e:
                logger.info('There are only {0} results for {1}\n'.format(
                    j-1, seqid))
                logger.debug(e)
                del taxa[str(j)]
                return taxa

    logger.debug('got taxa:\n{0}\n'.format(taxa))

    return taxa


def get_logger(debug=False):
    # 级别排序:CRITICAL > ERROR > WARNING > INFO > DEBUG
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # must be DEBUG, then 'ch' below works.
    # logger.setFormatter(formatter)

    fh = logging.FileHandler(os.path.basename(sys.argv[0]) + '.log')
    if debug:
        fh.setLevel(logging.DEBUG)
    else:
        fh.setLevel(logging.INFO)  # INFO level goes to the log file
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    if debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.WARNING)  # only WARNING level will output on screen
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def get_finished_seqids(file=None, f_format='tab'):
    seqids = set()
    if f_format == 'tab':
        with open(file, 'r') as fh:
            for i in fh:
                i = i.rstrip()
                seqid = i.split()[0]
                seqids.add(seqid)
    elif f_format == 'fasta':
        with open(file, 'r') as fh:
            for i in fh:
                i = i.strip()
                if i.startswith('>'):
                    seqid = i.split()[0].replace('>', '')
                    seqids.add(seqid)
    else:
        sys.exit('unknown infile format: {}'.format(f_format))

    return seqids


def main():
    args = get_parameters()

    logger = get_logger(debug=args.debug)

    logger.info('args: \n{0}\n'.format(args))

    # read in configure file
    clade_chooseDB_css, clade_getREUSLT_css, db_clade = choose_css_selector(db=args.db, logger=logger)

    clade = db_clade[args.db]
    logger.debug('clade:\n{0}\n'.format(clade))
    chooseDB_css = clade_chooseDB_css[clade]
    getREUSLT_css = clade_getREUSLT_css[clade]
    ranks_2 = getREUSLT_css.keys()
    logger.debug('ranks_2:\n{0}\n'.format(ranks_2))
    ranks = [i for i in ranks_2 if i != 'Header']

    logger.info('ranks:\n{0}\n'.format(ranks))

    # check if in continuous mode
    # and set taxa output file
    finished_seqids = set()
    if args.to_continue >= 1 and os.path.exists(args.outfile):
        finished_seqids = get_finished_seqids(args.outfile, 'tab')
        fhout = open(args.outfile, 'a')
    else:
        fhout = open(args.outfile, 'w')
        print('Seq id\t' + '\t'.join(ranks), file=fhout)


    # set timeout and no bold match out files
    TimeoutException_file = os.path.basename(args.outfile) + '.TimeoutException.fasta'
    fhout_timeoutSeq = open(TimeoutException_file, 'w')


    NoBoldMatchError_file = os.path.basename(
        args.outfile) + '.NoBoldMatchError.fasta'
    if args.to_continue >= 2 and os.path.exists(NoBoldMatchError_file):
        finished_seqids.update(
            get_finished_seqids(NoBoldMatchError_file, 'fasta'))
        fhout_noBoldMatch = open(NoBoldMatchError_file, 'a')
    else:
        fhout_noBoldMatch = open(NoBoldMatchError_file, 'w')


    # begin searching sequences
    driver = get_driver(browser=args.browser,
                        headless_browser=args.headless_browser,
                        logger=logger
                        )
    count = 0
    for rec in SeqIO.parse(args.infile, args.infileformat):
        count += 1

        # continuous mode
        if args.to_continue >= 1 and (rec.id in finished_seqids):
            logger.info('skip over the {0} sequence: {1}\n'.format(count, rec.id))
            continue
        logger.info('start to search the {0} sequence: {1}\n'.format(count, rec.id))

        seq = '>{0}\n{1}'.format(rec.id, rec.seq)

        for i in range(1, args.submissiontimes+1):
            if i >= 2:
                logger.info('The {0} time for the submission of: {1}\t{2}\n'.format(i, count, rec.id))
            try:
                taxa = BOLD_identification(
                        driver=driver,
                        chooseDB_css=chooseDB_css,
                        getREUSLT_css=getREUSLT_css,
                        ranks=ranks,
                        seq=seq,
                        db=args.db,
                        topnum=args.topnum,
                        timeout=args.timeout,
                        extra_time=args.extra_time,
                        logger=logger
                    )
            except NoBoldMatchError as e:
                logger.debug(e)
                print(seq, file=fhout_noBoldMatch, flush=True)
                # no need to re-submit
                break
            else:
                if taxa:
                    for j in taxa:
                        line = [taxa[j][i] for i in ranks]
                        line = '\t'.join(line)
                        print(rec.description, line,
                            sep='\t', file=fhout,flush=True)
                    break
        else:
            print(seq, file=fhout_timeoutSeq, flush=True)

        # to avoid your IP address being blocked by BOLD server.
        time.sleep(2)

    driver.quit()

    fhout.close()
    fhout_timeoutSeq.close()


if __name__ == '__main__':
    main()
