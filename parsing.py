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


def is_quotation_mark(c: str):
    assert len(c) == 1
    n = unicodedata.name(c)
    return 'QUOTATION MARK' in n or 'APOSTROPHE' in c


def is_sentence_delim(c: str):
    return c in ['.', '!', '?'] if len(c) == 1 else False


def is_sentence_sep(c: str):
    if len(c) != 1:
        return False
    cat = unicodedata.category(c)
    return cat == 'Cc' or cat.startswith('Z')


def is_content_word(word: str, stopwords: Set = None) -> bool:
    if stopwords is None:
        stopwords = get_stopwords()
    return word.lower().strip() not in stopwords and any([c for c in word if unicode_cat_major(c) == 'L'])


def preprocess_text(text: str) -> List[str]:
    text = unicodedata.normalize(UNICODE_NORMALIZATION, text)
    text = normalize_quotation_marks(text)
    text = text.replace('\n\n', '.\n')
    text = text.replace('..\n', '.\n')

    sentence = ''
    sentences = []
    while 3 <= len(text):
        f, s, t = text[:3]
        # case 1 - <delim><{Z}|{Cc}>
        if is_sentence_delim(s) and is_sentence_sep(t):
            sentences.append(sentence + f + s)
            text = text[3:]
            sentence = ''
        # case 2 - <delim><quotation mark><{Z}|{Cc}>
        elif is_sentence_delim(f) and is_quotation_mark(s) and is_sentence_sep(t):
            sentences.append(sentence + f + s)
            text = text[3:]
            sentence = ''
        else:
            text = text[1:]
            sentence += f
    sentence += text
    sentences.append(sentence)
    return [sentence.strip() for sentence in sentences if sentence]


def unicode_cat_major(c) -> str:
    return unicodedata.category(c)[0]


def as_named_entity(word: str, pos: int, stopwords: Set[str]) -> str:
    # A word is potentially a Named Entity if

    # (1) it's capitalized and 1 < len(word)
    if len(word) < 2 or word != word.capitalize():
        return ''

    # (2) it's not at the beginning of a sentence -> 0 < pos
    if pos == 0:
        return ''

    # (3) it's not a stop word
    if word.replace('.', '').lower() in stopwords:
        return ''

    # (4) cannot contain anything but letters, "'" or "-" (except for possibly a dot at the end)
    if word.endswith('.'):
        word = word.replace('.', '')

    if len(word) != len([c for c in word if unicode_cat_major(c) == 'L' or c in ["'", "-"]]):
        return ''

    return word.replace('.', '')


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
        if paragraph[-1] in ['.', '"']:
            paragraphs.append(paragraph)
        else:
            paragraphs.append(paragraph + '.')
    return paragraphs


def split_into_sentences(paragraphs: List[str], stopwords: Set[str], common_abbr: Set[str]) -> List[List[str]]:
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
    """
    Simple (and more rough) tagging of terms.

    :param sentences: list of (raw) string tokens
    :param stopwords: list of common stop words (-> https://dev.mysql.com/doc/refman/8.0/en/fulltext-stopwords.html#fulltext-stopwords-stopwords-for-myisam-search-indexes)
    :param common_abbr: list of common abbreviations (English)

    :return: (list of) list of tuples (pos, text_repr, surface_repr, tag) where
      * pos = position of token in sentence
      * text_repr = raw text representation
      * surface_repr = text_repr minus punctuation etc.
      * tag = one of 'stopword' (SW), 'content word' (CW) or 'abbreviation' (AB)
    """
    # step 1: enumerate -> (pos, text_repr, surface_repr)
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
    """
    Calculate the underlying representation from its surface representation.

    :param tagged_sentences: (list of) list of tuples (pos, text_repr, surface_repr, tag)
    :param stemmer: a Snowball Stemmer
    :return: (list of) list of tuples (pos, text_repr, surface_repr, underlying_repr, tag)
    """
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
    sentences = split_into_sentences(paragraphs, stopwords, common_abbr)

    tagged_sentences = tag_sentences(sentences, stopwords, common_abbr)

    tagged_and_stemmed = apply_snowball_stemmer(tagged_sentences, stemmer)

    return tagged_and_stemmed
