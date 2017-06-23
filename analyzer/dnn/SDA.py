# -*- coding: utf-8 -*-

import json
import logging
import six.moves.cPickle as pickle
import datetime
import numpy as np
from sklearn.datasets import fetch_mldata
from sklearn.cross_validation import train_test_split
from chainer import cuda, Variable, FunctionSet, optimizers
import chainer.functions as F

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from DA import DA

try:
    from pyhark.ssi.utils.logback import AdvancedEncoder
except:
    from utils.logback import AdvancedEncoder


class SDA(object):
    def __init__(
        self,
        rng,
        data,
        target,
        n_inputs=240,
        n_hidden=[120, 60, 30],
        n_outputs=10,
        gpu=-1
    ):
        self.model = FunctionSet(
            l1=F.Linear(n_inputs, n_hidden[0]),
            l2=F.Linear(n_hidden[0], n_hidden[1]),
            l3=F.Linear(n_hidden[1], n_hidden[2]),
            l4=F.Linear(n_hidden[2], n_outputs)
        )

        if gpu >= 0:
            self.model.to_gpu()

        self.rng = rng
        self.gpu = gpu
        self.data = data
        self.target = target

        self.x_train, self.x_test = data
        self.y_train, self.y_test = target

        self.n_train = len(self.y_train) if not self.y_train is None else 0
        self.n_test = len(self.y_test) if not self.y_test is None else 0

        self.n_inputs = n_inputs
        self.n_hidden = n_hidden
        self.n_outputs = n_outputs

        self.dae1 = None
        self.dae2 = None
        self.dae3 = None
        self.optimizer = None

        self.train_accuracies = []
        self.test_accuracies = []

    def setup_optimizer(self):
        self.optimizer = optimizers.Adam()
        # self.optimizer = optimizers.SGD()
        self.optimizer.setup(self.model.collect_parameters())

    def pre_train(self, n_epoch=20, batchsize=100):
        first_inputs = self.data

        # initialize first dAE
        self.dae1 = DA(
            self.rng,
            data=first_inputs,
            n_inputs=self.n_inputs,
            n_hidden=self.n_hidden[0],
            gpu=self.gpu,
            sparse=False
        )
        # train first dAE

        logging.debug("--------First DA training has started!--------")
        self.dae1.train_and_test(n_epoch=n_epoch, batchsize=batchsize)
        # compute second iputs for second dAE
        tmp1 = self.dae1.compute_hidden(first_inputs[0])
        tmp2 = self.dae1.compute_hidden(first_inputs[1])
        second_inputs = [tmp1, tmp2]

        # initialize second dAE
        self.dae2 = DA(
            self.rng,
            data=second_inputs,
            n_inputs=self.n_hidden[0],
            n_hidden=self.n_hidden[1],
            gpu=self.gpu,
            sparse=False
        )

        # train second dAE
        logging.debug("--------Second DA training has started!--------")
        self.dae2.train_and_test(n_epoch=n_epoch, batchsize=batchsize)
        # compute third inputs for third dAE
        tmp1 = self.dae2.compute_hidden(second_inputs[0])
        tmp2 = self.dae2.compute_hidden(second_inputs[1])
        third_inputs = [tmp1, tmp2]

        # initialize third dAE
        self.dae3 = DA(
            self.rng,
            data=third_inputs,
            n_inputs=self.n_hidden[1],
            n_hidden=self.n_hidden[2],
            gpu=self.gpu,
            sparse=True
        )
        # train third dAE
        logging.debug("--------Third DA training has started!--------")
        self.dae3.train_and_test(n_epoch=n_epoch, batchsize=batchsize)

        # update model parameters
        self.model.l1 = self.dae1.encoder()
        self.model.l2 = self.dae2.encoder()
        self.model.l3 = self.dae3.encoder()

        self.setup_optimizer()

    def forward(self, x_data, y_data, train=True):
        if self.gpu >= 0:
            x_data = cuda.to_gpu(x_data)
            y_data = cuda.to_gpu(y_data)

        x, t = Variable(x_data), Variable(y_data)
        h1 = F.dropout(F.relu(self.model.l1(x)), train=train)
        h2 = F.dropout(F.relu(self.model.l2(h1)), train=train)
        h3 = F.dropout(F.relu(self.model.l3(h2)), train=train)
        y = self.model.l4(h3)
        return F.softmax_cross_entropy(y, t), F.accuracy(y, t)

    def get_hidden_values(self, x_data, train=False):
        if self.gpu >= 0:
            x_data = cuda.to_gpu(x_data)
        x = Variable(x_data)
        h1 = F.dropout(F.relu(self.model.l1(x)), train=train)
        h2 = F.dropout(F.relu(self.model.l2(h1)), train=train)
        h3 = F.dropout(F.relu(self.model.l3(h2)), train=train)
        return h3.data

    def fine_tune(self, n_epoch=20, batchsize=100, logger=None):
        if logger is None:
            logger = logging.root

        for epoch in xrange(1, n_epoch+1):
            logging.debug('fine tuning epoch: %d' % epoch)

            perm = self.rng.permutation(self.n_train)
            sum_accuracy = 0
            sum_loss = 0
            for i in xrange(0, self.n_train, batchsize):
                x_batch = self.x_train[perm[i:i+batchsize]]
                y_batch = self.y_train[perm[i:i+batchsize]]

                real_batchsize = len(x_batch)

                if self.gpu >= 0:
                    x_batch = cuda.to_gpu(x_batch)
                    y_batch = cuda.to_gpu(y_batch)

                self.optimizer.zero_grads()
                loss, acc = self.forward(x_batch, y_batch)
                loss.backward()
                self.optimizer.update()

                sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize
                sum_accuracy += float(cuda.to_cpu(acc.data)) * real_batchsize

            train_loss = sum_loss / self.n_train
            train_accuracy = sum_accuracy / self.n_train
            self.train_accuracies.append(train_accuracy)
            logger.info(
                'fine tuning train mean loss={}, accuracy={}'.format(train_loss, train_accuracy)
            )

            # evaluation
            sum_accuracy = 0
            sum_loss = 0
            for i in xrange(0, self.n_test, batchsize):
                x_batch = self.x_test[i:i+batchsize]
                y_batch = self.y_test[i:i+batchsize]

                real_batchsize = len(x_batch)

                if self.gpu >= 0:
                    x_batch = cuda.to_gpu(x_batch)
                    y_batch = cuda.to_gpu(y_batch)

                loss, acc = self.forward(x_batch, y_batch, train=False)

                sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize
                sum_accuracy += float(cuda.to_cpu(acc.data)) * real_batchsize

            test_loss = sum_loss / self.n_test
            test_accuracy = sum_accuracy / self.n_test
            self.test_accuracies.append(test_accuracy)
            logger.info(
                'fine tuning test mean loss={}, accuracy={}'.format(
                    test_loss, test_accuracy
                )
            )

        logger.info(
            "best_accuracy: train> {}, test>{}".format(
                max(self.train_accuracies), max(self.test_accuracies)
            )
        )
        return max(self.train_accuracies), max(self.test_accuracies)

    def dump_model(self, filename=None):
        self.model.to_cpu()
        if filename is None:
            pickle.dump(self.model, open(self.model_name, 'wb'), -1)
        else:
            pickle.dump(self.model, open(filename, 'wb'), -1)

    def load_model(self):
        self.model = pickle.load(open(self.model_name, 'rb'))
        if self.gpu >= 0:
            self.model.to_gpu()
        self.optimizer.setup(self.model.collect_parameters())

    def create_accuracy_transition_figure(self, filename):
        plt.plot(
            xrange(len(self.train_accuracies)),
            self.train_accuracies,
            label="train", color="grey"
        )
        plt.plot(
            xrange(len(self.test_accuracies)),
            self.test_accuracies,
            label="test", color="cyan"
        )

        plt.xlabel("epoch")
        plt.ylabel("accuracy")
        plt.title("accuracy transition")
        plt.legend(loc=2)

        plt.savefig(filename)

    @classmethod
    def pretrain(
        cls,
        data,
        epochs=1,
        n_inputs=-1,
        hiddens=None,
        n_outputs=1,
        gpu=-1,
        logger=None
    ):
        if logger is None:
            logger = logging.root

        n_inputs = data[0].shape[1] if n_inputs < 0 else n_inputs
        hiddens = [n_inputs / 2, n_inputs / 2, n_inputs / 2] if hiddens is None else hiddens

        logger.info('variables: %s', json.dumps(locals(), indent=4, cls=AdvancedEncoder))

        rng = np.random.RandomState(1)
        if gpu >= 0:
            logging.info('using gpu %d ...' % gpu)
            cuda.check_cuda_available()

        logger.debug('creating sda instance ...')
        sda = SDA(
            rng=rng,
            data=data,
            target=[None, None],
            n_inputs=n_inputs,
            n_hidden=hiddens,
            n_outputs=n_outputs,
            gpu=gpu,
        )

        logger.debug('executing pre-training ...')
        sda.pre_train(n_epoch=epochs)

        modelpath = "sda_model.%d.in-%d.hiddens-%s.pre-%d.%s.pkl" % (
            data[0].shape[1],
            n_inputs, str(hiddens),
            epochs,
            datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        )
        logger.info('saving model in {} ...'.format(modelpath))
        sda.dump_model(modelpath)

        figurepath = "sda_accuracies.%d.in-%d.hiddens-%s.pre-%d.%s.png" % (
            data[0].shape[1],
            n_inputs, str(hiddens),
            epochs,
            datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        )
        sda.create_accuracy_transition_figure(figurepath)

        return sda

    @classmethod
    def train(
        cls,
        data, target,
        pretraining_epochs=1, finetuning_epochs=1,
        n_inputs=-1, hiddens=None, n_outputs=-1,
        gpu=-1, logger=None
    ):
        if logger is None:
            logger = logging.root

        n_inputs = data[0].shape[1] if n_inputs < 0 else n_inputs
        n_outputs = len(set(target[0])) if n_outputs < 0 else n_outputs
        hiddens = [n_inputs / 2, n_inputs / 2, n_inputs / 2] if hiddens is None else hiddens

        logger.info('variables: %s', json.dumps(locals(), indent=4, cls=AdvancedEncoder))

        rng = np.random.RandomState(1)
        if gpu >= 0:
            logging.info('using gpu %d ...' % gpu)
            cuda.check_cuda_available()

        logger.debug('creating sda instance ...')
        sda = SDA(
            rng=rng,
            data=data,
            target=target,
            n_inputs=n_inputs,
            n_hidden=hiddens,
            n_outputs=n_outputs,
            gpu=gpu,
        )

        logger.debug('executing pre-training ...')
        sda.pre_train(n_epoch=pretraining_epochs)
        logger.debug('executing fine-tuning ...')
        sda.fine_tune(n_epoch=finetuning_epochs, logger=logger)

        modelpath = "sda_model.%d.in-%d.hiddens-%s.out-%d.pre-%d.fine-%d.%s.pkl" % (
            data[0].shape[1],
            n_inputs, str(hiddens), n_outputs,
            pretraining_epochs, finetuning_epochs,
            datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        )
        logger.info('saving model in {} ...'.format(modelpath))
        sda.dump_model(modelpath)

        figurepath = "sda_accuracies.%d.in-%d.hiddens-%s.out-%d.pre-%d.fine-%d.%s.png" % (
            data[0].shape[1],
            n_inputs, str(hiddens), n_outputs,
            pretraining_epochs, finetuning_epochs,
            datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        )
        sda.create_accuracy_transition_figure(figurepath)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='MNIST')
    parser.add_argument('--gpu', '-g', default=-1, type=int,
                        help='GPU ID (negative value indicates CPU)')
    args = parser.parse_args()

    print 'fetch MNIST dataset'
    mnist = fetch_mldata('MNIST original')
    mnist.data = mnist.data.astype(np.float32)
    mnist.data /= 255
    mnist.target = mnist.target.astype(np.int32)

    data_train, data_test, target_train, target_test = train_test_split(mnist.data, mnist.target)

    print 'data_train', type(data_train), data_train.shape
    print 'target_train', type(target_train), target_train.shape

    data = [data_train, data_test]
    target = [target_train, target_test]

    SDA.train(data, target)
