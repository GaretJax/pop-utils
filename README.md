pop-utils
=========

The pop-utils package provides a collection of utilities to optimize the
deployment and management of a POP-C++ or POP-Java based setup with a special
focus on cloud deployments and Amazon Web Services.


Utilities
---------

The different utilities that come with the pop-utils package are:

 * ``pop-link`` -- A linker to register two or more already running job
   managers without needing to edit the configuration and restart them.

 * ``pop-master`` -- An AWS/Eucalyptus based utility to create base machine
   images for custom POP-C++/POP-Java deployments.

 * ``pop-cloud-setup`` -- An AWS/Eucalyptus based utility to setup a complete
   POP environment on a cloud service of choice.

 * ``pop-deploy`` -- A companion utility of the ``pop-cloud-setup`` utility to
   deploy an application to a particular setup (created either manually or
   using the ``pop-cloud-setup`` utility).


License
-------

The whole package is released under the MIT license. Note though that the
POP-C++/POP-Java sources are only available under the GPL license.


Links
-----

 * https://github.com/GaretJax/pop-utils -- Website of the pop-utils project

 * http://gridgroup.hefr.ch/popc -- Website of the POP-C++ project

 * http://aws.amazon.com/ -- Amazon Web Services homepage

 * http://www.eucalyptus.com/ -- Eucalyptus home page