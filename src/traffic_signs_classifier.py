## Imports #################################################
import numpy as np # scientific computations library (http://www.numpy.org/)
import tensorflow as tf # deep learning library (https://www.tensorflow.org/)
import cv2 # OpenCV computer vision library (https://opencv.org/)
import random
import os # file operations
import math
import csv

# Helper function files - plot_utils.py and img_utils.py
from plot_utils import visualize_dataset, plot_confusion_matrix, visualize_training_data_distribution
from img_utils import get_train_images, get_test_images, preprocess_images, transform_image, get_new_test_images
import matplotlib.pyplot as plt
#############################################################

## Global Variables ##############################################
NUM_CLASSES = 43

curr_dirname = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.dirname(os.path.abspath(curr_dirname))
MODEL_EXPORT_DIR = os.path.join(project_root_dir, 'models/new')
NEW_TEST_DIR = os.path.join(project_root_dir, 'NewTestImages')
##################################################################

class TrafficSignsClassifier:
    def __init__(self):
        self.x_train = None
        self.y_train = None
        self.x_validation = None
        self.y_validation = None
        self.x_test = None
        self.y_test = None
        self.train_errors = list()
        self.test_errors = list()
        self.train_cost = list()
        
    def train_validation_test_split(self, train_images, train_labels,test_images, test_labels, split_size = 5):
        train_labels = np.array(train_labels, dtype=np.int8)
        train_labels = self.convert_to_one_hot(train_labels, NUM_CLASSES)
        test_labels = np.array(test_labels, dtype=np.int8)
        test_labels = self.convert_to_one_hot(test_labels, NUM_CLASSES)

        train_dataset_size = len(train_images)
        # split the train set to get validation set
        num_validation_images = int(train_dataset_size * split_size/100)
        is_for_training = np.ones(train_dataset_size, dtype=bool)
        # randomly choose validation set indexes
        validation_imgs_idx = np.random.choice(np.arange(train_dataset_size), num_validation_images, replace=False)
        is_for_training[validation_imgs_idx] = False

        self.x_train = train_images[is_for_training]
        self.y_train = train_labels[is_for_training]
        self.x_validation = train_images[~is_for_training]
        self.y_validation = train_labels[~is_for_training]
        self.x_test, self.y_test = test_images, test_labels

    def create_placeholders(self, nH, nW, nC, nY):

        X = tf.placeholder(tf.float32, shape=[None, nH, nW, nC], name="X")
        Y = tf.placeholder(tf.float32, shape=[None, nY], name="Y")
        keep_prob = tf.placeholder(tf.float32)

        return X, Y, keep_prob

    def initialize_parameters(self):
        # Weights initialization
        W1 = tf.get_variable("W1", shape = [5, 5, 3, 16], initializer = tf.contrib.layers.xavier_initializer(seed = 0))
        W2 = tf.get_variable("W2", shape = [5, 5, 16, 32], initializer = tf.contrib.layers.xavier_initializer(seed = 0))
        W3 = tf.get_variable("W3", shape = [3, 3, 32, 128], initializer = tf.contrib.layers.xavier_initializer(seed = 0))
        W4 = tf.get_variable("W4", shape = [3, 3, 128, 256], initializer = tf.contrib.layers.xavier_initializer(seed = 0))

        return { "W1": W1, "W2":W2, "W3": W3, "W4": W4 }

    def forward_propagation(self, X, parameters, keep_prob):
        '''
        MODEL ARCHITECTURE:
        CONV --> ReLU --> CONV --> ReLU --> POOL --> CONV --> ReLU --> CONV --> ReLU --> POOL --> FC_1 --> FC_2 --> Output :)
        '''
        W1 = parameters["W1"]
        W2 = parameters["W2"]
        W3 = parameters["W3"]
        W4 = parameters["W4"]

        # Conv1 layer with stride 1 and same padding
        Z1 = tf.nn.conv2d(X, W1, strides=[1,1,1,1], padding="VALID")

        # Relu
        A1 = tf.nn.relu(Z1)

        # Conv2 with stride 1 and same padding
        Z2 = tf.nn.conv2d(A1, W2, strides=[1,1,1,1], padding="VALID")

        # Relu
        A2 = tf.nn.relu(Z2)

        # max-pool Kernel[2X2] stride 2
        P1 = tf.nn.max_pool(A2, ksize=[1,2,2,1], strides = [1,2,2,1], padding="VALID")

        # Conv3 layer with stride 1 and same padding
        Z3 = tf.nn.conv2d(P1, W3, strides=[1,1,1,1], padding="VALID")

        # Relu
        A3 = tf.nn.relu(Z3)

        # Conv4 with stride 1 and same padding
        Z4= tf.nn.conv2d(A3, W4, strides=[1,1,1,1], padding="VALID")

        # Relu
        A4 = tf.nn.relu(Z4)

        # max-pool kernel[2X2] stride 2
        P2 = tf.nn.max_pool(A4, ksize=[1,2,2,1], strides = [1,2,2,1], padding="VALID")

        # Flatten
        P2 = tf.contrib.layers.flatten(P2)
        
        #fully connected
        FC_1 = tf.contrib.layers.fully_connected(P2, 256, activation_fn=None)

        # drop outs are used to randomly deactivate neurons in layers.
        drop_out_1 = tf.nn.dropout(FC_1, keep_prob)
        
        FC_2 = tf.contrib.layers.fully_connected(drop_out_1, 128, activation_fn=None)
        
        #drop_out_2 = tf.nn.dropout(FC_2, keep_prob)

        #FC_3 = tf.contrib.layers.fully_connected(drop_out_2, 80, activation_fn=None)

        Z5 = tf.contrib.layers.fully_connected(FC_2, NUM_CLASSES, activation_fn=None)

        # returning Activations since we use that for visualization.
        return [A1, A2, A3, A4, Z5]

    def compute_cost(self, output, Y):
        cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits = output, labels = Y))
        return cost


    def random_mini_batches(self, X, Y, mini_batch_size = 64, seed = 0):
        # This code was adapted from deeplearning.ai online course.
        # Randomly split data into minibatches
        # Returns list of all minibatch

        m = X.shape[0] # number of training examples
        mini_batches = []
        np.random.seed(seed)
        permutation = list(np.random.permutation(m))
        shuffled_X = X[permutation,:,:,:]
        shuffled_Y = Y[permutation,:]

        num_complete_minibatches = int(math.floor(m/mini_batch_size)) # number of mini batches of size mini_batch_size in your partitionning

        for k in range(0, num_complete_minibatches):
            mini_batch_X = shuffled_X[k * mini_batch_size : k * mini_batch_size + mini_batch_size,:,:,:]
            mini_batch_Y = shuffled_Y[k * mini_batch_size : k * mini_batch_size + mini_batch_size,:]
            mini_batch = (mini_batch_X, mini_batch_Y)
            mini_batches.append(mini_batch)
        
        # Pick the remaining images. Since we only have collected complete minibatches.
        # This batch will not be complete.
        remaining_num_imgs = m - num_complete_minibatches*mini_batch_size
        missed_batch = (shuffled_X[m-remaining_num_imgs:m], shuffled_Y[m-remaining_num_imgs:m])
        mini_batches.append(missed_batch)
        
        return mini_batches

    def convert_to_one_hot(self, Y, C):
        # Details about one hot: https://machinelearningmastery.com/why-one-hot-encode-data-in-machine-learning/
        Y = np.eye(C)[Y.reshape(-1)]
        return Y

    def get_augmented_images(self, images, labels, epoch):
        # Image augmentation. The number of augmented image is is proportional to 50/epoch+1
        augmented_images = []
        augmented_labels = []
        len_img = len(images)
        num_imgs = int(50/(epoch+1))
        for i in range(num_imgs):
            rand_int = np.random.randint(len_img)
            augmented_images.append(transform_image(images[rand_int],3,3,3))
            augmented_labels.append(labels[rand_int])

        return np.array(augmented_images), np.array(augmented_labels)

    def visualize_filters(self, A1, A2, A3, A4, image, sess, X, keep_prob):
        # This function is purely for visulization purpose. We visualize different activation layers
        activation_units_1 = A1.eval(session=sess,feed_dict={X:image.reshape(1,30,30,3),keep_prob:1.0})
        activation_units_2 = A2.eval(session=sess,feed_dict={A1:activation_units_1,keep_prob:1.0})
        activation_units_3 = A3.eval(session=sess,feed_dict={A2:activation_units_2,keep_prob:1.0})
        activation_units_4 = A4.eval(session=sess,feed_dict={A3:activation_units_3,keep_prob:1.0})
        
        activations = [activation_units_1, activation_units_2, activation_units_3, activation_units_4]
        
        for activation in activations:
            num_of_filters = activation.shape[3]
            filtered_images = []
            for i in range(num_of_filters):
                filtered_images.append(activation[0,:,:,i-1])

            visualize_dataset(np.array(filtered_images)[0:15], True, (6,6), 4, 4)

    def build_model(self, restore = True, learning_rate = 0.0001, num_epochs = 50, minibatch_size = 100, print_cost = True):
        costs = []
        accuracys = []
        
        # Seeding is done so we get same randomness during different runs. Useful during testing
        tf.set_random_seed(1)

        (m, nH, nW, nC) = self.x_train.shape
        nY = self.y_train.shape[1]

        X, Y, keep_prob = self.create_placeholders(nH, nW, nC, nY)
        
        parameters = self.initialize_parameters()

        A1, A2, A3, A4, Z5 = self.forward_propagation(X, parameters, keep_prob)

        cost = self.compute_cost(Z5, Y)

        optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

        prediction = tf.argmax(tf.nn.softmax(Z5), 1)

        truth = tf.argmax(Y, 1)
        
        equality = tf.equal(prediction, truth)
        
        accuracy = tf.reduce_mean(tf.cast(equality, tf.float32))
        
        init = tf.global_variables_initializer()

        saver = tf.train.Saver()
        
        with tf.Session() as sess:
            sess.run(init)

            if restore == True: # restore the previously trained model
                
                saver.restore(sess,tf.train.latest_checkpoint(MODEL_EXPORT_DIR)) 
                pred, tru, eq, acc, shuffled_Y = self.run_test_in_batches(sess, [prediction, truth, equality, accuracy], X, Y, keep_prob, 1000)                
                print('Final Test Accuracy: {} %'.format(acc*100))
                
                # Visualization utility functions
                self.print_confusion_matrix(shuffled_Y,pred)
                self.plot_failed_cases(eq, pred)
                self.visualize_filters(A1, A2, A3, A4, self.x_train[20], sess, X, keep_prob)
            
            else: # start training process
                
                # epoch is one run through the entire training set.
                # Since our batch is large, we split them into mini batches and run batch gradient descent on them.
                for epoch in range(num_epochs):
                    minibatch_cost = 0.
                    num_minibatches = int(m / minibatch_size) # number of minibatches
                    minibatches = self.random_mini_batches(self.x_train, self.y_train, minibatch_size, seed=3)
                    
                    for minibatch in minibatches:
                        (minibatch_X, minibatch_Y) = minibatch
                        # augmenting images during training
                        aug_images, aug_labels = self.get_augmented_images(minibatch_X, minibatch_Y, epoch)
                        
                        if len(aug_images):
                            minibatch_X = np.append(minibatch_X, aug_images, axis = 0)
                            minibatch_Y = np.append(minibatch_Y, aug_labels, axis = 0)
                        _ , temp_cost = sess.run([optimizer, cost], feed_dict = {X: minibatch_X, Y: minibatch_Y, keep_prob: 0.5})
                        minibatch_cost += temp_cost / num_minibatches
                        
                    self.train_cost.append(minibatch_cost)  
                    
                    if print_cost == True:
                        train_acc= sess.run(accuracy, feed_dict = {X: self.x_validation, Y: self.y_validation, keep_prob: 1.0})
                        print('Validation Data Accuracy: {} %'.format(train_acc*100))
                        costs.append(minibatch_cost)
                        accuracys.append(train_acc)
                        self.train_errors.append(train_acc)

                    if print_cost == True and epoch % 5 == 0:
                        self.save_model(sess, epoch)
                        print ("############ EPOCH %i SUMMARY: ############" % epoch)
                        print("Copy of model saved...")
                        print ("Cost after epoch %i: %f" % (epoch, minibatch_cost))
                        print('Validation Data Accuracy: {} %'.format(train_acc*100))
                        print ('############################################')
                
                pred, tru, eq, acc, shuffled_Y = self.run_test_in_batches(sess, [prediction, truth, equality, accuracy], X, Y, keep_prob, 1000)
               
                print('Final Test Accuracy: {} %'.format(acc*100))
                
                # Visualization utility functions
                self.print_confusion_matrix(shuffled_Y,pred)
                self.plot_failed_cases(eq, pred)
                self.visualize_filters(A1, A2, A3, A4, self.x_train[20], sess, X, keep_prob)
    
    def run_test_in_batches(self, sess, information, X, Y, keep_prob, size=1000):
        # Splitting the test data into batches and running to model on the it 
        # to find the overall accuracy. Since our test batch contains about 12630 images,
        # the computer memory is not sufficient in a single pass so splitting them into
        # mini batches.

        test_minibatches = self.random_mini_batches(self.x_test, self.y_test, 1000)
        total_accuracy = 0
        predictions = np.array([])
        truth = np.array([])
        equality = np.array([])
        shuffled_Y = []
        
        for test_minibatch in test_minibatches:
            test_minibatch_x, test_minibatch_y = test_minibatch
            pred, tru, eq, acc= sess.run(information, feed_dict = {X: test_minibatch_x, Y: test_minibatch_y, keep_prob: 1.0})
            total_accuracy += acc
            predictions = np.concatenate((predictions, pred), axis=0)
            truth = np.concatenate((truth, tru), axis=0)
            equality = np.concatenate((equality, eq), axis=0)
            test_minibatch_y = test_minibatch_y.tolist()
            shuffled_Y += test_minibatch_y
            self.test_errors.append(acc)
            
        total_accuracy = (total_accuracy)/len(test_minibatches)
        
        return predictions, truth, equality, total_accuracy, np.array(shuffled_Y)
        
                
    def print_confusion_matrix(self, label, prediction):
        label = np.argmax(label, 1)
        sess = tf.Session()
        cnfn_matrix = sess.run(tf.confusion_matrix(label, prediction))
        np.set_printoptions(precision=2)
        
        # Plot non-normalized confusion matrix
        plot_confusion_matrix(cnfn_matrix, classes=label,
                              title='Confusion matrix, without normalization')
        
    def save_model(self, sess, epoch):
        saver = tf.train.Saver()
        saver.save(sess, MODEL_EXPORT_DIR + '/my-model', global_step = epoch)

    def plot_failed_cases(self, equality, prediction):
        incorrect = (equality == False)
        test_imgs = self.x_test
        test_lbls = self.y_test
        incorrect_images = test_imgs[incorrect]
        incorrect_predictions = prediction[incorrect]
        correct_labels = np.argmax(test_lbls[incorrect], 1)

        visualize_dataset(incorrect_images[25:50], False, (8,8), 5, 5, correct_labels, incorrect_predictions)
    
    def plot_learning_curve(self):
        plt.figure(figsize=(8,6))
        plt.title('Learning Curve')
        
        plt.tight_layout()
        
        if len(self.train_errors) > 0:
            plt.legend(['Training Error'])
            plt.plot([1-el for el in self.train_errors])    
        else:
            plt.legend(['Test Error'])
            plt.plot([1-el for el in self.test_errors])  
            
