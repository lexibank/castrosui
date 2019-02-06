from lingpy import *
from pyconcepticon.api import Concepticon
from collections import defaultdict

api = Concepticon('/home/mattis/projects/scripts/concepticon-data')


data = csv2list('wordlist.tsv', strip_lines=False)
langs = csv2dict('langs.tsv')

taxa = sorted(langs)


concepts = {c.number.rjust(3, '0'): c for c in
        api.conceptlists['Castro-2015-608'].concepts.values()}


D = {0: ['doculect', 'doculectid', 'glottocode', 'concept', 'glossid', 'value', 'form', 'phonetic',
    'concepticon_id', 'concepticon_gloss']}
idx = 1
for line in data:

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
        for num, gloss, val in zip(numbers[1:], glosses[1:], line[1:]):
            if num.strip() and gloss.strip():
                cname = concepts[num[1:]]
                forms = val.split(',')
                if forms:
                    for form in forms:
                        D[idx] = [langs[taxon][3], taxon, langs[taxon][5], 
                                cname.english, num[1:], val, form.strip(), '',
                                cname.concepticon_id, cname.concepticon_gloss,
                                ]
                        idxs[taxon, gloss] += [idx]
                        idx += 1
                else:
                    print('missing value', gloss, num, taxon)

    elif line[0] in taxa and phonetic:
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

wl = Wordlist(D)
wl.output('tsv', filename='castro-test', prettify=False)
