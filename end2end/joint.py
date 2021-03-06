"""Example running MemN2N on a single bAbI task.
Download tasks from facebook.ai/babi """
from __future__ import absolute_import
from __future__ import print_function

from data_utils import load_task, vectorize_data
from sklearn import metrics
from sklearn.model_selection import train_test_split
from memn2n import MemN2N
from itertools import chain
from six.moves import range, reduce

import os
import pickle

import tensorflow as tf
import numpy as np
import pandas as pd

# Make only 1 GPU available to CUDA
os.environ['CUDA_VISIBLE_DEVICES']="0" # Comma separated indexes of GPUs to use - GPUs are indexed from 0 to 7 on the workstation

# Set the options to limit the memory allocation on GPUs
tf_gpu_options = tf.GPUOptions(allow_growth=True,per_process_gpu_memory_fraction = 0.5)

tf.flags.DEFINE_float("learning_rate", 0.001, "Learning rate for Adam Optimizer.")
tf.flags.DEFINE_float("epsilon", 1e-8, "Epsilon value for Adam Optimizer.")
tf.flags.DEFINE_float("regularization", 1e-5, "Regularization.")
tf.flags.DEFINE_float("max_grad_norm", 40.0, "Clip gradients to this norm.")
tf.flags.DEFINE_integer("evaluation_interval", 10, "Evaluate and print results every x epochs")
tf.flags.DEFINE_integer("batch_size", 32, "Batch size for training.")
tf.flags.DEFINE_integer("hops", 3, "Number of hops in the Memory Network.")
tf.flags.DEFINE_integer("epochs", 200, "Number of epochs to train for.")
# tf.flags.DEFINE_integer("epochs", 10, "Number of epochs to train for.")
tf.flags.DEFINE_integer("early", 50, "Number of epochs for early stopping. Should be divisible by evaluation_interval.")
tf.flags.DEFINE_integer("embedding_size", 50, "Embedding size for embedding matrices.")
tf.flags.DEFINE_integer("memory_size", 50, "Maximum size of memory.")
tf.flags.DEFINE_integer("random_state", None, "Random state.")
tf.flags.DEFINE_string("data_dir", "data/tasks_1-20_v1-2/en/", "Directory containing bAbI tasks")
tf.flags.DEFINE_string("output_file", "logs/scores.alpha_{}.lambda_{}.csv", "Name of output file for final bAbI accuracy scores.")
FLAGS = tf.flags.FLAGS

print("Started Joint Model")
print("alpha = {}".format(FLAGS.learning_rate))
print("lambda = {}".format(FLAGS.regularization))
print("hops = {}".format(FLAGS.hops))
print("early stopping = {}".format(FLAGS.early))
print("embedding size = {}".format(FLAGS.embedding_size))
print("memory size = {}".format(FLAGS.memory_size))

# load all train/test data
ids = range(1, 21)
train, test = [], []
for i in ids:
    tr, te = load_task(FLAGS.data_dir, i)
    train.append(tr)
    test.append(te)
data = list(chain.from_iterable(train + test))

def get_log_dir_name():
    lr = FLAGS.learning_rate
    eps = FLAGS.epsilon
    mgn = FLAGS.max_grad_norm
    hp = FLAGS.hops
    es = FLAGS.embedding_size
    ms = FLAGS.memory_size
    # ti = FLAGS.task_id
    reg = FLAGS.regularization

    log_dir_name = "lr={0}_eps={1}_mgn={2}_hp={3}_es={4}_ms={5}_reg={6}".format(lr, eps, mgn, hp, es, ms, reg)
    return os.path.join('./logs/joint/', log_dir_name)

def get_wt_dir_name():
    lr = FLAGS.learning_rate
    eps = FLAGS.epsilon
    mgn = FLAGS.max_grad_norm
    hp = FLAGS.hops
    es = FLAGS.embedding_size
    ms = FLAGS.memory_size
    # ti = FLAGS.task_id
    reg = FLAGS.regularization

    log_dir_name = "lr={0}_eps={1}_mgn={2}_hp={3}_es={4}_ms={5}_reg={6}".format(lr, eps, mgn, hp, es, ms, reg)
    return os.path.join('./weights', log_dir_name)

def gen_writers(sess, base_dir):
    writers = {}
    writers["loss"] = tf.summary.FileWriter(os.path.join(base_dir, "loss") , sess.graph)

    for i in range(1, 21):
        writers["task{0}".format(i)] = tf.summary.FileWriter(os.path.join(base_dir, "task{0}".format(i)), sess.graph)

    return writers

