# -*- coding: utf-8 -*-

import sys
import logging
from copy import *
import argparse
import time
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import fetch_mldata
from sklearn.cross_validation import train_test_split
from chainer import cuda, Variable, FunctionSet, optimizers
import chainer.computational_graph as c
import chainer.functions as F


class DA(object):
    def __init__(self, rng, data, n_inputs=784, n_hidden=784, corruption_level=0.3, gpu=-1, sparse=False):
        """Denoising AutoEncoder
        data: data for train
        n_inputs: a number of units of input layer and output layer
        n_hidden: a number of units of hidden layer
        corruption_level: a ratio of masking noise
        """

        self.model = FunctionSet(encoder=F.Linear(n_inputs, n_hidden),
                                 decoder=F.Linear(n_hidden, n_inputs))

        if gpu >= 0:
            self.model.to_gpu()

        self.gpu = gpu

        self.x_train, self.x_test = data

        self.n_train = len(self.x_train)
        self.n_test = len(self.x_test)

        self.optimizer = optimizers.Adam()
        self.optimizer.setup(self.model.collect_parameters())
        self.corruption_level = corruption_level
        self.rng = rng
        self.sparse = sparse

    def forward(self, x_data, train=True):
        y_data = x_data
        # add noise (masking noise)
        # x_data = self.get_corrupted_inputs(x_data, train=train)

        if self.gpu >= 0:
            x_data = cuda.to_gpu(x_data)
            y_data = cuda.to_gpu(y_data)

        x, t = Variable(x_data), Variable(y_data)
        # encode
        h = self.encode(x)
        # decode
        y = self.decode(h)
        # compute loss
        if self.sparse:
            loss = F.mean_squared_error(y, t) + .001 * np.linalg.norm(h.data)
        else:
            loss = F.mean_squared_error(y, t)
        return loss

    def compute_hidden(self, x_data):

        if self.gpu >= 0:
            x_data = cuda.to_gpu(x_data)

        x = Variable(x_data)
        h = self.encode(x)
        return cuda.to_cpu(h.data)

    def predict(self, x_data):
        if self.gpu >= 0:
            x_data = cuda.to_gpu(x_data)

        x = Variable(x_data)
        # encode
        h = self.encode(x)
        # decode
        y = self.decode(h)
        return cuda.to_cpu(y.data)

    def encode(self, x):
        return F.relu(self.model.encoder(x))

    def decode(self, h):
        return F.relu(self.model.decoder(h))

    def encoder(self):
        return self.model.encoder

    def decoder(self):
        return self.model.decoder

    # masking noise
    def get_corrupted_inputs(self, x_data, train=True):
        if train:
            ret = self.rng.binomial(size=x_data.shape, n=1, p=1.0-self.corruption_level) * x_data
            return ret.astype(np.float32)
        else:
            return x_data

    def train_and_test(self, n_epoch=5, batchsize=100):
        for epoch in xrange(1, n_epoch+1):
            print 'epoch', epoch

            perm = self.rng.permutation(self.n_train)
            sum_loss = 0
            for i in xrange(0, self.n_train, batchsize):
                x_batch = self.x_train[perm[i:i+batchsize]]

                real_batchsize = len(x_batch)

                self.optimizer.zero_grads()
                loss = self.forward(x_batch)
                loss.backward()
                self.optimizer.update()

                sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize

            logging.info('train mean loss={}'.format(sum_loss/self.n_train))

            # evaluation
            sum_loss = 0
            for i in xrange(0, self.n_test, batchsize):
                x_batch = self.x_test[i:i+batchsize]

                real_batchsize = len(x_batch)

                loss = self.forward(x_batch, train=False)

                sum_loss += float(cuda.to_cpu(loss.data)) * real_batchsize

            logging.info('test mean loss={}'.format(sum_loss/self.n_test))


# 参考: http://qiita.com/kenmatsu4/items/7b8d24d4c5144a686412
def draw_digit(data):
    size = 28
    X, Y = np.meshgrid(range(size), range(size))
    Z = data.reshape(size, size)   # convert from vector to 28x28 matrix
    Z = Z[::-1, :]             # flip vertical
    plt.xlim(0, 27)
    plt.ylim(0, 27)
    plt.pcolor(X, Y, Z)
    plt.flag()
    plt.gray()
    plt.tick_params(labelbottom="off")
    plt.tick_params(labelleft="off")


def draw_digits(data, fname="fig.png"):
    for i in xrange(3*3):
        plt.subplot(331+i)
        draw_digit(data[i])
    plt.savefig(fname)


if __name__ == '__main__':
    print 'fetch MNIST dataset'
    mnist = fetch_mldata('MNIST original')
    mnist.data = mnist.data.astype(np.float32)
    mnist.data /= 255
    mnist.target = mnist.target.astype(np.int32)

    parser = argparse.ArgumentParser(description='MNIST')
    parser.add_argument('--gpu', '-g', default=-1, type=int,
                        help='GPU ID (negative value indicates CPU)')
    args = parser.parse_args()
    gpu = args.gpu

    if gpu >= 0:
        cuda.init(gpu)

    # draw_digits(mnist.data[0:9])
    rng = np.random.RandomState(1)

    start_time = time.time()

    da = DA(rng=rng, data=mnist.data, gpu=gpu)

    perm = np.random.permutation(N)
    data = mnist.data[perm[0:9]]

    draw_digits(data, fname="input.png")

    da.train_and_test(n_epoch=5)

    predicted = da.predict(data)
    draw_digits(predicted, fname="output_epoch5.png")

    perm = np.random.permutation(784)
    W = da.model.to_cpu().encoder.W[perm[0:9]]
    draw_digits(W, fname="learned_weights.png")

    end_time = time.time()

    print "time = {} min".format((end_time-start_time)/60.0)
