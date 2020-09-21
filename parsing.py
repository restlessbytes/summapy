import unicodedata
import re

from typing import List, Set, Tuple
from Stemmer import Stemmer

CONTENT_WORD_TAG = 'CW'
STOPWORD_TAG = 'SW'
STARTING_TAG = 'START'
ABBREVIATION_TAG = 'AB'
UNICODE_NORMALIZATION = 'NFC'


class Token:
    def __init__(self, position, surface_repr, underlying_repr, is_word):
        self.position = position
        self.surface_repr = surface_repr
        self.underlying_repr = underlying_repr
        self.is_word = is_word


def get_stopwords():
    with open('stopwords_en.txt', 'r', encoding='utf-8') as file:
        return {w.strip() for w in file.readlines()}


def get_common_abbr():
    with open('common-abbr.txt', 'r', encoding='utf-8') as file:
        return {line.strip() for line in file.readlines()}


def normalize_quotation_marks(s: str) -> str:
    result = ''
    for c in s:
        if unicodedata.category(c) in ['Pi', 'Pf']:
            char_name = unicodedata.name(c)
            if 'QUOTATION MARK' in char_name:
                if 'SINGLE' in char_name:
                    result += "'"
                elif 'DOUBLE' in char_name:
                    result += '"'
                # TODO ... 'else'?
            else:
                result += c
        else:
            result += c
    return result


def unicode_cat_major(c) -> str:
    return unicodedata.category(c)[0]


def as_text_abbreviation(word: str, pos: int, common_abbreviations: Set[str]) -> str:
    # A word is potentially an abbreviation if

    # trivial case: it's an abbreviation if it's in the list of common abbreviations
    if {word, word.lower(), word.upper(), word.capitalize()} & common_abbreviations:
        return word

    # case: 'A' at the start of a sentence -> probably the indefinite article
    if pos == 0 and word == 'A':
        return ''

    # case: all upper case letters
    if re.match(r"^[A-Z]+$", word):
        return word

    # case: all upper case letters and dots - in that case word must end with a dot
    if re.match(r"^([A-Z.]+)\.$", word):
        return word

    return ''


def split_into_paragraphs(text: str) -> List[str]:
    paragraphs = []
    for paragraph in text.split('\n\n'):
        if paragraph[-1] in ['.', '?', '!', '"']:
            paragraphs.append(paragraph)
        else:
            paragraphs.append(paragraph + '.')
    return paragraphs


def split_into_sentences(paragraphs: List[str], common_abbr: Set[str]) -> List[List[str]]:
    sentences = []
    for paragraph in paragraphs:
        tokens = re.split(r'[\n ]', paragraph)

        sentence = []
        t1, t2 = '', ''
        for i in range(0, len(tokens) - 1):
            t1 = tokens[i]
            t2 = tokens[i + 1]

            if t1[-1] in ['!', '?'] or t1[-2:] in ['."', '!"', '?"', '".', '"!', '"?']:
                # case: unambiguous sentence delimiters: !, ?, .", !", ?", "., "!, "?
                sentences.append(sentence + [t1])
                sentence = []
            elif t1 in common_abbr:
                # case: common abbreviation - they only appear mid-sentence so no new sentence here
                sentence.append(t1)
            elif t1.endswith('.') and unicodedata.category(t2[0]) == 'Lu':
                # case: if t1 ends with dot but t2 starts with lower case letter then we're probably still in a sentence
                sentences.append(sentence + [t1])
                sentence = []
            else:
                # base case: no new sentence - just append
                sentence.append(t1)
        sentences.append(sentence + [t2])
    return sentences


def tag_sentences(sentences: List[List[str]], stopwords: Set[str], common_abbr: Set[str]) -> List[List[Tuple]]:
    tagged_sentences = []
    for sentence in sentences:
        tagged_sentence = []
        for token_pos, token in enumerate(sentence):
            word = ''
            for c in token:
                if unicode_cat_major(c) in ['L', 'N'] or c in ["'", "-", "."]:
                    word += c
            word = word.replace('..', '.')

            if not word:
                # should not happen but you never know
                continue

            text_abbreviation = as_text_abbreviation(word, token_pos, common_abbr)

            if text_abbreviation:
                tagged_sentence.append((token_pos, token, text_abbreviation, ABBREVIATION_TAG))
                continue

            word = word.replace('.', '')
            if word.lower() in stopwords or not any([c for c in word if unicode_cat_major(c) == 'L']):
                tagged_sentence.append((token_pos, token, word.lower().replace('.', ''), STOPWORD_TAG))
                continue

            tagged_sentence.append((token_pos, token, word, CONTENT_WORD_TAG))
        tagged_sentences.append(tagged_sentence)
    return tagged_sentences


def apply_snowball_stemmer(tagged_sentences: List[List[Tuple]], stemmer: Stemmer) -> List[List[Tuple]]:
    stemmed_sentences = []
    for sentence in tagged_sentences:
        stemmed = []
        for pos, text_repr, surface_repr, tag in sentence:
            word = surface_repr.lower() if tag in [CONTENT_WORD_TAG, STOPWORD_TAG] else surface_repr
            stemmed.append((pos, text_repr, surface_repr, stemmer.stemWord(word), tag))
        stemmed_sentences.append(stemmed)
    return stemmed_sentences


def simple_tokenizer(text: str, stemmer: Stemmer = None) -> List[List[Tuple]]:
    if stemmer is None:
        stemmer = Stemmer('english')
    text = unicodedata.normalize(UNICODE_NORMALIZATION, text)
    text = normalize_quotation_marks(text)
    paragraphs = split_into_paragraphs(text)

    stopwords = get_stopwords()
    common_abbr = get_common_abbr()
    sentences = split_into_sentences(paragraphs, common_abbr)

    tagged_sentences = tag_sentences(sentences, stopwords, common_abbr)

    tagged_and_stemmed = apply_snowball_stemmer(tagged_sentences, stemmer)

    return tagged_and_stemmed
