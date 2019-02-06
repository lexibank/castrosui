from __future__ import unicode_literals, print_function
from collections import OrderedDict, defaultdict

import attr
from clldutils.misc import slug
from clldutils.path import Path
from clldutils.text import split_text, strip_brackets
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.dataset import Concept, Language

from lingpy import *
from tqdm import tqdm

@attr.s
class HConcept(Concept):
    Chinese_Gloss = attr.ib(default=None)

@attr.s
class HLanguage(Language):
    Chinese_name = attr.ib(default=None)
    Population = attr.ib(default=None)
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
    SubGroup = attr.ib(default=None)

∼

class Dataset(BaseDataset):
    id = 'castrosui'
    dir = Path(__file__).parent
    concept_class = HConcept
    language_class = HLanguage

    def split_forms(self, item, value):
        """Override custom behavior: no splitting into multiple values.
        This is done explicitly in the code"""
        value = self.lexemes.get(value, value)
        return [self.clean_form(item, form) for form in [value]]

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):

        data = self.raw.read_csv('wordlist.tsv', delimiter="\t")
        langs = {} # need for checking later
        concepts = {c.number.rjust(3, '0'): c for c in self.conceptlist.concepts.values()}

        with self.cldf as ds:

            for concept in concepts.values():
                ds.add_concept(
                        ID=concept.number.rjust(3, '0'),
                        Name=concept.english,
                        Chinese_Gloss=concept.attributes['chinese'],
                        Concepticon_ID=concept.concepticon_id,
                        Concepticon_Gloss=concept.concepticon_gloss
                        )
            for language in self.languages:
                ds.add_language(
                        ID=language['ID'],
                        Glottocode=language['Glottolog'],
                        Name=language['Name'],
                        SubGroup=language['Group'],
                        Chinese_name=language['Chinese_name'],
                        Latitude=language['Latitude'],
                        Longitude=language['Longitude']
                        )
                langs[language['ID']] = language

            ds.add_sources(*self.raw.read_bib())

            idx = 1
            D = {0: ['doculect', 'doculectid', 'glottocode', 'concept',
                'glossid', 'value', 'form', 'phonetic', 'concepticon_id',
                'concepticon_gloss']}

            for line in tqdm(data):
                if not line[0].strip():
                    phonetic = True
                if line[0] == "'Ref#":
                    numbers = line
                    phonetic = False
                    idxs = defaultdict(list)
                elif line[0] == 'Gloss':
                    glosses = line
                elif line[0] in langs and not phonetic:
                    taxon = line[0]
                    for num, gloss, val in zip(
                            numbers[1:],
                            glosses[1:],
                            line[1:]
                            ):
                        if num.strip() and gloss.strip():
                            cname = concepts[num[1:]]
                            forms = val.split(',')
                            if forms:
                                for form in forms:
                                    D[idx] = [
                                            langs[taxon]['Name'], 
                                            taxon, 
                                            langs[taxon]['Glottolog'], 
                                            cname.english, 
                                            num[1:], 
                                            val, form.strip(), 
                                            '', # check later for phonetic value
                                            cname.concepticon_id, 
                                            cname.concepticon_gloss,
                                            ]
                                    idxs[taxon, gloss] += [idx]
                                    idx += 1
                            else:
                                print('missing value', gloss, num, taxon)

                elif line[0] in langs and phonetic:
                    taxon = line[0]
                    for gloss, val in zip(glosses[1:], line[1:]):
                        if gloss.strip():
                            these_idx = idxs.get((taxon, gloss))
                            if not these_idx:
                                pass
                            else:
                                forms = val.split(',')
                                for this_idx, form in zip(these_idx, forms):
                                    D[this_idx][7] = form

            # add data to cldf
            for idx in tqdm(range(1, len(D)), desc='add data'):
                vals = dict(zip(D[0], D[idx]))
                segments = self.tokenizer(None, '^'+vals['form'].replace(' ',
                    '_')+'$', column="IPA")
                ds.add_lexemes(
                    Language_ID=vals['doculectid'],
                    Parameter_ID=vals['glossid'],
                    Form=vals['form'],
                    Value=vals['value'],
                    Segments=segments,
                    Source=['Castro2015'],
                    #PhoneticValue=vals['phonetic']
                    )