#        plt.ylim([-.01,0.2])        
        plt.savefig('learning_curve.png')
        plt.ylabel('Error')
        plt.xlabel('Epoch');
        
    def plot_cost(self):
        plt.figure(figsize=(8,6))
        plt.title('Cost')        
        plt.tight_layout()        
        plt.legend(['Cost'])
        plt.plot([el for el in self.train_cost])             
        plt.savefig('Training_Cost.png')
        plt.ylabel('Cost')
        plt.xlabel('Epoch');
        return self.train_cost
    
    def softMaxProb(self,test_x,test_y):
        
        (m, nH, nW, nC) = self.x_train.shape
        nY = self.y_train.shape[1]
        X, Y, keep_prob = self.create_placeholders(nH, nW, nC, nY)        
        parameters = self.initialize_parameters()
        d1,d2,d3,d4, Z5 = self.forward_propagation(X, parameters, keep_prob)
        init = tf.global_variables_initializer()
        saver = tf.train.Saver()
        softmax_logits = tf.nn.softmax(Z5)
        top_k = tf.nn.top_k(softmax_logits, k=5)
        
        with tf.Session() as sess:
            sess.run(init)            
            saver.restore(sess,tf.train.latest_checkpoint(MODEL_EXPORT_DIR)) 
            my_top_k          = sess.run(top_k,          feed_dict = {X: test_x, keep_prob: 1.0})              
        return my_top_k
    
    def plot_predict(self, top, prob, fsize=(8,8), rows = 4, cols = 6):
        
        fig = plt.figure(figsize=fsize)
        count = 1
        for i in range(0, rows):