vocab = sorted(reduce(lambda x, y: x | y, (set(list(chain.from_iterable(s)) + q + a) for s, q, a in data)))
word_idx = dict((c, i + 1) for i, c in enumerate(vocab))

max_story_size = max(map(len, (s for s, _, _ in data)))
mean_story_size = int(np.mean([ len(s) for s, _, _ in data ]))
sentence_size = max(map(len, chain.from_iterable(s for s, _, _ in data)))
query_size = max(map(len, (q for _, q, _ in data)))
memory_size = min(FLAGS.memory_size, max_story_size)
#
# # Add time words/indexes
# for i in range(memory_size):
#     word_idx['time{}'.format(i+1)] = 'time{}'.format(i+1)

vocab_size = len(word_idx) + 1 # +1 for nil word
# sentence_size = max(query_size, sentence_size) # for the position
sentence_size = 196
# sentence_size += 1  # +1 for time words

print("Vocab length", vocab_size)
print("Longest sentence length", sentence_size)
print("Longest story length", max_story_size)
print("Average story length", mean_story_size)

# train/validation/test sets
trainS = []
valS = []
trainQ = []
valQ = []
trainA = []
valA = []
for task in train:
    S, Q, A = vectorize_data(task, word_idx, sentence_size, memory_size)
    ts, vs, tq, vq, ta, va = train_test_split(S, Q, A, test_size=0.1, random_state=FLAGS.random_state)
    # ts, vs, tq, vq, ta, va = cross_validation.train_test_split(S, Q, A, test_size=0.1, random_state=FLAGS.random_state)
    trainS.append(ts)
    trainQ.append(tq)
    trainA.append(ta)
    valS.append(vs)
    valQ.append(vq)
    valA.append(va)

trainS = reduce(lambda a,b : np.vstack((a,b)), (x for x in trainS))
trainQ = reduce(lambda a,b : np.vstack((a,b)), (x for x in trainQ))
trainA = reduce(lambda a,b : np.vstack((a,b)), (x for x in trainA))
valS = reduce(lambda a,b : np.vstack((a,b)), (x for x in valS))
valQ = reduce(lambda a,b : np.vstack((a,b)), (x for x in valQ))
valA = reduce(lambda a,b : np.vstack((a,b)), (x for x in valA))

testS, testQ, testA = vectorize_data(list(chain.from_iterable(test)), word_idx, sentence_size, memory_size)

n_train = trainS.shape[0]
n_val = valS.shape[0]
n_test = testS.shape[0]

print("Training Size", n_train)
print("Validation Size", n_val)
print("Testing Size", n_test)

print(trainS.shape, valS.shape, testS.shape)
print(trainQ.shape, valQ.shape, testQ.shape)
print(trainA.shape, valA.shape, testA.shape)

train_labels = np.argmax(trainA, axis=1)
test_labels = np.argmax(testA, axis=1)
val_labels = np.argmax(valA, axis=1)

tf.set_random_seed(FLAGS.random_state)
batch_size = FLAGS.batch_size

# This avoids feeding 1 task after another, instead each batch has a random sampling of tasks
batches = list(zip(range(0, n_train-batch_size, batch_size), range(batch_size, n_train, batch_size)))
# batches = [(start, end) for start,end in batches]

tasks = range(0, 20) # TODO normally range(0,20)
best_test_accs = [-1] * len(tasks)
best_val_accs = [-1] * len(tasks)
best_val_epochs = [-1] * len(tasks)
best_val_update_epoch = -1
stop_early = False
best_train_accs = []


