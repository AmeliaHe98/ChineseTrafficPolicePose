import tensorflow as tf
import tensorflow.contrib.layers as layers


def inference_person(image):
    """Person inference net, return 4 stages for loss computing"""
    with tf.variable_scope('PersonNet'):
        conv1_1 = layers.conv2d(image, 64, 3, activation_fn=tf.nn.relu, scope='conv1_1')
        conv1_2 = layers.conv2d(conv1_1, 64, 3, activation_fn=tf.nn.relu, scope='conv1_2')
        pool1_stage1 = layers.max_pool2d(conv1_2, 2, 2)

        conv2_1 = layers.conv2d(pool1_stage1, 128, 3, activation_fn=tf.nn.relu, scope='conv2_1')
        conv2_2 = layers.conv2d(conv2_1, 128, 3, activation_fn=tf.nn.relu, scope='conv2_2')
        pool2_stage1 = layers.max_pool2d(conv2_2, 2, 2)

        conv3_1 = layers.conv2d(pool2_stage1, 256, 3, activation_fn=tf.nn.relu, scope='conv3_1')
        conv3_2 = layers.conv2d(conv3_1, 256, 3, activation_fn=tf.nn.relu, scope='conv3_2')
        conv3_3 = layers.conv2d(conv3_2, 256, 3, activation_fn=tf.nn.relu, scope='conv3_3')
        conv3_4 = layers.conv2d(conv3_3, 256, 3, activation_fn=tf.nn.relu, scope='conv3_4')
        pool3_stage1 = layers.max_pool2d(conv3_4, 2, 2)

        conv4_1 = layers.conv2d(pool3_stage1, 512, 3, activation_fn=tf.nn.relu, scope='conv4_1')
        conv4_2 = layers.conv2d(conv4_1, 512, 3, activation_fn=tf.nn.relu, scope='conv4_2')
        conv4_3 = layers.conv2d(conv4_2, 512, 3, activation_fn=tf.nn.relu, scope='conv4_3')
        conv4_4 = layers.conv2d(conv4_3, 512, 3, activation_fn=tf.nn.relu, scope='conv4_4')
        conv5_1 = layers.conv2d(conv4_4, 512, 3, activation_fn=tf.nn.relu, scope='conv5_1')
        conv5_2_cpm = layers.conv2d(conv5_1, 128, 3, activation_fn=tf.nn.relu, scope='conv5_2_cpm')
        conv6_1_cpm = layers.conv2d(conv5_2_cpm, 512, 1, activation_fn=tf.nn.relu, scope='conv6_1_cpm')
        conv6_2_cpm = layers.conv2d(conv6_1_cpm, 1, 1, activation_fn=None, scope='conv6_2_cpm')

        concat_stage2 = tf.concat(axis=3, values=[conv6_2_cpm, conv5_2_cpm])
        m_conv1_stage2 = layers.conv2d(concat_stage2, 128, 7, activation_fn=tf.nn.relu, scope='m_conv1_stage2')
        m_conv2_stage2 = layers.conv2d(m_conv1_stage2, 128, 7, activation_fn=tf.nn.relu, scope='m_conv2_stage2')
        m_conv3_stage2 = layers.conv2d(m_conv2_stage2, 128, 7, activation_fn=tf.nn.relu, scope='m_conv3_stage2')
        m_conv4_stage2 = layers.conv2d(m_conv3_stage2, 128, 7, activation_fn=tf.nn.relu, scope='m_conv4_stage2')
        m_conv5_stage2 = layers.conv2d(m_conv4_stage2, 128, 7, activation_fn=tf.nn.relu, scope='m_conv5_stage2')
        m_conv6_stage2 = layers.conv2d(m_conv5_stage2, 128, 1, activation_fn=tf.nn.relu, scope='m_conv6_stage2')
        m_conv7_stage2 = layers.conv2d(m_conv6_stage2, 1, 1, activation_fn=None, scope='m_conv7_stage2')

        concat_stage3 = tf.concat(axis=3, values=[m_conv7_stage2, conv5_2_cpm])
        m_conv1_stage3 = layers.conv2d(concat_stage3,  128, 7, activation_fn=tf.nn.relu, scope='m_conv1_stage3')
        m_conv2_stage3 = layers.conv2d(m_conv1_stage3, 128, 7, activation_fn=tf.nn.relu, scope='m_conv2_stage3')
        m_conv3_stage3 = layers.conv2d(m_conv2_stage3, 128, 7, activation_fn=tf.nn.relu, scope='m_conv3_stage3')
        m_conv4_stage3 = layers.conv2d(m_conv3_stage3, 128, 7, activation_fn=tf.nn.relu, scope='m_conv4_stage3')
        m_conv5_stage3 = layers.conv2d(m_conv4_stage3, 128, 7, activation_fn=tf.nn.relu, scope='m_conv5_stage3')
        m_conv6_stage3 = layers.conv2d(m_conv5_stage3, 128, 1, activation_fn=tf.nn.relu, scope='m_conv6_stage3')
        m_conv7_stage3 = layers.conv2d(m_conv6_stage3, 1, 1, activation_fn=None, scope='m_conv7_stage3')

        concat_stage4 = tf.concat(axis=3, values=[m_conv7_stage3, conv5_2_cpm])
        m_conv1_stage4 = layers.conv2d(concat_stage4,  128, 7, activation_fn=tf.nn.relu, scope='m_conv1_stage4')
        m_conv2_stage4 = layers.conv2d(m_conv1_stage4, 128, 7, activation_fn=tf.nn.relu, scope='m_conv2_stage4')
        m_conv3_stage4 = layers.conv2d(m_conv2_stage4, 128, 7, activation_fn=tf.nn.relu, scope='m_conv3_stage4')
        m_conv4_stage4 = layers.conv2d(m_conv3_stage4, 128, 7, activation_fn=tf.nn.relu, scope='m_conv4_stage4')
        m_conv5_stage4 = layers.conv2d(m_conv4_stage4, 128, 7, activation_fn=tf.nn.relu, scope='m_conv5_stage4')
        m_conv6_stage4 = layers.conv2d(m_conv5_stage4, 128, 1, activation_fn=tf.nn.relu, scope='m_conv6_stage4')
        m_conv7_stage4 = layers.conv2d(m_conv6_stage4, 1, 1, activation_fn=None, scope='m_conv7_stage4')

        return [conv6_2_cpm, m_conv7_stage2, m_conv7_stage3, m_conv7_stage4]


class PersonPredictor:
    def __init__(self, input_image):
        self.stage_losses = None
        self.total_loss = None  # Loss to be optimized
        self.heatmaps = inference_person(input_image)
        self.output = self.heatmaps[-1]
        self.output_shape = self.output.get_shape().as_list()
        self.loss_summary = None

    def build_loss(self, heatmap_gt):
        self.stage_losses = []
        for stage, heatmap in enumerate(self.heatmaps):
            stage_loss = tf.nn.l2_loss(heatmap - heatmap_gt)
            self.stage_losses.append(stage_loss)
            tf.summary.scalar("stage"+str(stage), stage_loss)
        self.total_loss = tf.reduce_mean(self.stage_losses)


def add_gradient_summary(grads):
    for grad, var in grads:
        if grad is not None:
            tf.summary.histogram(var.op.name + "/gradient", grad)

