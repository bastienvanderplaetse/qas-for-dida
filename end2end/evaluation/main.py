import argparse
import sys
import os
from os import listdir
from os.path import isfile, join
from data_utils import process_data, decode, reset_dict
from model_helper import get_pred
from pprint import pprint
import numpy as np

INPUT_DIRECTORY = 'texts'
OUTPUT_DIRECTORY = 'outputs'
QUESTIONS = [
    'Which species was studied ?',
    'Which type of study was done ?',
    'Which disease is concerned ?',
    'Which genes are concerned ?'
]

def check_args(argv):
    parser = argparse.ArgumentParser(description="Evaluate the end to end \
        memory network")

    args = parser.parse_args()

    return args

def run(args):
    files = [INPUT_DIRECTORY + '/' + f for f in listdir(INPUT_DIRECTORY) if isfile(join(INPUT_DIRECTORY, f))]
    files.sort()

    if not os.path.exists(OUTPUT_DIRECTORY) or not os.path.isdir(OUTPUT_DIRECTORY):
        os.mkdir(OUTPUT_DIRECTORY)

    latex_ouput = ''

    for filename in files:
        latex_part = "\\paragraph{"
        latex_part += filename.split('/')[-1].split('.pdf.txt.txt')[0]
        latex_part += "}\n\\begin{enumerate}\n"

        f = open(filename,"r",encoding='utf-8', errors='ignore')
        sentences = f.readlines()
        sentences = [sentence.replace('\n', '') for sentence in sentences]

        for question in QUESTIONS:
            latex_part += "\\item " + question + "\\\\\n"
            latex_part += "$\\longrightarrow$ "
            reset_dict()
            testS, testQ, testA = process_data(sentences, question)
            answer, answer_probability, mem_probs = get_pred(testS, testQ)
            memory_probabilities = np.round(mem_probs, 4)

            best_sentence_index = 0
            best_sentence_score = 0
            # print(len(memory_probabilities.tolist()))
            for index, mem in enumerate(memory_probabilities.tolist()):
                if mem[2] > best_sentence_score:
                    best_sentence_index = index
                    best_sentence_score = mem[2]

            words_l = []
            for idw in testS[0][best_sentence_index]:
                if idw == 0:
                    break
                words_l.append(decode(idw))
            sentence = ' '.join(words_l)
            sentence.replace('%', '\\%')
            sentence.replace('_', '\\_')

            latex_part += sentence + "\n"
        latex_part += "\\end{enumerate}"
        latex_ouput += "\n" + latex_part
    f = open(join(OUTPUT_DIRECTORY, 'latex_out.txt'), 'w')
    f.write(latex_ouput)






if __name__=="__main__":
    args = check_args(sys.argv)
    run(args)