with tf.Session(config = tf.ConfigProto(gpu_options = tf_gpu_options)) as sess:
    print(batch_size, vocab_size, sentence_size, memory_size, FLAGS.embedding_size, FLAGS.hops, FLAGS.max_grad_norm, FLAGS.regularization, FLAGS.learning_rate, FLAGS.epsilon)

    model = MemN2N(batch_size, vocab_size, sentence_size, memory_size, FLAGS.embedding_size, session=sess,
                   hops=FLAGS.hops, max_grad_norm=FLAGS.max_grad_norm, l2=FLAGS.regularization, lr=FLAGS.learning_rate, epsilon=FLAGS.epsilon, nonlin=tf.nn.relu)

    writers = gen_writers(sess, get_log_dir_name())

    for i in range(1, FLAGS.epochs+1):
        # # Stepped learning rate
        # if i - 1 <= FLAGS.anneal_stop_epoch:
        #     anneal = 2.0 ** ((i - 1) // FLAGS.anneal_rate)
        # else:
        #     anneal = 2.0 ** (FLAGS.anneal_stop_epoch // FLAGS.anneal_rate)
        # lr = FLAGS.learning_rate / anneal

        np.random.shuffle(batches)
        total_cost = 0.0
        for start, end in batches:
            end = start + batch_size
            s = trainS[start:end]
            q = trainQ[start:end]
            a = trainA[start:end]
            cost_t, cost_t_summary, cost_ema = model.batch_fit(s, q, a)
            total_cost += cost_t

        total_cost_summary = tf.summary.scalar("epoch_loss", total_cost)
        tcs = sess.run(total_cost_summary)
        writers["loss"].add_summary(tcs, i)

        if i % FLAGS.evaluation_interval == 0:
            train_accs = []
            # for start in range(0, n_train, int(n_train/20)):
            for start in [task * int(n_train/20) for task in tasks]:
                end = start + int(n_train/20)
                s = trainS[start:end]
                q = trainQ[start:end]
                pred = model.predict(s, q)
                acc = metrics.accuracy_score(pred, train_labels[start:end])
                train_accs.append(acc)

            val_accs = []
            # for start in range(0, n_val, n_val/20):
            for task in tasks:
                start = task * int(n_val/20)
                end = start + int(n_val/20)
                s = valS[start:end]
                q = valQ[start:end]
                pred = model.predict(s, q)
                acc = metrics.accuracy_score(pred, val_labels[start:end])
                val_accs.append(acc)

                if acc > best_val_accs[task]:
                    best_val_accs[task] = acc
                    best_val_epochs[task] = i
                    best_val_update_epoch = i
                    # test predictions for this task
                    start = task * int(n_test/20)
                    end = start + int(n_test/20)
                    s = testS[start:end]
                    q = testQ[start:end]
                    pred = model.predict(s, q)
                    acc = metrics.accuracy_score(pred, test_labels[start:end])
                    best_test_accs[task] = acc

            average_acc = np.average(val_accs)
            if best_val_update_epoch == i:
                # something was updated in this epoch
                new_test_bests = [test_acc if best_val_epochs[task] == i else "unchanged" for task, test_acc in enumerate(best_test_accs)]
                accs = zip(train_accs, val_accs, new_test_bests)
                best_train_accs = train_accs
            else:
                if i - FLAGS.early >= best_val_update_epoch:
                    stop_early = True
                accs = zip(train_accs, val_accs)

            print('-----------------------')
            print('Epoch', i)
            print('Total Cost:', total_cost)
            print()

            # t = 1
            # for t1, t2, t3 in zip(train_accs, val_accs, test_accs):
            for t, tup in enumerate(accs):
                print("Task {}".format(t+1))
                print("Training Accuracy = {}".format(tup[0]))
                print("Validation Accuracy = {}".format(tup[1]))
                if len(tup) > 2:
                    print("Testing Accuracy = {}".format(tup[2]))
                print()
                # t += 1

                train_acc_summary = tf.summary.scalar("train_acc", tup[0])
                val_acc_summary = tf.summary.scalar("val_acc", tup[1])

                vas = sess.run(val_acc_summary)
                tas = sess.run(train_acc_summary)

                writers["task{0}".format(t+1)].add_summary(vas, i)
                writers["task{0}".format(t+1)].add_summary(tas, i)

            print('-----------------------')

        # Write final results to csv file
        # if i == FLAGS.epochs:
        if stop_early or i == FLAGS.epochs:
            # save model data
            model.save_model(get_wt_dir_name())
            res = {'vocab': vocab, 'w_idx': word_idx, 'sentence_size': sentence_size, 'memory_size': memory_size}
            with open('./weights/vocab_data.pickle', 'wb') as fl:
              pickle.dump(res, fl)

            output_file = FLAGS.output_file.format(FLAGS.learning_rate, FLAGS.regularization)
            print('Writing final results to {}'.format(output_file))
            df = pd.DataFrame({
            'Training Accuracy': best_train_accs,
            'Validation Accuracy': best_val_accs,
            'Testing Accuracy': best_test_accs,
            'Best Epoch': best_val_epochs
            }, index=range(1,21))
            df.index.name = 'Task'
            df.to_csv(output_file)
            if stop_early:
                break