#            #plot test image
            ax = fig.add_subplot(rows, cols, count)                
            count += 1
            image = plt.imread(NEW_TEST_DIR + '/0' + str(i+1) + '.ppm')
            plt.imshow(image)
#                
            for j in range(1, cols):
                #plot guess class
                ax = fig.add_subplot(rows, cols, count) 
#                p  = float("{0:.100f}".format(prob[i][j-1]))
                p  = prob[i][j-1]
                ax.set_title(str(p))
                count += 1
                image = plt.imread(project_root_dir + '/sign_class/' + str(top[i][j-1]) + '.png')
                plt.imshow(image)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    
    # Get the image paths
    train_img_path = os.path.join(project_root_dir, 'GTSRB/Final_Training/Images')
    test_img_path = os.path.join(project_root_dir, 'GTSRB/Final_Test/Images')

    # Get the images and store them
    train_images, train_labels = get_train_images(train_img_path)
    test_images, test_labels = get_test_images(test_img_path)
    
    visualize_training_data_distribution(train_labels)
    
    # Preprocess images
    preprocessed_train_images = preprocess_images(train_images, False)
    preprocessed_test_images = preprocess_images(test_images, False)

    # Model building and evaluation
    traffic_sign_classifier = TrafficSignsClassifier()
    traffic_sign_classifier.train_validation_test_split(np.array(preprocessed_train_images), train_labels, np.array(preprocessed_test_images), test_labels)
#    traffic_sign_classifier.build_model(restore = True)
#    traffic_sign_classifier.plot_learning_curve()
#    cost = traffic_sign_classifier.plot_cost()
    
    new_test_images, new_test_labels = get_new_test_images(NEW_TEST_DIR)
    preprocessed_new_test_images = preprocess_images(new_test_images, False)
    top = traffic_sign_classifier.softMaxProb(preprocessed_new_test_images,new_test_labels)      
    classes = traffic_sign_classifier.plot_predict(top.indices, top.values, (8,8),4,6)    
