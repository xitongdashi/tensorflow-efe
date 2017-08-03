from model import Model
import tensorflow as tf
import datetime
import numpy as np
import config
from utils.tf_utils import *

class TransE_L2(Model):
	def __init__(self, n_entities, n_relations, hparams):
		super(TransE_L2, self).__init__(n_entities, n_relations, hparams)
		self.margin = hparams.margin
		self.build()
	
	def add_params(self):
		minVal = -6/np.sqrt(self.embedding_size)
		maxVal = -minVal
		self.entity_embedding = tf.Variable(tf.random_uniform([self.n_entities, self.embedding_size], minVal, maxVal, seed=config.RANDOM_SEED), dtype=tf.float32, name="entity_embedding")
		self.relation_embedding = tf.Variable(tf.nn.l2_normalize(tf.random_uniform([self.n_relations, self.embedding_size], minVal, maxVal, seed=config.RANDOM_SEED), -1), dtype=tf.float32, name="relation_embedding")

		normalized_entity_embedding = tf.nn.l2_normalize(self.entity_embedding, -1)
		self.normalization = self.entity_embedding.assign(normalized_entity_embedding)

	def add_prediction_op(self):
		self.e1 = tf.nn.embedding_lookup(self.entity_embedding, self.heads)
		self.e2 = tf.nn.embedding_lookup(self.entity_embedding, self.tails)
		self.r = tf.nn.embedding_lookup(self.relation_embedding, self.relations)

		self.pred = - l2_loss(self.e1 + self.r - self.e2)

	def add_loss_op(self):
		pos_size, neg_size = self.batch_size, self.batch_size * self.neg_ratio
		score_pos, score_neg = tf.split(self.pred, [pos_size, neg_size])

		losses = tf.maximum(0.0, self.margin - score_pos \
				+ tf.reduce_mean(tf.reshape(score_neg, (self.batch_size, self.neg_ratio)), -1))
		self.loss = tf.reduce_mean(losses)
	
	def train_on_batch(self, sess, input_batch):
		feed = self.create_feed_dict(**input_batch)
		sess.run(self.normalization)
		_, step, loss = sess.run([self.train_op, self.global_step, self.loss], feed_dict=feed)
		time_str = datetime.datetime.now().isoformat()
		print("{}: step {}, loss {:g}".format(time_str, step, loss))

class TransE_L1(TransE_L2):
	def add_prediction_op(self):
		self.e1 = tf.nn.embedding_lookup(self.entity_embedding, self.heads)
		self.e2 = tf.nn.embedding_lookup(self.entity_embedding, self.tails)
		self.r = tf.nn.embedding_lookup(self.relation_embedding, self.relations)

		self.pred = - l1_loss(self.e1 + self.r - self.e2)

	def add_loss_op(self):
		pos_size, neg_size = self.batch_size, self.batch_size * self.neg_ratio
		score_pos, score_neg = tf.split(self.pred, [pos_size, neg_size])

		losses = tf.maximum(0.0, self.margin - score_pos \
				+ tf.reduce_mean(tf.reshape(score_neg, (self.batch_size, self.neg_ratio)), -1))
		self.loss = tf.reduce_mean(losses)

class DistMult(Model):
	def __init__(self, n_entities, n_relations, hparams):
		super(DistMult, self).__init__(n_entities, n_relations, hparams)
		self.margin = hparams.margin
		self.l2_reg_lambda = hparams.l2_reg_lambda
		self.build()

	def add_params(self):
		self.entity_embedding = tf.Variable(tf.random_uniform([self.n_entities, self.embedding_size], 0., 1., seed=config.RANDOM_SEED), dtype=tf.float32, name="entity_embedding")
		self.relation_embedding = tf.Variable(tf.random_uniform([self.n_relations, self.embedding_size], 0., 1., seed=config.RANDOM_SEED), dtype=tf.float32, name="relation_embedding")
	
		normalized_entity_embedding = tf.nn.l2_normalize(self.entity_embedding, -1)
		self.normalization = self.entity_embedding.assign(normalized_entity_embedding)

	def add_prediction_op(self):
		self.e1 = tf.nn.embedding_lookup(self.entity_embedding, self.heads)
		self.e2 = tf.nn.embedding_lookup(self.entity_embedding, self.tails)
		self.r = tf.nn.embedding_lookup(self.relation_embedding, self.relations)

		self.pred = tf.reduce_sum(self.e1 * self.r * self.e2, -1)

	def add_loss_op(self):
		pos_size, neg_size = self.batch_size, self.batch_size * self.neg_ratio
		score_pos, score_neg = tf.split(self.pred, [pos_size, neg_size])

		losses = tf.maximum(0.0, self.margin - score_pos \
				+ tf.reduce_mean(tf.reshape(score_neg, (self.batch_size, self.neg_ratio)), axis=-1))
		#self.l2_loss = tf.nn.l2_loss(self.r)
		self.loss = tf.reduce_mean(losses) + self.l2_reg_lambda * self.l2_loss

	def train_on_batch(self, sess, input_batch):
		feed = self.create_feed_dict(**input_batch)
		sess.run(self.normalization)
		_, step, loss = sess.run([self.train_op, self.global_step, self.loss], feed_dict=feed)
		time_str = datetime.datetime.now().isoformat()
		print("{}: step {}, loss {:g}".format(time_str, step, loss))

class DistMult_tanh(DistMult):
	def add_prediction_op(self):
		self.e1 = tf.tanh(tf.nn.embedding_lookup(self.entity_embedding, self.heads))
		self.e2 = tf.tanh(tf.nn.embedding_lookup(self.entity_embedding, self.tails))
		self.r = tf.nn.embedding_lookup(self.relation_embedding, self.relations)

		self.pred = tf.reduce_sum(self.e1 * self.r * self.e2, -1)

class DistMult_Logistic(Model):
	def __init__(self, n_entities, n_relations, hparams):
		super(DistMult_Logistic, self).__init__(n_entities, n_relations, hparams)
		self.l2_reg_lambda = hparams.l2_reg_lambda
		self.build()

	def add_params(self):
		self.entity_embedding = tf.Variable(tf.random_uniform([self.n_entities, self.embedding_size], 0., 1., seed=config.RANDOM_SEED), dtype=tf.float32, name="entity_embedding")
		self.relation_embedding = tf.Variable(tf.random_uniform([self.n_relations, self.embedding_size], 0., 1., seed=config.RANDOM_SEED), dtype=tf.float32, name="relation_embedding")
	
	def add_prediction_op(self):
		self.e1 = tf.nn.embedding_lookup(self.entity_embedding, self.heads)
		self.e2 = tf.nn.embedding_lookup(self.entity_embedding, self.tails)
		self.r = tf.nn.embedding_lookup(self.relation_embedding, self.relations)

		self.pred = tf.nn.sigmoid(tf.reduce_sum(self.e1 * self.r * self.e2, -1))

	def add_loss_op(self):
		losses = tf.nn.softplus(-self.labels * tf.reduce_sum(self.e1 * self.r * self.e2, -1))
		self.l2_loss = tf.reduce_mean(tf.square(self.e1)) + \
				tf.reduce_mean(tf.square(self.e2)) + \
				tf.reduce_mean(tf.square(self.r))
		self.loss = tf.reduce_mean(losses) + self.l2_reg_lambda * self.l2_loss

class NTN(Model):
	def __init__(self, n_entities, n_relations, hparams):
		super(NTN, self).__init__(n_entities, n_relations, hparams)
