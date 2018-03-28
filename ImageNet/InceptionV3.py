import numpy as np
import sys

split_no=int(sys.argv[1])
use_bg_cls=sys.argv[2]

parallel=False

no_of_epochs=3

if parallel:
    from imagenet_data_prep import parallelized_imagenet_data_prep    
    training_generator = parallelized_imagenet_data_prep(
                                            db_type='train',
                                            batch_size=128,
                                            include_known_unknowns = True,
                                            use_bg_cls=use_bg_cls,
                                            split_no=split_no,
                                            no_of_epochs=no_of_epochs
                                            )

    validation_generator = parallelized_imagenet_data_prep(
                                            db_type='val',
                                            batch_size=128,
                                            training_data_obj=training_generator,
                                            use_bg_cls=use_bg_cls,
                                            split_no=split_no
                                            )

    fit_generator_params = dict(
                                workers=1,
                                steps_per_epoch=training_generator.get_no_of_batches,
                                validation_steps=validation_generator.get_no_of_batches
                                )
else:
    # This Implementation is slightly slower and uses the keras tutorial approach    
    from imagenet_data_prep import imagenet_data_prep    
    training_generator = imagenet_data_prep(
                                            db_type='train',
                                            batch_size=128,
                                            include_known_unknowns = True,
                                            use_bg_cls=use_bg_cls,
                                            split_no=split_no
                                            )

    validation_generator = imagenet_data_prep(
                                            db_type='val',
                                            batch_size=128,
                                            training_data_obj=training_generator,
                                            use_bg_cls=use_bg_cls,
                                            split_no=split_no
                                            )
    fit_generator_params = dict(workers=1)
    """
    **self.feature_params
    """
    

from keras.applications.inception_v3 import InceptionV3
from keras.preprocessing import image
from keras.models import Model
from keras.layers import Dense, GlobalAveragePooling2D
from keras import backend as K
from keras.optimizers import Adam

from keras.backend.tensorflow_backend import set_session
from keras.utils import multi_gpu_model
import tensorflow as tf

config = tf.ConfigProto()
config.gpu_options.allow_growth = True
set_session(tf.Session(config=config))


#tf.reset_default_graph()
with tf.device('/cpu:0'):
    # create the base pre-trained model
    base_model = InceptionV3(weights='imagenet', include_top=False)

    # add a global spatial average pooling layer
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    # let's add a fully-connected layer
    x = Dense(1024, activation='relu')(x)
    if use_bg_cls:
        predictions = Dense(101, activation='softmax')(x)
    else:
        predictions = Dense(100, activation='softmax')(x)

    model = Model(inputs=base_model.input, outputs=predictions)

parallel_model = multi_gpu_model(model, gpus=[0,1])

# first: train only the top layers (which were randomly initialized)
# i.e. freeze all convolutional InceptionV3 layers
for layer in base_model.layers:
    layer.trainable = False

# compile the model (should be done *after* setting layers to non-trainable)
#adam = Adam(lr=0.01)
parallel_model.compile(optimizer='rmsprop', loss='categorical_crossentropy',metrics=['acc'])


# train the model on the new data for a few epochs
#model.fit_generator(...)
parallel_model.fit_generator(
                            generator=training_generator,
                            validation_data=validation_generator,
                            use_multiprocessing=False,
                            max_queue_size=50,
                            epochs=no_of_epochs,
                            **fit_generator_params
                            )

if use_bg_cls:
    model.save('BG_Cls_Data/Finetuned_Model_Split_'+str(split_no))
else:
    model.save('Cross_Entr_Data/Finetuned_Model_Split_'+str(split_no))



"""
i=0
while i<10:
    i+=1
    print training_generator
    d = next(training_generator)
    print "D",d,list(d)
#    print (X,y,sample_weights)
"""
