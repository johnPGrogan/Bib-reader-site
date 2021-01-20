import os
import requests
import urllib.parse
from flask import redirect, render_template, request, session
from functools import wraps

import bibtexparser
from bibtexparser.bparser import BibTexParser
import numpy as np

import re

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def check_bib_format(bibtex_str, bib_style="bibtex"):
    """ check that bibtex_str matches the format expected, returns errors if not """

    # check it is a string
    if not isinstance(bibtex_str, str):
        apology('Bibliography was not detected as text. Please check you have pasted the bibliography properly')

    # len > 1
    if len(bibtex_str) <= 1:
        return 'Bibliography was too short - it must contain at least two references'

    # has letters?
    x = re.search('[a-zA-Z]', bibtex_str)
    if not x:
        return 'Bibliography did not contain any letters - please check you have entered it correctly'

    # num lines >= 1
    bibtex_lines = bibtex_str.splitlines()
    if len(bibtex_lines) <= 1:
        return 'Bibliography was too short - please make sure it contains at least two references'


    # if  bibtex, does it start with @?
    if bib_style == 'bibtex':
        x = re.search('\A[\s*\@]',  bibtex_str)
        #print(x)
        if not x:
            return 'Bibliography was not detected as BibTex format - please check your format'

    # if apa, does it start with \s|\w
    if bib_style == 'apa':
        x = re.search('\A[\s*\w]', bibtex_str)
        #print(x)
        if not x:
            return 'Bibliography was not detected as APA format - please check your format'

    return None




def parse_bib(bibtex_str):
    """ parse a bibtex bibliography into a list of dictionaries with author and journal fields"""

    parser = BibTexParser()

    def customizations(record):
    # https://python.hotexamples.com/examples/bibtexparser.bparser/BibTexParser/customization/python-bibtexparser-customization-method-examples.html
    # get the author name as list of separate names

        record = bibtexparser.customization.convert_to_unicode(record)
        # Split author field from separated by 'and' into a list of "Name, Surname".
        record = bibtexparser.customization.author(record)

        # get journal ID - name without whitespaces
        #record = bibtexparser.customization.journal(record)

        return record

    parser.customization = customizations

    bib_database = bibtexparser.loads(bibtex_str, parser=parser)

    all_authors = []
    all_journals = []
    for i, entry in enumerate(bib_database.entries):
        # get authors and journals from each
        #name = bibtexparser.customization.splitname(entry['author']) # split author into dict with first, last, von, jr
        authors = entry['author']
        for name in authors:
            all_authors.append(name)

        if "journal" in entry:
            all_journals.append(entry['journal'])

    return all_authors, all_journals




def parse_apa(bibtex_str):
    """ parse APA bibliography text into list of dicts for authors and journals"""

    bibtex_str = bibtex_str.splitlines() # each entry in list is a reference

    # make a list of dictionaries with author and journal

    all_authors = []
    all_journals = []
    for entry in bibtex_str: # for each entry
        if not entry: # if is empty newline
            continue

        # get each name
        split_paren = entry.split('(') # this will give us the names bit
        names = split_paren[0].split('.,') # this will separate each name

        # remove any punctuation
        for name in names:
            # use regexp to remove leading/trailing whitespace, or ... or &
            name = name.title() # use title case

            # remove ellipses or ampersands
            x = re.search('\&|\u2026', name)
            if x:
                name = name[x.span()[1]+1:]

            # name, initials - ignores whitespace
            x = re.search('\w.*\S', name) # name.
            name = x.group()

            # make sure all initials/prenames have spaces between them
            x = re.search('\.[A-Z]', name)
            while x:
                name = name[:x.span()[0]] + x.group()[0] + ' ' + x.group()[1] + name[x.span()[1]:]
                x = re.search('\.[A-Z]', name)


            # check it ends in .
            if name[-1] != '.':
                name = name + '.'

            # remove numbers - if they had a numbered list
            name = re.sub('\A\s*\d+[\.\s*]*',"", name)

            all_authors.append(name) # title case


        ####### get the journal name
        x = re.search("\)\.", entry)
        latter_half = entry[x.span()[1]+1:] # get reference from year til end

        # split by periods
        split_dot = latter_half.split('.')

        if len(split_dot) <= 1:
            continue # there is no journal name, just a title. move to next entry


        for section in split_dot[::-1]: # search from end to beginning
            #space_inds = re.search('\s[a-Z]') # there must be at least one space
            space_inds = re.search('\s+[a-zA-z]',section) # there must be at least one space, then a letter
            if space_inds:
                num = re.search(',\s\d', section) # and there must be some digits after the space
                if num:
                    journal_name = section[:num.span()[0]] # take from beginning of section until comma before the first number

                    # remove leading whitespace
                    journal_name = re.findall('\w.*',journal_name)

                    all_journals.append(journal_name)
                    break # move to next entry

                else:
                    x = re.search('http|doi',section) # check it does not have http in it
                    if not x:
                        journal_name = section
                        journal_name = re.findall('\w.*',journal_name)
                        all_journals.append(journal_name)

                        break

    return all_authors, all_journals



def make_initials(my_list, use_initials):
    """ replace prenames with initials only """

    new_list = []
    for entry in my_list: # for each name


        # otherwise we will be using certain prenames/initials, so...

        name = bibtexparser.customization.splitname(entry) # split author into dict with first, last, von, jr

        if use_initials == 'first_initial': # only use initial for first prename
            initials = name['first'][0][0]
            new_name = ' '.join(name['last']) + ', ' + '., '.join(map(str, initials)) + '.'

        elif use_initials == 'all_initials': # use all prename initials
            initials = []
            for prename in name['first']: # for each first name
                initials.append(prename[0]) # just take the initial

            # combine into one: von SURNAME, I., N., ...
            new_name = ' '.join(name['last']) + ', ' + '., '.join(map(str, initials)) + '.'

        elif use_initials == 'first_name': # first name only
            new_name = ' '.join(name['last']) + ', ' + ''.join(map(str, name['first'][0]))

        elif use_initials == 'surname-only': # only keep surnames
            new_name = ' '.join(name['last'])

        else: # use original entry
            new_name = entry
            name['von'] = '' # set empty, will skip next line

        if name['von']: # if there is a von, add it
            new_name = name['von'][0] + ' ' + new_name

        new_list.append(new_name)

    return new_list



def bib_count(my_list):
    """ count unique items in a list, return as sorted dict of name:count """

    # count them
    names, counts = np.unique(my_list, return_counts=True)

    inds = np.argsort(counts) # sort by count
    inds = inds[::-1] # descending order

    # make into dictionary, with name:count
    my_dict = dict(zip(names[inds],counts[inds]))

    return my_dict




def bib_analyser(bibtex_str, bib_style="bibtex", use_initials="initials"):


    if bib_style == "bibtex":

        all_authors, all_journals = parse_bib(bibtex_str)

    else:

        all_authors, all_journals = parse_apa(bibtex_str)


    # get names/initials
    all_authors = make_initials(all_authors, use_initials) # whether to use first initial only, or all initials

    # sort by frequency of uniques
    authors = bib_count(all_authors)
    journals = bib_count(all_journals)

    return authors, journals




