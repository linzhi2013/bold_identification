import re
import requests
from bs4 import BeautifulSoup
import sys
import collections


class NoBoldMatchError(Exception):
    def __init__(self, arg):
        super(NoBoldMatchError, self).__init__()
        self.arg = arg

    def __str__(self):
        return "NoBoldMatchError:\n{0}\n".format(self.arg)


class BOLD(object):
    """docstring for BOLD"""

    def __init__(self, db='COX1', seqid=None, seq=None, timeout=None):
        super(BOLD, self).__init__()
        self.db = db
        self.pane_type = self.db_to_paneType(db=self.db)
        self.url = self.paneType_to_url(pane_type=self.pane_type)
        self.seqid = seqid
        self.seq = re.sub(r'\s+', '', seq)
        self.timeout = timeout

        self.data = {
             'tabtype': self.pane_type,
             'searchdb': self.db,
             'sequence': self.seq,
        }


    def submit(self):
        r = requests.post(self.url, data=self.data)
        result_url = 'http://www.boldsystems.org' + r.text.split('<span style="text-decoration: none" result="')[1].split('">')[0]

        page_source = requests.get(result_url).text

        return taxonRanks(
            page_source=page_source,
            seqid=self.seqid,
            pane_type=self.pane_type)


    def db_to_paneType(self, db=None):
        db_paneType = {
            'COX1': 'animalTabPane',
            'COX1_SPECIES': 'animalTabPane',
            'COX1_SPECIES_PUBLIC': 'animalTabPane',
            'COX1_L640bp': 'animalTabPane',
            'ITS': 'fungiTabPane',
            'MATK_RBCL': 'plantTabPane'}

        return db_paneType[db]

    def paneType_to_url(self, pane_type=None):
        paneType_url = {
            'animalTabPane': 'http://www.boldsystems.org/index.php/IDS_IdentificationRequest',
            'fungiTabPane':'http://www.boldsystems.org/index.php/IDS_BlastRequest',
            'plantTabPane':'http://www.boldsystems.org/index.php/IDS_BlastRequest'
        }

        return paneType_url[pane_type]


class taxonRanks(object):
    """docstring for taxonRanks"""
    def __init__(self, page_source=None, seqid=None, pane_type=None):
        super(taxonRanks, self).__init__()
        self.page_source = page_source
        self.seqid = seqid
        self.pane_type = pane_type
        self.taxa = self.get_taxonRank(page_source=self.page_source, seqid=self.seqid, pane_type=self.pane_type)

    def get_taxonRank(self, page_source=None, seqid=None, pane_type=None):
        if 'Unable to match any records in the selected database.' in page_source:
            raise NoBoldMatchError(seqid)

        soup = BeautifulSoup(page_source, "html5lib")

        result_class = self.get_table_class(pane_type=pane_type)
        table = soup.find_all('table', class_=result_class)[0]

        head_line = True
        ranks = []
        taxa = []
        for row in table.find_all('tr'):
            if head_line:
                for col in row.find_all('td'):
                    ranks.append(col.text)
                head_line = False
                continue
            else:
                taxon_oneline = collections.OrderedDict()
                taxon_oneline['seqid'] = seqid
                for col_name, col_val in zip(ranks, row.find_all('td')):
                    taxon_oneline[col_name] = col_val.text.strip()
                taxa.append(taxon_oneline)


        return taxa

    def get_table_class(self, pane_type=None):
        paneType_class = {
            'animalTabPane': 'resultsTable noborder',
            'fungiTabPane': 'table resultTable noborder',
            'plantTabPane': 'table resultTable noborder',
        }

        return paneType_class[pane_type]















