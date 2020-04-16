from collections import defaultdict

import attr
from pathlib import Path
from pylexibank import Concept, Language
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.util import progressbar

from clldutils.misc import slug


@attr.s
class CustomConcept(Concept):
    Chinese_Gloss = attr.ib(default=None)


@attr.s
class CustomLanguage(Language):
    ChineseName = attr.ib(default=None)
    Population = attr.ib(default=None)
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
    SubGroup = attr.ib(default="Sui")
    ID_in_Source = attr.ib(default=None)
    Family = attr.ib(default="Tai-Kadai")
    DialectGroup = attr.ib(default=None)
    Location = attr.ib(default=None)
    Number_in_Source = attr.ib(default=None)


class Dataset(BaseDataset):
    id = "castrosui"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage

    def cmd_makecldf(self, args):

        wl = self.raw_dir.read_csv("wordlist.tsv", delimiter="\t")
        concept_lookup = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = concept.id.split('-')[-1]+'_'+slug(concept.english)
            args.writer.add_concept(
                ID=idx,
                Name=concept.english,
                Chinese_Gloss=concept.attributes["chinese"],
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss,
            )
            concept_lookup[concept.number.rjust(3, "0")] = [idx, concept]
        language_lookup = {k["ID_in_Source"]: k for k in self.languages}
        args.writer.add_languages()
        args.writer.add_sources()

        idx = 1
        mapping = {
            0: [
                "doculect",
                "doculectid",
                "glottocode",
                "concept",
                "glossid",
                "value",
                "form",
                "phonetic",
                "concepticon_id",
                "concepticon_gloss",
            ]
        }

        for line in progressbar(wl, desc="load the data"):
            if not line[0].strip():
                phonetic = True
            if line[0] == "'Ref#":
                numbers = line
                phonetic = False
                idxs = defaultdict(list)
            elif line[0] == "Gloss":
                glosses = line
            elif line[0] in language_lookup and not phonetic:
                taxon = line[0]
                for num, gloss, val in zip(numbers[1:], glosses[1:], line[1:]):
                    if num.strip() and gloss.strip():
                        cname = concept_lookup[num[1:]][1]
                        forms = val.split(",")
                        if forms:
                            for form in forms:
                                mapping[idx] = [
                                    language_lookup[taxon]["Name"],
                                    taxon,
                                    language_lookup[taxon]["Glottocode"],
                                    cname.english,
                                    num[1:],
                                    val,
                                    form.strip(),
                                    "",  # check later for phonetic value
                                    cname.concepticon_id,
                                    cname.concepticon_gloss,
                                ]
                                idxs[taxon, gloss] += [idx]
                                idx += 1
                        else:
                            print("missing value", gloss, num, taxon)

            elif line[0] in language_lookup and phonetic:
                taxon = line[0]
                for gloss, val in zip(glosses[1:], line[1:]):
                    if gloss.strip():
                        these_idx = idxs.get((taxon, gloss))
                        if not these_idx:
                            pass
                        else:
                            forms = val.split(",")
                            for this_idx, form in zip(these_idx, forms):
                                mapping[this_idx][7] = form
        # export to lingpy wordlist in raw folder
        # Wordlist(mapping).output(
        #    "tsv", filename=self.dir.joinpath("raw", "lingpy-wordlist").as_posix()
        # )

        # add data to cldf
        for idx in progressbar(range(1, len(mapping)), desc="cldfify", total=len(mapping)):
            vals = dict(zip(mapping[0], mapping[idx]))
            args.writer.add_forms_from_value(
                Language_ID=language_lookup[vals["doculectid"]]["ID"],
                Parameter_ID=concept_lookup[vals["glossid"]][0],
                Value=vals["value"],
                Source=["Castro2015"],
            )
