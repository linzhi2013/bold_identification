#!/usr/bin/env python3
# Copyright Guanliang MENG 2018-2020
# License: GPL v3

import re
import sys
import time
import os
import argparse
from Bio import SeqIO

src_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_path)
from bold_engin import BOLD, NoBoldMatchError
from logger import get_logger


def get_parameters():
    version = '0.0.27'
    description = '''
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

By Guanliang Meng.
See https://github.com/linzhi2013/bold_identification.

Citation:
Yang C, Zheng Y, Tan S, Meng G, et al.
Efficient COI barcoding using high throughput single-end 400 bp sequencing.
https://doi.org/10.1186/s12864-020-07255-w

version: {version}
'''.format(version=version)

    parser = argparse.ArgumentParser(description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-i', dest='infile', required=True, metavar='<str>',
                        help='input file name')

    parser.add_argument('-f', dest='infileformat', default='fasta',
        metavar='<str>', help='input file format [%(default)s]')

    parser.add_argument('-o', dest='outprefix', required=True, metavar='<str>',
                        help='outfile prefix')

    parser.add_argument('-d', dest='db', choices=['COX1', 'COX1_SPECIES', 'COX1_SPECIES_PUBLIC', 'COX1_L640bp','ITS', 'MATK_RBCL'],
        required=False, default='COX1',
        help='database to search [%(default)s]')

    parser.add_argument('-n', dest='topnum', type=int, default=1,
        metavar='<int>',
        help='how many first top hits will be output. [%(default)s]')

    parser.add_argument('-r', dest='submissiontimes', type=int, required=False,
        default=4, metavar='<int>',
        help='Maximum submission time for a sequence, useful for handling TimeOutException. [%(default)s]')

    parser.add_argument('-c', dest='to_continue', action='count',
        default=0, help='continuous mode, jump over the ones already in "-o" file, will resubmit all the remained. use "-cc" to also jump over the ones in "*.NoBoldMatchError.fasta" file.')

    parser.add_argument('-C', dest='check_chimera', action='store_true',
        default=False,
        help="For chimera check purpose. If set, for each sequence, I will query the BOLD database using the subsequences from 5'- and 3'-ends with a length of '-q <int>' bp, respectively")

    parser.add_argument('-q', dest='chimera_len', type=int, default=400,
        metavar='<int>',
        help="The length of subsequences for chimera check [%(default)s]")

    parser.add_argument('-D', dest='debug', action='store_true', default=False,
        help='debug mode output [%(default)s]')


    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(version))

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()
    else:
        args = parser.parse_args()
        return args


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


def multi_submissions(submissiontimes=4, seq_count=0, rec=None, db='COX1', fhout=sys.stdout, fhout_noBoldMatch=sys.stderr, fhout_timeoutSeq=sys.stdout, topnum=1, header_line=False, logger=None):
    seqid = str(rec.id)
    seq = str(rec.seq)

    for i in range(1, submissiontimes+1):
        if i >= 2:
            logger.info('The {0} time for the submission of: {1}\t{2}\n'.format(i, seq_count, seqid))
        try:
            taxa = BOLD(db=db, seqid=seqid, seq=seq).submit().taxa

        except NoBoldMatchError as e:
            logger.debug(e)
            SeqIO.write(rec, fhout_noBoldMatch, 'fasta')
            # no need to re-submit
            break
        else:
            item_tot = len(taxa)
            if item_tot > 0:
                output_num = topnum
                if item_tot < topnum:
                    output_num = item_tot
                for j in range(output_num):
                    item = taxa[j]
                    if seq_count == 1 and header_line:
                        print('\t'.join(item.keys()), file=fhout)
                        header_line = False

                    line = [item[k] for k in item.keys()]
                    line = '\t'.join(line)
                    print(line, file=fhout,flush=True)
                break
            else:
                # can be Timeout, will re-submit
                continue
    else:
        SeqIO.write(rec, fhout_timeoutSeq, 'fasta')


