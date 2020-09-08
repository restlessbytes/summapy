import unicodedata

from typing import Dict, List, Tuple
from collections import Counter
from Stemmer import Stemmer
from parsing import UNICODE_NORMALIZATION, STOPWORD_TAG
from parsing import unicode_cat_major, normalize_quotation_marks, get_stopwords, simple_tokenizer


def choose_scored_sentences(scored_sentences: List[Tuple[int, float, List]]) -> List[Tuple[int, float, List]]:
    results = []
    avg_score = sum([score for _, score, _ in scored_sentences]) / len(scored_sentences)
    limit = avg_score * 1.25
    for position, score, sentence in scored_sentences:
        if limit <= score:
            results.append((position, score, sentence))
    return results


def reduce_sentences(scored_sentences: List[Tuple[int, float, List[Tuple]]], n_sentences=0) \
        -> List[Tuple[int, float, List[Tuple]]]:
    """
    Filter sentences: remove all sentences whose score is lower than the average score of all sentences; or if
    n_sentences is specified, return the top N sentences (score-wise).

    :param scored_sentences: list of tuples (pos, score, "sentence")
    :param n_sentences: if greater 0, return the top N sentences (instead of all sentences with above-average-score)

    :return: filtered sentences in their 'chronological' text order (that is ordered by ascending position).
    """
    # order by score, then get top sentences (whatever that means)
    if 0 < n_sentences:
        scored_sentences = sorted(scored_sentences, key=lambda t: t[1], reverse=True)[:7]
    else:
        scored_sentences = choose_scored_sentences(scored_sentences)

    # print sentences in their 'chronological' order (i.e. ordered by position)
    return sorted(scored_sentences, key=lambda t: t[0])


def get_top_keywords(scored_terms: Dict, top_n=5) -> List[Tuple[int, str]]:
    ranked_terms = sorted(scored_terms.values(), key=lambda item: item[0], reverse=True)[:top_n]
    ranked_terms = [term for _, _, term in ranked_terms]
    return [(i+1, term) for i, term in enumerate(ranked_terms)]


def score_terms(sentences: List[List[Tuple]]) -> Dict:
    """
    The score of a term (~ word) is calculated as follows:
      1. tf  -> by its term frequency
      2. tag -> by tag (named entities and abbreviations count twice)
      3. df  -> document frequency: in how many sentences does a term appear

    :param sentences: list of list of tuples (pos, text_repr, surface_repr, underlying_repr, tag)
    :return: dictionary with a mapping underlying_repr -> score
    """

    # mapping (ur, tag) -> [terms]
    term_frequencies = dict()
    for sentence in sentences:
        for pos, tr, sr, ur, tag in sentence:
            if tag == STOPWORD_TAG:
                continue
            if (ur, tag) in term_frequencies:
                term_frequencies[(ur, tag)].append(sr)
            else:
                term_frequencies[(ur, tag)] = [sr]

    scores = dict()
    for term, tag in term_frequencies.keys():
        tf = term_frequencies[(term, tag)]
        tf_count = len(tf)
        surface_term, _ = Counter(tf).most_common(1)[0]
        score = tf_count
        scores[term] = (score, tag, surface_term)

    return scores


def score_sentences(scored_terms: Dict, sentences: List[List[Tuple]]) -> List[Tuple[int, float, List]]:
    scored_sentences = []
    for position, sentence in enumerate(sentences):
        score_tuples = [scored_terms.get(ur, (0, '', '')) for _, _, _, ur, _ in sentence]
        score = sum([score for score, _, _ in score_tuples])
        scored_sentences.append((position, score, sentence))
    return scored_sentences


def summarize(text_file: str) -> Dict:
    en_stemmer = Stemmer('english')
    with open(text_file, 'r', encoding='utf-8') as file:
        sentences = simple_tokenizer(file.read(), en_stemmer)

    scored_terms = score_terms(sentences)
    scored_sentences = score_sentences(scored_terms, sentences)

    top_keywords = get_top_keywords(scored_terms)  # TODO those are underlying reprs!
    reduced_text = reduce_sentences(scored_sentences)

    return {
        'top keywords': top_keywords,
        'reduced text': reduced_text,
        'reduced by': (1 - (len(reduced_text) / float(len(sentences))))
    }


def print_summary(summary: Dict, print_scores=False, print_keywords=False, print_reduction_rate=False):
    keywords = summary['top keywords']
    actual_summary = summary['reduced text']
    reduced_by = summary['reduced by']

    for pos, score, sentence in actual_summary:
        sentence_repr = ' '.join([tr for _, tr, _, _, _ in sentence])
        if print_scores:
            print("({}) [{:.3f}] : {}".format(pos, score, sentence_repr))
        else:
            print(sentence_repr)

    if print_keywords:
        print("")
        print('Top 5 Keywords: {}'.format(["{}#{}".format(r, k) for r, k in keywords]))
    if print_reduction_rate:
        print('Original text reduced by {:.2f}%'.format(100 * reduced_by))
    print("")


def main():
    t1 = 'data/taiwan_passport_change-original.txt'
    t2 = 'data/macron-refuses-to-condemn-hebdo-cartoons-original.txt'
    t3 = 'data/us-wont-join-global-covid-vaccine-effort-original.txt'

    for t in [t1, t2, t3]:
        summary = summarize(t)
        print_summary(summary, True, True, True)


if __name__ == '__main__':
    main()
