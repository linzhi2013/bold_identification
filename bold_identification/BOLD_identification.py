#!/usr/bin/env python3
# Copyright Guanliang MENG 2018-2019
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
    version = '0.0.25'
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

By mengguanliang AT genomics DOT cn.
See https://github.com/linzhi2013/bold_identification.

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
        default=0, help='continuous mode, jump over the ones already in "-o" file, will resubmit all the remained. use "-cc" to also jump over the ones in "*.NoBoldMatchError.fasta" file. [%(default)s]')

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


def main():
    args = get_parameters()

    logger = get_logger(debug=args.debug)

    logger.info('args: \n{0}\n'.format(args))

    # check if in continuous mode
    # and set taxa output file
    header_line = True
    finished_seqids = set()
    if args.to_continue >= 1 and os.path.exists(args.outfile):
        finished_seqids = get_finished_seqids(args.outfile, 'tab')
        fhout = open(args.outfile, 'a')
        header_line = False
    else:
        fhout = open(args.outfile, 'w')


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
    count = 0
    for rec in SeqIO.parse(args.infile, args.infileformat):
        count += 1

        # continuous mode
        if args.to_continue >= 1 and (rec.id in finished_seqids):
            logger.info('skip over the {0} sequence: {1}\n'.format(count, rec.id))
            continue
        logger.info('start to search the {0} sequence: {1}\n'.format(count, rec.id))

        seq = str(rec.seq)

        for i in range(1, args.submissiontimes+1):
            if i >= 2:
                logger.info('The {0} time for the submission of: {1}\t{2}\n'.format(i, count, rec.id))
            try:
                taxa = BOLD(db=args.db, seqid=rec.id, seq=seq).submit().taxa

            except NoBoldMatchError as e:
                logger.debug(e)
                SeqIO.write(rec, fhout_noBoldMatch, 'fasta')
                # no need to re-submit
                break
            else:
                item_tot = len(taxa)
                if item_tot > 0:
                    output_num = args.topnum
                    if item_tot < args.topnum:
                        output_num = item_tot
                    for j in range(output_num):
                        item = taxa[j]
                        if count == 1 and header_line:
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

        # to avoid your IP address being blocked by BOLD server.
        time.sleep(2)

    fhout.close()
    fhout_timeoutSeq.close()
    fhout_noBoldMatch.close()


if __name__ == '__main__':
    main()
