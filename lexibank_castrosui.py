from collections import defaultdict
from pathlib import Path

import attr
import pylexibank
from clldutils.misc import slug


@attr.s
class CustomConcept(pylexibank.Concept):
    Chinese_Gloss = attr.ib(default=None)


@attr.s
class CustomLanguage(pylexibank.Language):
    ChineseName = attr.ib(default=None)
    PopulationSize = attr.ib(default=None)
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
    SubGroup = attr.ib(default="Sui")
    ID_in_Source = attr.ib(default=None)
    Family = attr.ib(default="Tai-Kadai")
    DialectGroup = attr.ib(default=None)
    Location = attr.ib(default=None)
    Number_in_Source = attr.ib(default=None)


class Dataset(pylexibank.Dataset):
    id = "castrosui"
    dir = Path(__file__).parent
    concept_class = CustomConcept
    language_class = CustomLanguage
    writer_options = dict(keep_languages=False, keep_parameters=False)
    form_spec = pylexibank.FormSpec(separators=",")

    def cmd_makecldf(self, args):
        wl = self.raw_dir.read_csv("wordlist.tsv", delimiter="\t")
        concept_lookup = {}
        for concept in self.conceptlists[0].concepts.values():
            idx = concept.id.split("-")[-1] + "_" + slug(concept.english)
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
                "phonetic",
                "concepticon_id",
                "concepticon_gloss",
            ]
        }

        for line in pylexibank.progressbar(wl, desc="load the data"):
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
                        if val:
                            mapping[idx] = [
                                language_lookup[taxon]["Name"],
                                taxon,
                                language_lookup[taxon]["Glottocode"],
                                cname.english,
                                num[1:],
                                val,
                                "",  # check later for phonetic value
                                cname.concepticon_id,
                                cname.concepticon_gloss,
                            ]

                            idxs[taxon, gloss] += [idx]
                            idx += 1

            elif line[0] in language_lookup and phonetic:
                taxon = line[0]
                for gloss, val in zip(glosses[1:], line[1:]):
                    if gloss.strip():
                        these_idx = idxs.get((taxon, gloss))
                        if not these_idx:
                            pass

        for idx in pylexibank.progressbar(
            range(1, len(mapping)), desc="cldfify", total=len(mapping)
        ):
            vals = dict(zip(mapping[0], mapping[idx]))

            args.writer.add_forms_from_value(
                Language_ID=language_lookup[vals["doculectid"]]["ID"],
                Parameter_ID=concept_lookup[vals["glossid"]][0],
                Value=vals["value"],
                Source=["Castro2015"],
            )

        # We explicitly remove the ISO code column since the languages in
        # this datasets do not have an ISO code.
        args.writer.cldf["LanguageTable"].tableSchema.columns = [
            col
            for col in args.writer.cldf["LanguageTable"].tableSchema.columns
            if col.name != "ISO639P3code"
        ]
