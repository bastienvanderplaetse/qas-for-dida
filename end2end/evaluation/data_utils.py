import re
import numpy as np
import pickle
from pprint import pprint
import string
from functools import cmp_to_key


with open('model/vocab_data.pickle', 'rb') as handle:
  vocab_data = pickle.load(handle)
  # pprint(vocab_data)

decode_dict = {v:k for k,v in vocab_data['w_idx'].items()}

def reset_dict():
    with open('model/vocab_data.pickle', 'rb') as handle:
        vocab_data = pickle.load(handle)

def tokenize(sent):
    '''Return the tokens of a sentence including punctuation.
    >>> tokenize('Bob dropped the apple. Where is the apple?')
    ['Bob', 'dropped', 'the', 'apple', '.', 'Where', 'is', 'the', 'apple', '?']
    '''
    stripped = sent.rstrip()
    stripped = re.sub('([.,!?()])', r' \1 ', sent)
    stripped = re.sub('\s{2,}', ' ', stripped)
    stripped = [x.strip() for x in stripped.split(' ') if len(x) != 0]

    return stripped


def vectorize_data(data, word_idx, sentence_size, memory_size):
    """
    Vectorize stories and queries.

    If a sentence length < sentence_size, the sentence will be padded with 0's.

    If a story length < memory_size, the story will be padded with empty memories.
    Empty memories are 1-D arrays of length sentence_size filled with 0's.

    The answer array is returned as a one-hot encoding.
    """
    S = []
    Q = []
    A = []
    for story, query, answer in data:
        lq = max(0, sentence_size - len(query))
        for w in query:
            if not w in word_idx:
                word_idx[w] = len(word_idx) + 1

        q = [word_idx[w] for w in query] + [0] * lq

        ss = []
        for i, sentence in enumerate(story, 1):
            if len(sentence) > 196:
                sentence = [x for x in sentence if not x in string.punctuation]
                if len(sentence) > 196:
                    sentence = sentence[:196]
            ls = max(0, sentence_size - len(sentence))
            for w in sentence:
                if not w in word_idx:
                    word_idx[w] = len(word_idx) + 1
            ss.append([word_idx[w] for w in sentence] + [0] * ls)

        if len(ss) > memory_size:
            # Use Jaccard similarity to determine the most relevant sentences
            q_words = set(q)
            least_like_q = sorted(ss, key = cmp_to_key(lambda x, y: jaccard(set(x), q_words) < jaccard(set(y), q_words)))[:len(ss)-memory_size]
            for sent in least_like_q:
                # Remove the first occurrence of sent. A list comprehension as in [sent for sent in ss if sent not in least_like_q]
                # should not be used, as it would remove multiple occurrences of the same sentence, some of which might actually make the cutoff.
                ss.remove(sent)
        else:
            # pad to memory_size
            lm = max(0, memory_size - len(ss))
            for _ in range(lm):
                ss.append([0] * sentence_size)

        # take only the most recent sentences that fit in memory
        ss = ss[::-1][:memory_size][::-1]

        # # Make the last word of each sentence the time 'word' which
        # # corresponds to vector of lookup table
        # for i in range(len(ss)):
        #     ss[i][-1] = len(word_idx) - memory_size - i + len(ss)
        #
        # # pad to memory_size
        # lm = max(0, memory_size - len(ss))
        # for _ in range(lm):
        #     ss.append([0] * sentence_size)
        #
        # lq = max(0, sentence_size - len(query))
        # q = [word_idx[w] for w in query] + [0] * lq

        y = np.zeros(len(word_idx) + 1) # 0 is reserved for nil word
        for a in answer:
            y[word_idx[a]] = 1
        # print("++++" + str(len(ss)))
        S.append(ss)
        Q.append(q)
        A.append(y)
        # print(S)
        # print(np.array(S))
        # print("===================")
    return np.array(S), np.array(Q), np.array(A)


def decode(index):
    # print(vocab_data['w_idx'])
    decode_dict = {v:k for k,v in vocab_data['w_idx'].items()}
    return decode_dict.get(index, 'unknown')


def process_data(sentences, question):
    sent = [tokenize(s.lower()) for s in sentences]
    # sent_t = [filter(lambda x: x != ".", s) for s in sent_t]
    sent_t = []
    for s in sent:
        strip_s = []
        for w in s:
            # print(w)
            if w != ".":
                strip_s.append(w)
        sent_t.append(strip_s)
    # sent_t = [s for s in sent_t if s != "."]
    # print("ICIIIIIIIIIIIII")
    # print(sent_t)

    q_t = tokenize(question.lower())
    if q_t[-1] == "?":
        q_t = q_t[:-1]

    data = [(sent_t, q_t, ['where'])]

    testS, testQ, testA = vectorize_data(data, vocab_data['w_idx'], vocab_data['sentence_size'], vocab_data['memory_size'])
    # testS, testQ, testA = vectorize_data(data, vocab_data['w_idx'], maxsize+1, vocab_data['memory_size'])

    return testS, testQ, testA


def jaccard(a, b):
    '''
    Assumes that a and b are sets so that calling code only has to cast the question to set once.
    '''
    return len(a.intersection(b)) / float(len(a.union(b)))
    set(a).intersection(set(b))