def get_taxa(to_continue=False, infile=None, infileformat='fasta', db='COX1',  outprefix='out', submissiontimes=4, topnum=1, logger=None):
    # check if in continuous mode
    # and set taxa output file
    header_line = True
    finished_seqids = set()

    taxa_file = outprefix + '.taxa'
    if to_continue >= 1 and os.path.exists(taxa_file):
        finished_seqids = get_finished_seqids(taxa_file, 'tab')
        fhout = open(taxa_file, 'a')
        header_line = False
    else:
        fhout = open(taxa_file, 'w')


    # set timeout and no bold match out files
    fhout_timeoutSeq = open(outprefix+'.TimeoutException.fasta', 'w')


    NoBoldMatchError_file = outprefix + '.NoBoldMatchError.fasta'
    if to_continue >= 2 and os.path.exists(NoBoldMatchError_file):
        finished_seqids.update(
            get_finished_seqids(NoBoldMatchError_file, 'fasta'))
        fhout_noBoldMatch = open(NoBoldMatchError_file, 'a')
    else:
        fhout_noBoldMatch = open(NoBoldMatchError_file, 'w')


    # begin searching sequences
    seq_count = 0
    for rec in SeqIO.parse(infile, infileformat):
        seq_count += 1

        # continuous mode
        if to_continue >= 1 and (rec.id in finished_seqids):
            logger.info('skip over the {0} sequence: {1}\n'.format(seq_count, rec.id))
            continue
        logger.info('start to search the {0} sequence: {1}\n'.format(seq_count, rec.id))

        multi_submissions(
            submissiontimes=submissiontimes,
            seq_count = seq_count,
            rec = rec,
            db = db,
            fhout = fhout,
            fhout_noBoldMatch = fhout_noBoldMatch,
            fhout_timeoutSeq = fhout_timeoutSeq,
            topnum = topnum,
            header_line = header_line,
            logger = logger)

        # to avoid your IP address being blocked by BOLD server.
        time.sleep(2)

    fhout.close()
    fhout_timeoutSeq.close()
    fhout_noBoldMatch.close()


def chimera_check(infile=None, infileformat='fasta', db='COX1', chimera_len=400, outprefix='check_chimera', submissiontimes=4, topnum=1, logger=None):
    # fhout_5 = open(outprefix+'.5end.taxa', 'w')
    # fhout_3 = open(outprefix+'.3end.taxa', 'w')

    fhout = open(outprefix+'.5-and-3ends.taxa', 'w')

    fhout_noBoldMatch_5 = open(outprefix + '.5end.NoBoldMatchError.fasta', 'w')
    fhout_noBoldMatch_3 = open(outprefix + '.3end.NoBoldMatchError.fasta', 'w')

    # set timeout and no bold match out files
    fhout_timeoutSeq_5 = open(outprefix + '.5end.TimeoutException.fasta', 'w')
    fhout_timeoutSeq_3 = open(outprefix + '.3end.TimeoutException.fasta', 'w')

    seq_count = 0
    header_line_5 = True
    header_line_3 = True
    for rec in SeqIO.parse(infile, infileformat):
        seq_count += 1
        logger.info('start to search the {0} sequence: {1}\n'.format(seq_count, rec.id))

        rec_5 = rec[0:chimera_len]
        rec_5.id = rec.id + '_5end'
        rec_5.description = ''

        rec_3 = rec[-chimera_len:]
        rec_3.id = rec.id + '_3end'
        rec_3.description = ''

        multi_submissions(
            submissiontimes=submissiontimes,
            seq_count = seq_count,
            rec = rec_5,
            db = db,
            fhout = fhout,
            fhout_noBoldMatch = fhout_noBoldMatch_5,
            fhout_timeoutSeq = fhout_timeoutSeq_5,
            topnum = topnum,
            header_line = header_line_5,
            logger = logger)

        multi_submissions(
            submissiontimes=submissiontimes,
            seq_count = seq_count,
            rec = rec_3,
            db = db,
            fhout = fhout,
            fhout_noBoldMatch = fhout_noBoldMatch_3,
            fhout_timeoutSeq = fhout_timeoutSeq_3,
            topnum = topnum,
            header_line = header_line_3,
            logger = logger)

        # to avoid your IP address being blocked by BOLD server.
        time.sleep(2)

    fhout.close()
    # fhout_5.close()
    fhout_timeoutSeq_5.close()
    fhout_noBoldMatch_5.close()
    # fhout_3.close()
    fhout_timeoutSeq_3.close()
    fhout_noBoldMatch_3.close()


def main():
    args = get_parameters()

    logger = get_logger(debug=args.debug)
    logger.info('args: \n{0}\n'.format(args))

    if args.check_chimera:
        chimera_check(
            infile=args.infile,
            infileformat=args.infileformat,
            db=args.db,
            chimera_len=args.chimera_len,
            outprefix=args.outprefix,
            submissiontimes=args.submissiontimes,
            topnum=args.topnum,
            logger=logger)
    else:
        get_taxa(
            to_continue=args.to_continue,
            infile=args.infile,
            infileformat=args.infileformat,
            db=args.db,
            outprefix=args.outprefix,
            submissiontimes=args.submissiontimes,
            topnum=args.topnum,
            logger=logger)



if __name__ == '__main__':
    main()
